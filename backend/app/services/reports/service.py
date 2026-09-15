import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
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
from app.services.pipeline.service import get_default_stage_template


def funnel(db: Session, organization_id: uuid.UUID) -> list[dict]:
    template = get_default_stage_template(db, organization_id)
    if template is None:
        return []
    stages = sorted(template.stages, key=lambda s: s.sort_order)

    applications = list(db.scalars(select(Application).where(Application.organization_id == organization_id)).all())
    max_reached: dict[uuid.UUID, int] = {}
    stage_order_by_id = {s.id: s.sort_order for s in stages}

    for app_row in applications:
        reached = stage_order_by_id.get(app_row.current_stage_id, -1)
        max_reached[app_row.id] = reached

    history_rows = db.scalars(
        select(ApplicationStageHistory).where(ApplicationStageHistory.application_id.in_([a.id for a in applications]))
    ).all()
    for row in history_rows:
        order = stage_order_by_id.get(row.to_stage_id)
        if order is not None:
            max_reached[row.application_id] = max(max_reached.get(row.application_id, -1), order)

    return [
        {"stage": stage.name, "value": sum(1 for reached in max_reached.values() if reached >= stage.sort_order)}
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
    rows = db.execute(
        select(Job.recruiter_id, User.full_name, func.count(Job.id))
        .join(User, User.id == Job.recruiter_id)
        .where(Job.organization_id == organization_id, Job.status == JobStatus.ACTIVE.value)
        .group_by(Job.recruiter_id, User.full_name)
    ).all()

    results = []
    for recruiter_id, full_name, open_jobs in rows:
        applications = (
            db.scalar(
                select(func.count(Application.id))
                .join(Job, Job.id == Application.job_id)
                .where(Job.recruiter_id == recruiter_id, Job.organization_id == organization_id)
            )
            or 0
        )
        hires = (
            db.scalar(
                select(func.count(Application.id))
                .join(Job, Job.id == Application.job_id)
                .where(
                    Job.recruiter_id == recruiter_id,
                    Job.organization_id == organization_id,
                    Application.status == ApplicationStatus.HIRED.value,
                )
            )
            or 0
        )
        results.append(
            {
                "recruiter_id": recruiter_id,
                "recruiter_name": full_name,
                "open_jobs": open_jobs,
                "applications": applications,
                "hires": hires,
            }
        )
    return results


def aging_jobs(db: Session, organization_id: uuid.UUID) -> list[dict]:
    jobs = list(
        db.scalars(
            select(Job)
            .where(Job.organization_id == organization_id, Job.status == JobStatus.ACTIVE.value)
            .order_by(Job.posted_at)
        ).all()
    )
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
    hired_events = db.execute(
        select(Job.posted_at, ApplicationStageHistory.created_at)
        .join(Application, Application.id == ApplicationStageHistory.application_id)
        .join(Job, Job.id == Application.job_id)
        .join(StageTemplateStage, StageTemplateStage.id == ApplicationStageHistory.to_stage_id)
        .where(
            Job.organization_id == organization_id,
            StageTemplateStage.terminal_outcome == TerminalOutcome.HIRED.value,
            Job.posted_at.is_not(None),
        )
    ).all()

    days = [(hired_at - posted_at).days for posted_at, hired_at in hired_events if posted_at and hired_at]
    return {
        "average_days": sum(days) / len(days) if days else None,
        "filled_jobs_count": len(days),
    }


_TREND_MONTHS = 12


def _month_key(value: datetime) -> str:
    return value.strftime("%Y-%m")


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


def hiring_trend(db: Session, organization_id: uuid.UUID) -> list[dict]:
    """Offers created vs. hires made, bucketed by month over the last year."""
    months = _recent_month_keys()
    window_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=31 * (_TREND_MONTHS - 1)
    )

    offers_by_month: dict[str, int] = {key: 0 for key in months}
    hires_by_month: dict[str, int] = {key: 0 for key in months}

    offer_dates = db.scalars(
        select(Offer.created_at).where(Offer.organization_id == organization_id, Offer.created_at >= window_start)
    ).all()
    for created_at in offer_dates:
        key = _month_key(created_at)
        if key in offers_by_month:
            offers_by_month[key] += 1

    hire_dates = db.scalars(
        select(ApplicationStageHistory.created_at)
        .join(Application, Application.id == ApplicationStageHistory.application_id)
        .join(StageTemplateStage, StageTemplateStage.id == ApplicationStageHistory.to_stage_id)
        .where(
            Application.organization_id == organization_id,
            StageTemplateStage.terminal_outcome == TerminalOutcome.HIRED.value,
            ApplicationStageHistory.created_at >= window_start,
        )
    ).all()
    for created_at in hire_dates:
        key = _month_key(created_at)
        if key in hires_by_month:
            hires_by_month[key] += 1

    return [
        {
            "month": datetime.strptime(key, "%Y-%m").strftime("%b %Y"),
            "offers": offers_by_month[key],
            "hires": hires_by_month[key],
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
    """Distribution of the latest AI overall score per application."""
    rows = db.execute(
        select(AIEvaluation.application_id, AIEvaluation.version, AIEvaluation.overall_score)
        .where(
            AIEvaluation.organization_id == organization_id,
            AIEvaluation.status == AIEvaluationStatus.COMPLETED.value,
            AIEvaluation.overall_score.is_not(None),
        )
        .order_by(AIEvaluation.application_id, AIEvaluation.version)
    ).all()

    # Rows are version-ordered, so the last write per application is the latest evaluation.
    latest: dict[uuid.UUID, float] = {}
    for application_id, _version, overall_score in rows:
        latest[application_id] = float(overall_score)

    counts = {label: 0 for label, _lo, _hi in _SCORE_BUCKETS}
    for score in latest.values():
        for label, low, high in _SCORE_BUCKETS:
            if low <= score < high:
                counts[label] += 1
                break

    return [{"bucket": label, "count": counts[label]} for label, _lo, _hi in _SCORE_BUCKETS]


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
                Job.recruiter_id == recruiter_id,
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
                Job.recruiter_id == recruiter_id, Job.organization_id == organization_id, Application.applied_at >= week_ago
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
                Job.recruiter_id == recruiter_id,
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
                Job.recruiter_id == recruiter_id,
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
