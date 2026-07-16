from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.schemas.auth import (
    CurrentUser,
    ForgotPasswordRequest,
    InviteAcceptRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPair,
)
from app.schemas.user import UserRead
from app.services.auth import service as auth_service
from app.services.users.service import get_user_by_id, role_names_for_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db_session)) -> TokenPair:
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


@router.post("/forgot-password", status_code=204)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db_session)) -> None:
    auth_service.request_password_reset(db, email=payload.email)


@router.post("/reset-password", status_code=204)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db_session)) -> None:
    auth_service.reset_password(db, token=payload.token, new_password=payload.new_password)


@router.post("/invite/accept", response_model=UserRead, status_code=201)
def accept_invite(payload: InviteAcceptRequest, db: Session = Depends(get_db_session)) -> UserRead:
    user = auth_service.accept_invitation(
        db, token=payload.token, full_name=payload.full_name, password=payload.password
    )
    return UserRead(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=role_names_for_user(user),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/me", response_model=UserRead)
def me(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db_session)) -> UserRead:
    user = get_user_by_id(db, current_user.organization_id, current_user.id)
    return UserRead(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=role_names_for_user(user),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
