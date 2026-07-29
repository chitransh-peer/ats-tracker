import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.schemas.ai import AIEvaluationRead
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListItem,
    ApplicationRead,
    ApplicationStageHistoryRead,
)
from app.schemas.auth import CurrentUser
from app.schemas.pipeline import MoveStageRequest, StageActionRequest
from app.services.ai import evaluation as ai_evaluation_service
from app.services.applications import service as application_service
from app.services.audit.service import record as record_audit
from app.services.pipeline import service as pipeline_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationListItem])
def list_applications(
    job_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    status: str | None = None,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.APPLICATION, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[ApplicationListItem]:
    applications = application_service.list_applications(
        db, current_user.organization_id, job_id=job_id, candidate_id=candidate_id, status=status, viewer=current_user
    )
    scores = ai_evaluation_service.latest_scores(
        db, current_user.organization_id, [a.id for a in applications]
    )
    items: list[ApplicationListItem] = []
    for application in applications:
        score, recommendation = scores.get(application.id, (None, None))
        item = ApplicationListItem.model_validate(application)
        item.ai_score = score
        item.ai_recommendation = recommendation
        items.append(item)
    return items


@router.post("", response_model=ApplicationRead, status_code=201)
def create_application(
    payload: ApplicationCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.APPLICATION, PermissionAction.CREATE)),
    db: Session = Depends(get_db_session),
) -> ApplicationRead:
    application = application_service.create_application(
        db,
        organization_id=current_user.organization_id,
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        source=payload.source,
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.APPLICATION_CREATED.value,
        resource_type="application",
        resource_id=str(application.id),
    )
    db.commit()
    return application


@router.get("/{application_id}", response_model=ApplicationRead)
def get_application(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.APPLICATION, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> ApplicationRead:
    return application_service.get_application(db, current_user.organization_id, application_id, viewer=current_user)


@router.get("/{application_id}/timeline", response_model=list[ApplicationStageHistoryRead])
def get_timeline(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.APPLICATION, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[ApplicationStageHistoryRead]:
    application = application_service.get_application(db, current_user.organization_id, application_id, viewer=current_user)
    return application_service.get_timeline(db, application)


@router.get("/{application_id}/ai-review", response_model=AIEvaluationRead)
def get_ai_review(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.AI_EVALUATION, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> AIEvaluationRead:
    return ai_evaluation_service.get_latest_evaluation(db, current_user.organization_id, application_id)


@router.post("/{application_id}/move-stage", response_model=ApplicationRead)
def move_stage(
    application_id: uuid.UUID,
    payload: MoveStageRequest,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.PIPELINE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> ApplicationRead:
    application = application_service.get_application(db, current_user.organization_id, application_id, viewer=current_user)
    application = pipeline_service.move_stage(
        db, application, to_stage_id=payload.to_stage_id, actor_id=current_user.id, note=payload.note
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.APPLICATION_STAGE_MOVED.value,
        resource_type="application",
        resource_id=str(application.id),
        metadata={"to_stage_id": str(payload.to_stage_id)},
    )
    db.commit()
    return application


@router.post("/{application_id}/hold", response_model=ApplicationRead)
def hold_application(
    application_id: uuid.UUID,
    payload: StageActionRequest,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.PIPELINE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> ApplicationRead:
    application = application_service.get_application(db, current_user.organization_id, application_id, viewer=current_user)
    application = pipeline_service.hold_application(db, application, actor_id=current_user.id, note=payload.note)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.APPLICATION_HELD.value,
        resource_type="application",
        resource_id=str(application.id),
    )
    db.commit()
    return application


@router.post("/{application_id}/reject", response_model=ApplicationRead)
def reject_application(
    application_id: uuid.UUID,
    payload: StageActionRequest,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.PIPELINE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> ApplicationRead:
    application = application_service.get_application(db, current_user.organization_id, application_id, viewer=current_user)
    application = pipeline_service.reject_application(db, application, actor_id=current_user.id, note=payload.note)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.APPLICATION_REJECTED.value,
        resource_type="application",
        resource_id=str(application.id),
    )
    db.commit()
    return application


@router.post("/{application_id}/restore", response_model=ApplicationRead)
def restore_application(
    application_id: uuid.UUID,
    payload: StageActionRequest,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.PIPELINE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> ApplicationRead:
    application = application_service.get_application(db, current_user.organization_id, application_id, viewer=current_user)
    application = pipeline_service.restore_application(db, application, actor_id=current_user.id, note=payload.note)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.APPLICATION_RESTORED.value,
        resource_type="application",
        resource_id=str(application.id),
    )
    db.commit()
    return application
