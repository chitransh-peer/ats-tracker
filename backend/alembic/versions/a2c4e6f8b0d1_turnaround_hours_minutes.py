"""turnaround time accepts hours and minutes

A turnaround "In Hours" can now be entered as hours:minutes (4:30), stored as
fractional hours (4.5). Existing whole-number values convert unchanged.

Revision ID: a2c4e6f8b0d1
Revises: f7b3c9d2e8a4
Create Date: 2026-09-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a2c4e6f8b0d1"
down_revision: str | None = "f7b3c9d2e8a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "jobs",
        "turnaround_time_value",
        existing_type=sa.Integer(),
        type_=sa.Numeric(8, 2),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Rounds any hours-and-minutes value to the nearest whole number.
    op.alter_column(
        "jobs",
        "turnaround_time_value",
        existing_type=sa.Numeric(8, 2),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="round(turnaround_time_value)::integer",
    )
