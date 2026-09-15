"""client master fields

Revision ID: b1c2d3e4f5a6
Revises: f35477b12fcb
Create Date: 2026-08-07 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "f35477b12fcb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("client_code", sa.String(length=50), nullable=True))
    op.add_column("clients", sa.Column("contact_number", sa.String(length=50), nullable=True))
    op.add_column("clients", sa.Column("website", sa.String(length=255), nullable=True))
    op.add_column("clients", sa.Column("category", sa.String(length=50), nullable=True))
    op.add_column("clients", sa.Column("primary_owner_id", sa.UUID(), nullable=True))
    op.add_column("clients", sa.Column("business_unit", sa.String(length=100), nullable=True))
    op.add_column("clients", sa.Column("primary_business_unit", sa.String(length=100), nullable=True))
    op.add_column(
        "clients",
        sa.Column("display_on_job_posting", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("clients", sa.Column("created_by", sa.UUID(), nullable=True))
    op.add_column("clients", sa.Column("updated_by", sa.UUID(), nullable=True))

    # Backfill client_code for existing rows: CLI-<year><4-digit seq per organization>.
    op.execute(
        """
        UPDATE clients c
        SET client_code = 'CLI-' || to_char(c.created_at, 'YYYY') || lpad(s.seq::text, 4, '0')
        FROM (
            SELECT id, row_number() OVER (PARTITION BY organization_id ORDER BY created_at, id) AS seq
            FROM clients
        ) s
        WHERE s.id = c.id AND c.client_code IS NULL
        """
    )
    op.alter_column("clients", "client_code", nullable=False)

    op.create_index(op.f("ix_clients_client_code"), "clients", ["client_code"], unique=False)
    op.create_unique_constraint("uq_clients_org_client_code", "clients", ["organization_id", "client_code"])
    op.create_foreign_key(
        "fk_clients_primary_owner_id_users", "clients", "users", ["primary_owner_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key("fk_clients_created_by_users", "clients", "users", ["created_by"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_clients_updated_by_users", "clients", "users", ["updated_by"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_clients_updated_by_users", "clients", type_="foreignkey")
    op.drop_constraint("fk_clients_created_by_users", "clients", type_="foreignkey")
    op.drop_constraint("fk_clients_primary_owner_id_users", "clients", type_="foreignkey")
    op.drop_constraint("uq_clients_org_client_code", "clients", type_="unique")
    op.drop_index(op.f("ix_clients_client_code"), table_name="clients")
    for column in (
        "updated_by",
        "created_by",
        "display_on_job_posting",
        "primary_business_unit",
        "business_unit",
        "primary_owner_id",
        "category",
        "website",
        "contact_number",
        "client_code",
    ):
        op.drop_column("clients", column)
