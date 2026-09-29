"""bulk import: import jobs, staged rows, saved mappings

Adds the tables behind CSV/JSON/Excel import, and on each importable table a
link back to the import that created a row so that import can be undone.

Candidates also gain `external_id` (the id in the system they came from, e.g.
a Ceipal Applicant ID, so re-importing the same export matches rather than
duplicates) and lose the NOT NULL on email: exported records do not always
have one, and they are imported with a "Missing email" tag instead of being
dropped. Nothing that creates candidates inside the app stops requiring it.

Revision ID: f7b3c9d2e8a4
Revises: e3f9a1c5d7b2
Create Date: 2026-09-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f7b3c9d2e8a4"
down_revision: str | None = "e3f9a1c5d7b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_IMPORTABLE_TABLES = ["candidates", "vendors", "clients", "jobs", "bench_profiles"]


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("columns", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("mapping", postgresql.JSONB(), nullable=False),
        sa.Column("duplicate_mode", sa.String(10), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("processed_rows", sa.Integer(), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("kept_on_undo", sa.Integer(), nullable=False),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_import_jobs_organization_id", "import_jobs", ["organization_id"])

    op.create_table(
        "import_rows",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "import_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("import_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_import_rows_job_status_row", "import_rows", ["import_job_id", "status", "row_number"])

    op.create_table(
        "import_presets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity", sa.String(30), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("mapping", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "entity", "name", name="uq_import_presets_org_entity_name"),
    )
    op.create_index("ix_import_presets_organization_id", "import_presets", ["organization_id"])

    for table in _IMPORTABLE_TABLES:
        op.add_column(
            table,
            sa.Column(
                "import_job_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("import_jobs.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(f"ix_{table}_import_job_id", table, ["import_job_id"])

    op.add_column("candidates", sa.Column("external_id", sa.String(100), nullable=True))
    op.create_index("ix_candidates_org_external_id", "candidates", ["organization_id", "external_id"])
    op.alter_column("candidates", "email", existing_type=sa.String(255), nullable=True)
    # Duplicate matching on import compares phones by their last ten digits, so
    # "+1 (555) 010-2030" matches "5550102030". Without this, every import
    # chunk scanned the whole candidate table to compare them.
    # Vendors and clients are matched on import by case-insensitive name.
    op.execute("CREATE INDEX IF NOT EXISTS ix_vendors_org_lower_name ON vendors (organization_id, lower(name))")
    op.execute("CREATE INDEX IF NOT EXISTS ix_clients_org_lower_name ON clients (organization_id, lower(name))")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_candidates_org_phone_digits ON candidates "
        r"(organization_id, (right(regexp_replace(phone, '\D', '', 'g'), 10)))"
    )


def downgrade() -> None:
    # Refuses, rather than inventing addresses, if email-less candidates exist.
    op.execute("DROP INDEX IF EXISTS ix_candidates_org_phone_digits")
    op.execute("DROP INDEX IF EXISTS ix_vendors_org_lower_name")
    op.execute("DROP INDEX IF EXISTS ix_clients_org_lower_name")
    op.alter_column("candidates", "email", existing_type=sa.String(255), nullable=False)
    op.drop_index("ix_candidates_org_external_id", table_name="candidates")
    op.drop_column("candidates", "external_id")
    for table in _IMPORTABLE_TABLES:
        op.drop_index(f"ix_{table}_import_job_id", table_name=table)
        op.drop_column(table, "import_job_id")
    op.drop_table("import_presets")
    op.drop_table("import_rows")
    op.drop_table("import_jobs")
