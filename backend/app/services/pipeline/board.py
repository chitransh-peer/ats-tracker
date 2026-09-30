"""The pipeline board: applications grouped by stage.

Its own module because it reads through the applications service, which in
turn depends on the pipeline service for stage templates.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ApplicationStatus
from app.db.models.application import Application
from app.db.models.candidate import Candidate
from app.db.models.job import Job
from app.schemas.auth import CurrentUser
from app.services.applications.service import build_applications_query

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
    # Counts per stage and status in one grouped query: the columns and the
    # "Hired" card both read from it.
    counts = db.execute(
        select(on_board.c.current_stage_id, on_board.c.status, func.count()).group_by(
            on_board.c.current_stage_id, on_board.c.status
        )
    ).all()
    by_stage: dict = {}
    hired = 0
    for stage_id, status, count in counts:
        by_stage[stage_id] = by_stage.get(stage_id, 0) + count
        if status == ApplicationStatus.HIRED.value:
            hired += count
    # The cards as plain rows, names joined in, rather than 2,000 ORM objects
    # and a second query to name them.
    rows = db.execute(
        query.with_only_columns(
            Application.id,
            Application.candidate_id,
            Candidate.full_name,
            Application.job_id,
            Job.title,
            Application.current_stage_id,
            Application.status,
            Application.applied_at,
            maintain_column_froms=True,
        )
        .join(Candidate, Candidate.id == Application.candidate_id)
        .join(Job, Job.id == Application.job_id)
        .limit(limit)
    ).all()
    cards = [
        {
            "id": row[0],
            "candidate_id": row[1],
            "candidate_name": row[2],
            "job_id": row[3],
            "job_title": row[4],
            "current_stage_id": row[5],
            "status": row[6],
            "applied_at": row[7],
        }
        for row in rows
    ]
    return {
        "stage_counts": [{"stage_id": stage_id, "count": count} for stage_id, count in by_stage.items() if stage_id],
        "total": sum(by_stage.values()),
        "hired": hired,
        "cards": cards,
        "limit": limit,
    }
