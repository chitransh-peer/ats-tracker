"""Ceipal backup import: candidates with their résumés

Adds `candidates.origin` (set to "ceipal" for candidates brought in from a
Ceipal backup, which are never AI-scored), the import job and its staged
rows, and the per-candidate Ceipal profile the Ceipal view of the candidate
list is drawn from.

Revision ID: d4f6a8c0e2b3
Revises: c3e5a7b9d1f2
Create Date: 2026-10-07 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4f6a8c0e2b3"
down_revision: str | None = "c3e5a7b9d1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("candidates", sa.Column("origin", sa.String(length=20), nullable=True))
    op.create_index("ix_candidates_origin", "candidates", ["origin"])

    op.create_table(
        "ceipal_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("applicants_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applicants_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_expected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_attached", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_orphaned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("education_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("submissions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("submissions_linked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("kept_on_undo", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ceipal_imports_organization_id", "ceipal_imports", ["organization_id"])

    op.create_table(
        "ceipal_rows",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "import_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ceipal_imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("ref", sa.String(length=100)),
        sa.Column("key", sa.String(length=500)),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text()),
        sa.Column("record_id", postgresql.UUID(as_uuid=True)),
        sa.UniqueConstraint("import_id", "kind", "source", "row_number", name="uq_ceipal_rows_position"),
    )
    op.create_index("ix_ceipal_rows_import_kind_ref", "ceipal_rows", ["import_id", "kind", "ref"])
    op.create_index("ix_ceipal_rows_import_kind_key", "ceipal_rows", ["import_id", "kind", "key"])
    op.create_index("ix_ceipal_rows_import_kind_status", "ceipal_rows", ["import_id", "kind", "status", "id"])

    op.create_table(
        "ceipal_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("ceipal_id", sa.String(length=100), nullable=False),
        sa.Column("fields", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("submissions", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "resume_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_documents.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_import_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ceipal_imports.id", ondelete="SET NULL"),
        ),
        sa.Column("candidate_created", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "last_import_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ceipal_imports.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "ceipal_id", name="uq_ceipal_profiles_org_ceipal_id"),
    )
    op.create_index("ix_ceipal_profiles_organization_id", "ceipal_profiles", ["organization_id"])
    op.create_index("ix_ceipal_profiles_created_import_id", "ceipal_profiles", ["created_import_id"])


def downgrade() -> None:
    op.drop_table("ceipal_profiles")
    op.drop_table("ceipal_rows")
    op.drop_table("ceipal_imports")
    op.drop_index("ix_candidates_origin", table_name="candidates")
    op.drop_column("candidates", "origin")
