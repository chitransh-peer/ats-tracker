"""Offer pay terms and interview logistics

Offers gain a pay type (salary or hourly), an hourly rate, a currency, the
employment type and terms (W-2 / 1099 / C2C / India payroll or contract) and a
contract duration, so contracts and India hires can be offered; the base salary
becomes optional because an hourly offer has none. Offer versions snapshot the
same fields.

Interviews gain the time zone they were scheduled in, a duration, a meeting
link and a location, for coordinating panels across the US and India.

Revision ID: e5a7c9b1d3f4
Revises: d4f6a8c0e2b3
Create Date: 2026-10-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5a7c9b1d3f4"
down_revision: str | None = "d4f6a8c0e2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _offer_term_columns() -> list[sa.Column]:
    return [
        sa.Column("pay_type", sa.String(length=10), nullable=False, server_default="Salary"),
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("employment_type", sa.String(length=30), nullable=True),
        sa.Column("tax_term", sa.String(length=30), nullable=True),
        sa.Column("contract_duration", sa.String(length=100), nullable=True),
    ]


def upgrade() -> None:
    for table in ("offers", "offer_versions"):
        for column in _offer_term_columns():
            op.add_column(table, column)
        op.alter_column(table, "base_salary", existing_type=sa.Integer(), nullable=True)

    op.add_column("interviews", sa.Column("timezone", sa.String(length=64), nullable=True))
    op.add_column("interviews", sa.Column("duration_minutes", sa.Integer(), nullable=True))
    op.add_column("interviews", sa.Column("meeting_link", sa.String(length=1000), nullable=True))
    op.add_column("interviews", sa.Column("location", sa.String(length=500), nullable=True))


def downgrade() -> None:
    for column in ("location", "meeting_link", "duration_minutes", "timezone"):
        op.drop_column("interviews", column)

    for table in ("offers", "offer_versions"):
        # Hourly offers have no base salary; zero keeps the NOT NULL restorable.
        op.execute(sa.text(f"UPDATE {table} SET base_salary = 0 WHERE base_salary IS NULL"))
        op.alter_column(table, "base_salary", existing_type=sa.Integer(), nullable=False)
        for column in ("contract_duration", "tax_term", "employment_type", "currency", "hourly_rate", "pay_type"):
            op.drop_column(table, column)
