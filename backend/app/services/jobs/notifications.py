"""Emails recruiters when a job is assigned to them."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.job import Job
from app.db.models.user import User
from app.services.mail import messages
from app.workers.dispatch import dispatch
from app.workers.tasks.mail import send_email_task


def job_recruiter_ids(job: Job) -> set[uuid.UUID]:
    """The primary recruiter plus everyone the job is assigned to."""
    ids = set(job.assigned_to_ids or [])
    if job.primary_recruiter_id:
        ids.add(job.primary_recruiter_id)
    return ids


def notify_assigned_recruiters(
    db: Session, job: Job, *, recruiter_ids: set[uuid.UUID], assigned_by: str | None
) -> int:
    """Send each active recruiter in `recruiter_ids` the assignment email.

    Returns how many were queued. Mail trouble never fails the request that
    triggered it (`dispatch` and `send_email` both swallow errors).
    """
    if not recruiter_ids:
        return 0
    users = db.scalars(
        select(User).where(
            User.id.in_(recruiter_ids),
            User.organization_id == job.organization_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    ).all()
    location = job.location or job.city
    client_name = job.client.name if job.client else None
    for user in users:
        subject, text_body, html_body = messages.job_assignment(
            recruiter_first_name=(user.full_name or "").split(" ")[0] or None,
            job_title=job.title,
            req_id=job.req_id,
            job_id=str(job.id),
            client_name=client_name,
            location=location,
            assigned_by=assigned_by,
        )
        dispatch(send_email_task, user.email, subject, text_body, html_body, allow_inline=True)
    return len(users)
