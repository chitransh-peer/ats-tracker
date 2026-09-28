"""per-account login lockout

Adds the consecutive-failure counter and lock deadline behind the per-account
brute-force guard. Existing users start at zero failures and unlocked.

Revision ID: d8e2f4a61b37
Revises: c7a1e9b45d20
Create Date: 2026-09-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d8e2f4a61b37"
down_revision: str | None = "c7a1e9b45d20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("users", "failed_login_count", server_default=None)
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
