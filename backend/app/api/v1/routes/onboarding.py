import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.onboarding import (
    OnboardingCaseRead,
    OnboardingCaseUpdate,
    OnboardingTaskCreate,
    OnboardingTaskRead,
    OnboardingTaskUpdate,
)
from app.services.audit.service import record as record_audit
from app.services.onboarding import service as onboarding_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("", response_model=list[OnboardingCaseRead])
def list_cases(
    status: str | None = None,
    application_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.ONBOARDING, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[OnboardingCaseRead]:
    return onboarding_service.list_cases(
        db, current_user.organization_id, status=status, application_id=application_id, viewer=current_user
    )


@router.get("/{case_id}", response_model=OnboardingCaseRead)
def get_case(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.ONBOARDING, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> OnboardingCaseRead:
    return onboarding_service.get_case(db, current_user.organization_id, case_id, viewer=current_user)


@router.patch("/{case_id}", response_model=OnboardingCaseRead)
def update_case(
    case_id: uuid.UUID,
    payload: OnboardingCaseUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.ONBOARDING, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OnboardingCaseRead:
    case = onboarding_service.get_case(db, current_user.organization_id, case_id, viewer=current_user)
    case = onboarding_service.update_case(
        db, case, actor_id=current_user.id, **payload.model_dump(exclude_unset=True)
    )
    db.commit()
    return case


@router.post("/{case_id}/complete", response_model=OnboardingCaseRead)
def complete_case(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.ONBOARDING, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OnboardingCaseRead:
    case = onboarding_service.get_case(db, current_user.organization_id, case_id, viewer=current_user)
    case = onboarding_service.complete_case(db, case)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.ONBOARDING_COMPLETED.value,
        resource_type="onboarding_case",
        resource_id=str(case.id),
    )
    db.commit()
    return case


@router.post("/{case_id}/cancel", response_model=OnboardingCaseRead)
def cancel_case(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.ONBOARDING, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OnboardingCaseRead:
    case = onboarding_service.get_case(db, current_user.organization_id, case_id, viewer=current_user)
    case = onboarding_service.cancel_case(db, case)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.ONBOARDING_CANCELLED.value,
        resource_type="onboarding_case",
        resource_id=str(case.id),
    )
    db.commit()
    return case


@router.post("/{case_id}/tasks", response_model=OnboardingTaskRead, status_code=201)
def add_task(
    case_id: uuid.UUID,
    payload: OnboardingTaskCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.ONBOARDING, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OnboardingTaskRead:
    case = onboarding_service.get_case(db, current_user.organization_id, case_id, viewer=current_user)
    task = onboarding_service.add_task(db, case, **payload.model_dump())
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.ONBOARDING_TASK_ADDED.value,
        resource_type="onboarding_task",
        resource_id=str(task.id),
    )
    db.commit()
    return task


@router.patch("/tasks/{task_id}", response_model=OnboardingTaskRead)
def update_task(
    task_id: uuid.UUID,
    payload: OnboardingTaskUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.ONBOARDING, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> OnboardingTaskRead:
    task = onboarding_service.get_task(db, current_user.organization_id, task_id)
    task = onboarding_service.update_task(db, task, **payload.model_dump(exclude_unset=True))
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.ONBOARDING_TASK_UPDATED.value,
        resource_type="onboarding_task",
        resource_id=str(task.id),
    )
    db.commit()
    return task
