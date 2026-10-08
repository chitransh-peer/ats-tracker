import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    AIEvaluationStatus,
    ApplicationStatus,
    InterviewStatus,
    JobStatus,
    OfferStatus,
    TerminalOutcome,
)
from app.db.models.ai import AIEvaluation
from app.db.models.application import Application, ApplicationStageHistory
from app.db.models.candidate import Candidate
from app.db.models.interview import Interview
from app.db.models.job import Job
from app.db.models.offer import Offer
from app.db.models.pipeline_stage import StageTemplateStage
from app.db.models.user import User
from app.services.jobs.service import job_recruiters, recruiter_on_job
from app.services.pipeline.service import get_default_stage_template


def funnel(db: Session, organization_id: uuid.UUID) -> list[dict]:
    """How many applications reached each stage of the default template.

    An application counts toward every stage up to the furthest it ever got
    to, whether it is there now or moved on, so the history counts as well as
    the current stage. Computed by the database in one query: loading every
    application and its history to do this in Python failed at ~65,000.
    """
    template = get_default_stage_template(db, organization_id)
    if template is None:
        return []
    stages = sorted(template.stages, key=lambda s: s.sort_order)

    # Only this template's stages carry an order; a stage from another template
    # joins to nothing and counts as "not reached" (-1).
    template_stage = (
        select(StageTemplateStage.id, StageTemplateStage.sort_order)
        .where(StageTemplateStage.template_id == template.id)
        .subquery()
    )
    current_stage = template_stage.alias("current_stage")
    history_stage = template_stage.alias("history_stage")
    reached = (
        select(
            func.greatest(
                func.coalesce(func.max(current_stage.c.sort_order), -1),
                func.coalesce(func.max(history_stage.c.sort_order), -1),
            ).label("reached")
        )
        .select_from(Application)
        .outerjoin(current_stage, current_stage.c.id == Application.current_stage_id)
        .outerjoin(ApplicationStageHistory, ApplicationStageHistory.application_id == Application.id)
        .outerjoin(history_stage, history_stage.c.id == ApplicationStageHistory.to_stage_id)
        .where(Application.organization_id == organization_id)
        .group_by(Application.id)
        .subquery()
    )
    counts = db.execute(select(reached.c.reached, func.count()).group_by(reached.c.reached)).all()

    return [
        {"stage": stage.name, "value": sum(count for order, count in counts if order >= stage.sort_order)}
        for stage in stages
    ]


def source_effectiveness(db: Session, organization_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(Application.source, func.count(Application.id))
        .where(Application.organization_id == organization_id)
        .group_by(Application.source)
    ).all()
    return [{"source": source or "Unknown", "value": count} for source, count in rows]


def recruiter_performance(db: Session, organization_id: uuid.UUID) -> list[dict]:
    """Per recruiter with at least one open job: open jobs, and applications
    and hires across all their jobs. A job counts for its primary recruiter
    and everyone it is assigned to, as the job page shows them. One grouped
    query, not three per recruiter."""
    owners = job_recruiters()
    open_jobs = func.count(func.distinct(Job.id)).filter(Job.status == JobStatus.ACTIVE.value)
    rows = db.execute(
        select(
            owners.c.user_id,
            User.full_name,
            open_jobs,
            func.count(Application.id),
            func.count(Application.id).filter(Application.status == ApplicationStatus.HIRED.value),
        )
        .select_from(owners)
        .join(Job, Job.id == owners.c.job_id)
        .join(User, User.id == owners.c.user_id)
        .outerjoin(Application, Application.job_id == Job.id)
        .where(Job.organization_id == organization_id, Job.deleted_at.is_(None))
        .group_by(owners.c.user_id, User.full_name)
        .having(open_jobs > 0)
        .order_by(User.full_name)
    ).all()
    return [
        {
            "recruiter_id": recruiter_id,
            "recruiter_name": full_name,
            "open_jobs": open_count,
            "applications": applications,
            "hires": hires,
        }
        for recruiter_id, full_name, open_count, applications, hires in rows
    ]


def aging_jobs(db: Session, organization_id: uuid.UUID) -> list[dict]:
    # The four columns shown, not whole job rows.
    jobs = db.execute(
        select(Job.id, Job.title, Job.status, Job.posted_at)
        .where(Job.organization_id == organization_id, Job.status == JobStatus.ACTIVE.value, Job.deleted_at.is_(None))
        .order_by(Job.posted_at)
    ).all()
    now = datetime.now(UTC)
    return [
        {
            "job_id": job.id,
            "title": job.title,
            "status": job.status,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
            "age_days": (now - job.posted_at).days if job.posted_at else None,
        }
        for job in jobs
    ]


def time_to_fill(db: Session, organization_id: uuid.UUID) -> dict:
    """Average whole days from a job being posted to each hire on it."""
    days = func.floor(func.extract("epoch", ApplicationStageHistory.created_at - Job.posted_at) / 86400)
    average, count = db.execute(
        select(func.avg(days), func.count())
        .select_from(ApplicationStageHistory)
        .join(Application, Application.id == ApplicationStageHistory.application_id)
        .join(Job, Job.id == Application.job_id)
        .join(StageTemplateStage, StageTemplateStage.id == ApplicationStageHistory.to_stage_id)
        .where(
            Job.organization_id == organization_id,
            StageTemplateStage.terminal_outcome == TerminalOutcome.HIRED.value,
            Job.posted_at.is_not(None),
        )
    ).one()
    return {
        "average_days": float(average) if average is not None else None,
        "filled_jobs_count": count,
    }


_TREND_MONTHS = 12


def _recent_month_keys(count: int = _TREND_MONTHS) -> list[str]:
    now = datetime.now(UTC)
    keys: list[str] = []
    year, month = now.year, now.month
    for _ in range(count):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(keys))


def _count_by_month(db: Session, column, query) -> dict[str, int]:
    """{"YYYY-MM": count} for `query`, bucketed on `column` in UTC."""
    month = func.to_char(func.timezone("UTC", column), "YYYY-MM")
    return dict(db.execute(query.add_columns(month, func.count()).group_by(month)).all())


def hiring_trend(db: Session, organization_id: uuid.UUID) -> list[dict]:
    """Offers created vs. hires made, bucketed by month over the last year.
    The database counts per month, so only twelve rows per series come back."""
    months = _recent_month_keys()
    window_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=31 * (_TREND_MONTHS - 1)
    )

    offers_by_month = _count_by_month(
        db,
        Offer.created_at,
        select().select_from(Offer).where(Offer.organization_id == organization_id, Offer.created_at >= window_start),
    )
    hires_by_month = _count_by_month(
        db,
        ApplicationStageHistory.created_at,
        select()
        .select_from(ApplicationStageHistory)
        .join(Application, Application.id == ApplicationStageHistory.application_id)
        .join(StageTemplateStage, StageTemplateStage.id == ApplicationStageHistory.to_stage_id)
        .where(
            Application.organization_id == organization_id,
            StageTemplateStage.terminal_outcome == TerminalOutcome.HIRED.value,
            ApplicationStageHistory.created_at >= window_start,
        ),
    )

    return [
        {
            "month": datetime.strptime(key, "%Y-%m").strftime("%b %Y"),
            "offers": offers_by_month.get(key, 0),
            "hires": hires_by_month.get(key, 0),
        }
        for key in months
    ]


_SCORE_BUCKETS: list[tuple[str, float, float]] = [
    ("0-39", 0, 40),
    ("40-59", 40, 60),
    ("60-74", 60, 75),
    ("75-89", 75, 90),
    ("90-100", 90, 100.01),
]


def score_distribution(db: Session, organization_id: uuid.UUID) -> list[dict]:
    """Distribution of the latest completed AI overall score per application,
    bucketed by the database rather than by loading every evaluation."""
    latest = (
        select(AIEvaluation.overall_score.label("score"))
        .where(
            AIEvaluation.organization_id == organization_id,
            AIEvaluation.status == AIEvaluationStatus.COMPLETED.value,
            AIEvaluation.overall_score.is_not(None),
        )
        .distinct(AIEvaluation.application_id)
        .order_by(AIEvaluation.application_id, AIEvaluation.version.desc())
        .subquery()
    )
    bucket = case(
        *[((latest.c.score >= low) & (latest.c.score < high), label) for label, low, high in _SCORE_BUCKETS],
        else_=None,
    )
    counts = dict(db.execute(select(bucket, func.count()).group_by(bucket)).all())
    return [{"bucket": label, "count": counts.get(label, 0)} for label, _lo, _hi in _SCORE_BUCKETS]


def offer_metrics(db: Session, organization_id: uuid.UUID) -> dict:
    rows = db.execute(
        select(Offer.status, func.count(Offer.id)).where(Offer.organization_id == organization_id).group_by(Offer.status)
    ).all()
    by_status = dict(rows)

    sent = by_status.get(OfferStatus.SENT.value, 0)
    accepted = by_status.get(OfferStatus.ACCEPTED.value, 0)
    declined = by_status.get(OfferStatus.DECLINED.value, 0)
    pending = by_status.get(OfferStatus.APPROVAL_PENDING.value, 0)

    # Only decided offers count toward the rate; still-outstanding ones aren't a signal yet.
    decided = accepted + declined
    return {
        "sent": sent,
        "accepted": accepted,
        "declined": declined,
        "pending": pending,
        "acceptance_rate": round(accepted / decided * 100, 1) if decided else None,
    }


def recruiter_dashboard(db: Session, organization_id: uuid.UUID, recruiter_id: uuid.UUID) -> dict:
    open_jobs = (
        db.scalar(
            select(func.count(Job.id)).where(
                Job.organization_id == organization_id,
                recruiter_on_job(recruiter_id),
                Job.status == JobStatus.ACTIVE.value,
            )
        )
        or 0
    )

    week_ago = datetime.now(UTC) - timedelta(days=7)
    applications_this_week = (
        db.scalar(
            select(func.count(Application.id))
            .join(Job, Job.id == Application.job_id)
            .where(
                recruiter_on_job(recruiter_id), Job.organization_id == organization_id, Application.applied_at >= week_ago
            )
        )
        or 0
    )

    interviews_scheduled = (
        db.scalar(
            select(func.count(Interview.id))
            .join(Application, Application.id == Interview.application_id)
            .join(Job, Job.id == Application.job_id)
            .where(
                recruiter_on_job(recruiter_id),
                Interview.organization_id == organization_id,
                Interview.status == InterviewStatus.SCHEDULED.value,
            )
        )
        or 0
    )

    offers_pending = (
        db.scalar(
            select(func.count(Offer.id))
            .join(Application, Application.id == Offer.application_id)
            .join(Job, Job.id == Application.job_id)
            .where(
                recruiter_on_job(recruiter_id),
                Offer.organization_id == organization_id,
                Offer.status == OfferStatus.APPROVAL_PENDING.value,
            )
        )
        or 0
    )

    return {
        "open_jobs": open_jobs,
        "applications_this_week": applications_this_week,
        "interviews_scheduled": interviews_scheduled,
        "offers_pending": offers_pending,
    }


def executive_dashboard(db: Session, organization_id: uuid.UUID) -> dict:
    total_open_jobs = (
        db.scalar(
            select(func.count(Job.id)).where(Job.organization_id == organization_id, Job.status == JobStatus.ACTIVE.value)
        )
        or 0
    )
    total_candidates = db.scalar(select(func.count(Candidate.id)).where(Candidate.organization_id == organization_id)) or 0
    total_hires = (
        db.scalar(
            select(func.count(Application.id)).where(
                Application.organization_id == organization_id, Application.status == ApplicationStatus.HIRED.value
            )
        )
        or 0
    )

    return {
        "total_open_jobs": total_open_jobs,
        "total_candidates": total_candidates,
        "total_hires": total_hires,
        "funnel": funnel(db, organization_id),
    }
