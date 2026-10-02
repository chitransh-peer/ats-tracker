"""careers-page application answers

The careers-page form now asks for profile, education, availability and
role-specific answers. They are kept on the application as asked.

Revision ID: c3e5a7b9d1f2
Revises: b7d9e1f3a5c2
Create Date: 2026-10-02 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c3e5a7b9d1f2"
down_revision: str | None = "b7d9e1f3a5c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("answers", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("applications", "answers")
