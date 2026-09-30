"""indexes behind the paged lists, the board and the SQL reports

Phase 3 moved the jobs, interviews, offers, onboarding and hotlist lists to
server-side paging, newest first, and moved the funnel, trend and
time-to-fill reports into single grouped queries. Each of those orders or
joins on a column pair no index covered, so at volume every page and report
would sort or scan the whole table. Job search (title, job code) gets the
same trigram indexes the candidate, vendor and client searches already have.

As in e3f9a1c5d7b2, a missing pg_trgm extension skips only the trigram
indexes; the plain ones are created either way.

Revision ID: b7d9e1f3a5c2
Revises: a2c4e6f8b0d1
Create Date: 2026-09-30 12:00:00.000000

"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7d9e1f3a5c2"
down_revision: str | None = "a2c4e6f8b0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger("alembic.runtime.migration")

_PLAIN_INDEXES = [
    # Newest-first list pages.
    ("ix_jobs_org_created_at", "jobs", ["organization_id", "created_at"]),
    ("ix_applications_org_applied_at", "applications", ["organization_id", "applied_at"]),
    ("ix_interviews_org_scheduled_at", "interviews", ["organization_id", "scheduled_at"]),
    ("ix_offers_org_created_at", "offers", ["organization_id", "created_at"]),
    ("ix_onboarding_cases_org_created_at", "onboarding_cases", ["organization_id", "created_at"]),
    ("ix_hotlists_org_created_at", "hotlists", ["organization_id", "created_at"]),
    # Board stage counts and the funnel's current-stage join.
    ("ix_applications_current_stage_id", "applications", ["current_stage_id"]),
    # Hires by stage, for the hiring trend and time to fill.
    ("ix_application_stage_history_to_stage_id", "application_stage_history", ["to_stage_id"]),
]

_TRIGRAM_INDEXES = [
    ("ix_jobs_title_trgm", "jobs", "title"),
    ("ix_jobs_req_id_trgm", "jobs", "req_id"),
]


def _trigram_available() -> bool:
    bind = op.get_bind()
    savepoint = bind.begin_nested()
    try:
        bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        savepoint.commit()
        return True
    except Exception as exc:  # noqa: BLE001 -- any failure means "not available here"
        savepoint.rollback()
        logger.warning("pg_trgm unavailable (%s); skipping trigram job search indexes.", exc)
        return False


def upgrade() -> None:
    for name, table, columns in _PLAIN_INDEXES:
        op.create_index(name, table, columns, if_not_exists=True)

    if _trigram_available():
        for name, table, column in _TRIGRAM_INDEXES:
            op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} USING gin ({column} gin_trgm_ops)")


def downgrade() -> None:
    for name, _table, _column in _TRIGRAM_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
    for name, table, _columns in _PLAIN_INDEXES:
        op.drop_index(name, table_name=table, if_exists=True)
