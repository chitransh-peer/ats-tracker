from fastapi import APIRouter, Depends
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session, require_permission, require_super_admin
from app.core.config import get_settings
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.organization import (
    EmailStatusRead,
    OrganizationRead,
    OrganizationSettingsUpdate,
    SystemStatusRead,
)
from app.services.audit.service import record as record_audit
from app.services.organizations import service as organization_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/email-status", response_model=EmailStatusRead)
def get_email_status(
    current_user: CurrentUser = Depends(get_current_user),
) -> EmailStatusRead:
    """Whether outbound email can actually leave the building. Excludes credentials.

    Open to any authenticated user rather than gated on settings:read — a recruiter
    composing candidate outreach needs to know whether it will actually be sent,
    and the payload holds no secrets.
    """
    settings = get_settings()
    return EmailStatusRead(
        enabled=settings.mail_enabled,
        smtp_host=settings.smtp_host or None,
        from_email=settings.mail_from_email,
        from_name=settings.mail_from_name,
        app_base_url=settings.app_base_url,
    )


@router.get("/system-status", response_model=SystemStatusRead)
def get_system_status(
    current_user: CurrentUser = Depends(require_super_admin),
) -> SystemStatusRead:
    """What this deployment is actually configured with.

    Managed runtimes hand you no shell and, often, no console access either, so
    "which environment variables did this revision actually get?" is otherwise
    unanswerable from outside. This reports that, restricted to Super Admin and
    limited to booleans and non-sensitive values -- whether a credential is
    present, never the credential itself.
    """
    settings = get_settings()

    url = make_url(settings.database_url)
    # A Cloud SQL unix socket carries no host; the instance is named in the
    # query string instead, which is worth showing since it is a common
    # misconfiguration. The password never leaves this function either way.
    socket_dir = url.query.get("host") if url.query else None
    database_host = url.host or (str(socket_dir) if socket_dir else None)

    return SystemStatusRead(
        app_env=settings.app_env,
        app_base_url=settings.app_base_url,
        cors_origins=settings.cors_origin_list,
        mail_enabled=settings.mail_enabled,
        smtp_host=settings.smtp_host or None,
        smtp_port=settings.smtp_port,
        smtp_credentials_set=bool(settings.smtp_username and settings.smtp_password),
        mail_from_email=settings.mail_from_email,
        ai_provider=settings.ai_provider,
        ai_model=(
            settings.openrouter_model or None if settings.ai_provider == "openrouter" else settings.ollama_model or None
        ),
        ai_credentials_set=(bool(settings.openrouter_api_key) if settings.ai_provider == "openrouter" else True),
        storage_backend=settings.storage_backend,
        storage_endpoint_url=settings.storage_endpoint_url or None,
        storage_bucket=settings.storage_bucket,
        # On the gcs backend there is no key pair by design: the container
        # authenticates as its own service account, so "configured" means the
        # backend is selected, not that a secret was supplied.
        storage_credentials_set=(
            True
            if settings.storage_backend.lower() == "gcs"
            else bool(settings.storage_access_key and settings.storage_secret_key)
        ),
        # The default points at a localhost Redis that does not exist on a
        # managed runtime, so treat that as "not configured" rather than as a
        # real broker -- it is the difference between queued work running and
        # silently never running.
        redis_configured=bool(settings.redis_url)
        and "localhost" not in settings.redis_url
        and "127.0.0.1" not in settings.redis_url,
        embeddings_enabled=settings.embeddings_enabled,
        database_backend=url.drivername,
        database_host=database_host,
    )


@router.get("/organization", response_model=OrganizationRead)
def get_organization_settings(
    current_user: CurrentUser = Depends(require_permission(PermissionResource.SETTINGS, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> OrganizationRead:
    return organization_service.get_organization(db, current_user.organization_id)


@router.patch("/organization", response_model=OrganizationRead)
def update_organization_settings(
    payload: OrganizationSettingsUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.SETTINGS, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OrganizationRead:
    org = organization_service.get_organization(db, current_user.organization_id)
    org = organization_service.update_settings(db, org, **payload.model_dump(exclude_unset=True))
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.SETTINGS_CHANGED.value,
        resource_type="organization",
        resource_id=str(org.id),
        metadata=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    return org
