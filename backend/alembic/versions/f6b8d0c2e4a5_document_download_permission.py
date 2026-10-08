"""Document download permission

Downloading an original document file becomes its own permission,
`document_download`, so recruiters and other roles can read résumés and
documents in the in-app preview without being able to take a copy.

Role defaults are only applied to roles the seeder creates, and every
deployment already has its roles, so the grant the new defaults call for is
made here: Super Admin gets `manage`, Admin the four plain actions -- the same
as app/core/permissions.py. No other role is granted it; an admin can still
grant it to any role from the role editor.

Revision ID: f6b8d0c2e4a5
Revises: e5a7c9b1d3f4
Create Date: 2026-10-08 13:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6b8d0c2e4a5"
down_revision: str | None = "e5a7c9b1d3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RESOURCE = "document_download"
GRANTS = {
    "super_admin": ["manage"],
    "admin": ["create", "read", "update", "delete"],
}


def upgrade() -> None:
    bind = op.get_bind()
    for actions in GRANTS.values():
        for action in actions:
            bind.execute(
                sa.text(
                    "INSERT INTO permissions (id, resource, action) VALUES (:id, :resource, :action) "
                    "ON CONFLICT ON CONSTRAINT uq_permissions_resource_action DO NOTHING"
                ),
                {"id": uuid.uuid4(), "resource": RESOURCE, "action": action},
            )
    for role, actions in GRANTS.items():
        bind.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "SELECT r.id, p.id FROM roles r JOIN permissions p "
                "ON p.resource = :resource AND p.action = ANY(:actions) "
                "WHERE r.name = :role "
                "ON CONFLICT DO NOTHING"
            ),
            {"resource": RESOURCE, "actions": actions, "role": role},
        )


def downgrade() -> None:
    # Cascades to role_permissions.
    op.execute(sa.text(f"DELETE FROM permissions WHERE resource = '{RESOURCE}'"))
