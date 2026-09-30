"""The pipeline board: applications grouped by stage.

Its own module because it reads through the applications service, which in
turn depends on the pipeline service for stage templates.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ApplicationStatus
from app.db.models.application import Application
from app.schemas.auth import CurrentUser
from app.services.applications.service import application_labels, build_applications_query

# Past this the board is unreadable anyway; the page says how many it is not
# showing and offers the job filter to narrow it.
BOARD_CARD_LIMIT = 2000

_ON_BOARD = (ApplicationStatus.ACTIVE.value, ApplicationStatus.HIRED.value)


def board(
    db: Session,
    organization_id: uuid.UUID,
    *,
    job_id: uuid.UUID | None = None,
    viewer: CurrentUser | None = None,
    limit: int = BOARD_CARD_LIMIT,
) -> dict:
    """Stage counts for every application on the board, plus cards for the
    newest `limit` of them.

    The counts come from the database, so they stay right when the cards are
    cut off; before, the board fetched a capped list and counted that, so past
    2,000 applications it silently under-reported and dropped cards.
    """
    query = build_applications_query(organization_id, job_id=job_id, viewer=viewer).where(Application.status.in_(_ON_BOARD))
    on_board = query.order_by(None).subquery()
    by_stage = dict(
        db.execute(select(on_board.c.current_stage_id, func.count()).group_by(on_board.c.current_stage_id)).all()
    )
    hired = db.scalar(select(func.count()).select_from(on_board).where(on_board.c.status == ApplicationStatus.HIRED.value))
    applications = list(db.scalars(query.limit(limit)).all())
    labels = application_labels(db, [a.id for a in applications])
    cards = [
        {
            "id": a.id,
            "candidate_id": a.candidate_id,
            "job_id": a.job_id,
            "current_stage_id": a.current_stage_id,
            "status": a.status,
            "applied_at": a.applied_at,
            "candidate_name": labels.get(a.id, {}).get("candidate_name"),
            "job_title": labels.get(a.id, {}).get("job_title"),
        }
        for a in applications
    ]
    return {
        "stage_counts": [{"stage_id": stage_id, "count": count} for stage_id, count in by_stage.items() if stage_id],
        "total": sum(by_stage.values()),
        "hired": hired or 0,
        "cards": cards,
        "limit": limit,
    }
