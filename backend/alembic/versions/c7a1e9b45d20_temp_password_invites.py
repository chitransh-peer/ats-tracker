"""temporary password invitations

Adds the two columns that back the invite-by-temporary-password flow:
a flag that forces the holder through a password change before the API
will serve them anything else, and a deadline on the temporary password.

Existing users are backfilled with must_change_password = false, so nobody
already signed in is pushed into the change-password screen by this upgrade.

Revision ID: c7a1e9b45d20
Revises: fa491895e721
Create Date: 2026-09-16 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "c7a1e9b45d20"
down_revision: str | None = "fa491895e721"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default backfills the existing rows in the same statement; it is
    # dropped afterwards so the application default is the only one in play.
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("users", "must_change_password", server_default=None)
    op.add_column(
        "users",
        sa.Column("temp_password_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "temp_password_expires_at")
    op.drop_column("users", "must_change_password")
