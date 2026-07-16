import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ApplicationStatus, InterviewStatus, JobStatus, OfferStatus, TerminalOutcome
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

    applications = list(
        db.scalars(select(Application).where(Application.organization_id == organization_id)).all()
    )
    max_reached: dict[uuid.UUID, int] = {}
    stage_order_by_id = {s.id: s.sort_order for s in stages}

    for app_row in applications:
        reached = stage_order_by_id.get(app_row.current_stage_id, -1)
        max_reached[app_row.id] = reached

    history_rows = db.scalars(
        select(ApplicationStageHistory).where(
            ApplicationStageHistory.application_id.in_([a.id for a in applications])
        )
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
        applications = db.scalar(
            select(func.count(Application.id))
            .join(Job, Job.id == Application.job_id)
            .where(Job.recruiter_id == recruiter_id, Job.organization_id == organization_id)
        ) or 0
        hires = db.scalar(
            select(func.count(Application.id))
            .join(Job, Job.id == Application.job_id)
            .where(
                Job.recruiter_id == recruiter_id,
                Job.organization_id == organization_id,
                Application.status == ApplicationStatus.HIRED.value,
            )
        ) or 0
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
    now = datetime.now(timezone.utc)
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


def recruiter_dashboard(db: Session, organization_id: uuid.UUID, recruiter_id: uuid.UUID) -> dict:
    open_jobs = db.scalar(
        select(func.count(Job.id)).where(
            Job.organization_id == organization_id, Job.recruiter_id == recruiter_id, Job.status == JobStatus.ACTIVE.value
        )
    ) or 0

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    applications_this_week = db.scalar(
        select(func.count(Application.id))
        .join(Job, Job.id == Application.job_id)
        .where(Job.recruiter_id == recruiter_id, Job.organization_id == organization_id, Application.applied_at >= week_ago)
    ) or 0

    interviews_scheduled = db.scalar(
        select(func.count(Interview.id))
        .join(Application, Application.id == Interview.application_id)
        .join(Job, Job.id == Application.job_id)
        .where(
            Job.recruiter_id == recruiter_id,
            Interview.organization_id == organization_id,
            Interview.status == InterviewStatus.SCHEDULED.value,
        )
    ) or 0

    offers_pending = db.scalar(
        select(func.count(Offer.id))
        .join(Application, Application.id == Offer.application_id)
        .join(Job, Job.id == Application.job_id)
        .where(
            Job.recruiter_id == recruiter_id,
            Offer.organization_id == organization_id,
            Offer.status == OfferStatus.APPROVAL_PENDING.value,
        )
    ) or 0

    return {
        "open_jobs": open_jobs,
        "applications_this_week": applications_this_week,
        "interviews_scheduled": interviews_scheduled,
        "offers_pending": offers_pending,
    }


def executive_dashboard(db: Session, organization_id: uuid.UUID) -> dict:
    total_open_jobs = db.scalar(
        select(func.count(Job.id)).where(Job.organization_id == organization_id, Job.status == JobStatus.ACTIVE.value)
    ) or 0
    total_candidates = db.scalar(
        select(func.count(Candidate.id)).where(Candidate.organization_id == organization_id)
    ) or 0
    total_hires = db.scalar(
        select(func.count(Application.id)).where(
            Application.organization_id == organization_id, Application.status == ApplicationStatus.HIRED.value
        )
    ) or 0

    return {
        "total_open_jobs": total_open_jobs,
        "total_candidates": total_candidates,
        "total_hires": total_hires,
        "funnel": funnel(db, organization_id),
    }
