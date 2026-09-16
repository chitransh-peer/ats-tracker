from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.core.config import get_settings
from app.core.enums import AuditAction, RoleName
from app.core.exceptions import ForbiddenError, ValidationAppError
from app.core.rate_limit import limiter
from app.core.security import create_view_as_token
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUser,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPair,
    ViewAsRequest,
    ViewAsResponse,
)
from app.schemas.user import UserRead
from app.services.audit.service import record as record_audit
from app.services.auth import service as auth_service
from app.services.mail import messages as mail_messages
from app.services.users.service import get_user_by_id, role_names_for_user
from app.workers.dispatch import dispatch
from app.workers.tasks.mail import send_email_task

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db_session)) -> TokenPair:
    access_token, refresh_token = auth_service.login(
        db, email=payload.email, password=payload.password, ip_address=request.client.host if request.client else None
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db_session)) -> TokenPair:
    access_token, refresh_token = auth_service.refresh(db, refresh_token=payload.refresh_token)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
def logout(payload: LogoutRequest, db: Session = Depends(get_db_session)) -> None:
    auth_service.logout(db, refresh_token=payload.refresh_token)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit("5/minute")
def forgot_password(
    request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db_session)
) -> ForgotPasswordResponse:
    expires_in_minutes = 30
    raw_token = auth_service.request_password_reset(db, email=payload.email, expires_in_minutes=expires_in_minutes)

    settings = get_settings()

    # raw_token is None when no active account matched. Queue mail only when it
    # did, but keep the response identical either way so the endpoint can't be
    # used to probe which addresses have accounts.
    if raw_token is not None:
        subject, text_body, html_body = mail_messages.password_reset(token=raw_token, expires_in_minutes=expires_in_minutes)
        # allow_inline: without this mail the user cannot reset their password.
        dispatch(send_email_task, payload.email, subject, text_body, html_body, allow_inline=True)

    # Never hand the token back in production, whatever the flag says.
    expose = settings.expose_password_reset_token and settings.app_env != "production"

    return ForgotPasswordResponse(
        detail="If an account exists for that email, a password reset link has been issued.",
        reset_token=raw_token if expose else None,
    )


@router.post("/reset-password", status_code=204)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db_session)) -> None:
    auth_service.reset_password(db, token=payload.token, new_password=payload.new_password)


@router.post("/change-password", response_model=TokenPair)
def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TokenPair:
    """Set your own password, completing an invitation if one is outstanding.

    Reachable while must_change_password is set — see the exempt paths in
    app/api/deps.py — so an invited user can get themselves out of that state.

    Returns a fresh token pair because changing the password revokes every
    existing refresh token, and because the old access token still carries the
    stale must_change_password claim that would keep the gate closed.
    """
    user = get_user_by_id(db, current_user.organization_id, current_user.id)
    completed_invitation = auth_service.change_password(
        db,
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )

    if completed_invitation:
        # Confirmation that the account is live. Carries no credential, and gives
        # the person a way to react if it wasn't them who activated it.
        subject, text_body, html_body = mail_messages.account_created(
            full_name=user.full_name, email=user.email, role_names=role_names_for_user(user)
        )
        dispatch(send_email_task, user.email, subject, text_body, html_body, allow_inline=True)

    access_token, refresh_token = auth_service.issue_tokens_for(db, user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/view-as", response_model=ViewAsResponse)
def view_as(
    payload: ViewAsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ViewAsResponse:
    if RoleName.SUPER_ADMIN.value not in current_user.roles:
        raise ForbiddenError("Only Super Admin can preview other roles")
    try:
        role = RoleName(payload.role_name)
    except ValueError:
        raise ValidationAppError(f"Unknown role: {payload.role_name}") from None

    token = create_view_as_token(str(current_user.id), str(current_user.organization_id), role.value)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.VIEW_AS_STARTED.value,
        resource_type="user",
        resource_id=str(current_user.id),
        metadata={"role_name": role.value},
    )
    db.commit()
    return ViewAsResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def me(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db_session)) -> UserRead:
    user = get_user_by_id(db, current_user.organization_id, current_user.id)
    return UserRead(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        roles=role_names_for_user(user),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
