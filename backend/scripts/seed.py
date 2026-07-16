"""Bootstrap script: seeds roles/permissions, the default organization, and
a super admin user. Safe to re-run — every step is idempotent.

Usage: python -m scripts.seed
"""

from sqlalchemy import select

from app.core.config import get_settings
from app.core.enums import RoleName
from app.db.models.organization import Organization, OrganizationSettings
from app.db.session import SessionLocal
from app.services.pipeline.service import seed_default_stage_template
from app.services.roles.service import seed_roles_and_permissions
from app.services.users.service import create_user, get_user_by_email


def run() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        seed_roles_and_permissions(db)

        org = db.scalar(select(Organization).where(Organization.slug == settings.default_org_slug))
        if org is None:
            org = Organization(name=settings.default_org_name, slug=settings.default_org_slug)
            db.add(org)
            db.flush()
            db.add(OrganizationSettings(organization_id=org.id))
            db.commit()
            print(f"Created organization '{org.name}' ({org.slug})")
        else:
            print(f"Organization '{org.name}' already exists")

        seed_default_stage_template(db, org.id)
        print("Ensured default pipeline stage template")

        existing_admin = get_user_by_email(db, org.id, settings.default_super_admin_email)
        if existing_admin is None:
            create_user(
                db,
                organization_id=org.id,
                email=settings.default_super_admin_email,
                full_name="Super Admin",
                password=settings.default_super_admin_password,
                role_names=[RoleName.SUPER_ADMIN.value],
            )
            print(f"Created super admin user '{settings.default_super_admin_email}'")
        else:
            print("Super admin user already exists")
    finally:
        db.close()


if __name__ == "__main__":
    run()
