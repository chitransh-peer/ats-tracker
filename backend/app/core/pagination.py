"""Shared offset pagination for list endpoints.

Every list endpoint used to return every row in the table — fine at pilot
scale, but the first thing to break once a real client's candidate database
lands in this system. Endpoints that expect to grow past a couple hundred
rows should use this rather than returning `list[db.scalars(query).all()]`
directly.

The response body stays a plain JSON array (no envelope), so this is a
non-breaking addition for any existing caller: the total row count instead
rides on the `X-Total-Count` response header, which a frontend can read to
decide whether more pages exist.
"""

from dataclasses import dataclass
from typing import TypeVar

from fastapi import Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

T = TypeVar("T")


@dataclass
class PageParams:
    limit: int
    offset: int


def page_params(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> PageParams:
    """FastAPI dependency: `limit`/`offset` query params, clamped to sane bounds."""
    return PageParams(limit=limit, offset=offset)


def paginate(db: Session, query: Select, params: PageParams) -> tuple[list, int]:
    """Run `query` for one page plus a total count of all matching rows.

    `query` should carry filters and eager-load options but not its own
    `.limit()`/`.offset()` — those are applied here. Ordering is preserved for
    the page query and stripped only for the count subquery.
    """
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = list(db.scalars(query.limit(params.limit).offset(params.offset)).unique().all())
    return rows, total
