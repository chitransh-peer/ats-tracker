"""search and listing indexes for bulk-imported volumes

A Ceipal import brings in ~100,000 candidates, ~50,000 vendors and ~10,000
clients. The list pages search those with a case-insensitive "contains"
(ILIKE '%term%'), which no ordinary b-tree index can serve, so every keystroke
in a search box scanned the whole table. Trigram (pg_trgm) GIN indexes serve
exactly that query shape.

Also adds the indexes behind duplicate detection on import (candidate phone,
which had none) and behind the lists' default newest-first ordering.

pg_trgm ships with Postgres and is on Cloud SQL's supported-extension list, but
creating an extension needs a privilege the database user might lack. That is
not a reason to stop the app booting -- this migration runs on startup -- so if
the extension cannot be created the trigram indexes are skipped and search
simply stays as it was. The plain indexes are created either way.

Revision ID: e3f9a1c5d7b2
Revises: d8e2f4a61b37
Create Date: 2026-09-30 00:00:00.000000

"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e3f9a1c5d7b2"
down_revision: str | None = "d8e2f4a61b37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger("alembic.runtime.migration")

# (index name, table, column) for every column a list search box matches on.
_TRIGRAM_INDEXES = [
    ("ix_candidates_full_name_trgm", "candidates", "full_name"),
    ("ix_candidates_email_trgm", "candidates", "email"),
    ("ix_vendors_name_trgm", "vendors", "name"),
    ("ix_vendors_state_trgm", "vendors", "state"),
    ("ix_vendors_country_trgm", "vendors", "country"),
    ("ix_clients_name_trgm", "clients", "name"),
    ("ix_clients_client_code_trgm", "clients", "client_code"),
    ("ix_clients_industry_trgm", "clients", "industry"),
]

_PLAIN_INDEXES = [
    ("ix_candidates_org_phone", "candidates", ["organization_id", "phone"]),
    ("ix_candidates_org_created_at", "candidates", ["organization_id", "created_at"]),
    ("ix_vendors_org_created_at", "vendors", ["organization_id", "created_at"]),
    ("ix_clients_org_created_at", "clients", ["organization_id", "created_at"]),
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
        logger.warning("pg_trgm unavailable (%s); skipping trigram search indexes.", exc)
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
