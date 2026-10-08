"""Ceipal profile edits

Recruiters can now correct a migrated Ceipal record. `edited_columns` lists
the Ceipal headers they corrected, so re-importing a later backup keeps the
correction instead of restoring Ceipal's copy.

Revision ID: a7c9e1f3b5d7
Revises: f6b8d0c2e4a5
Create Date: 2026-10-08 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a7c9e1f3b5d7"
down_revision: str | None = "f6b8d0c2e4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ceipal_profiles",
        sa.Column("edited_columns", postgresql.JSONB(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("ceipal_profiles", "edited_columns")
