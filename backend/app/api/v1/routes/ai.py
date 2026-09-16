import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.config import get_settings
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.schemas.ai import (
    AIConfigRead,
    AIEvaluationOverrideRequest,
    AIEvaluationRead,
    JDResumeComparisonRead,
    ParseResumeRequest,
    ResumeParseRunRead,
)
from app.schemas.auth import CurrentUser
from app.services.ai import evaluation as evaluation_service
from app.services.ai import resume_parsing as resume_parsing_service
from app.services.audit.service import record as record_audit
from app.workers.dispatch import dispatch
from app.workers.tasks.ai import evaluate_application_task, parse_resume_task

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/config", response_model=AIConfigRead)
def ai_config(
    current_user: CurrentUser = Depends(require_permission(PermissionResource.SETTINGS, PermissionAction.READ)),
) -> AIConfigRead:
    """Read-only view of the active AI configuration. Deliberately excludes API
    keys — this is for confirming which model is scoring, not for managing secrets."""
    settings = get_settings()
    model = settings.ollama_model if settings.ai_provider == "ollama" else settings.openrouter_model
    return AIConfigRead(
        provider=settings.ai_provider,
        model=model or "not configured",
        embeddings_enabled=settings.embeddings_enabled,
        embeddings_model=settings.embeddings_model if settings.embeddings_enabled else None,
        evaluation_skill_weight=settings.evaluation_skill_weight,
    )


@router.post("/parse-resume", response_model=ResumeParseRunRead, status_code=202)
def parse_resume(
    payload: ParseResumeRequest,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.AI_EVALUATION, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> ResumeParseRunRead:
    run = resume_parsing_service.create_pending_run(
        db,
        organization_id=current_user.organization_id,
        candidate_id=payload.candidate_id,
        document_id=payload.document_id,
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.RESUME_PARSED.value,
        resource_type="resume_parse_run",
        resource_id=str(run.id),
    )
    db.commit()
    dispatch(parse_resume_task, str(run.id))
    return run


@router.get("/parse-runs/{run_id}", response_model=ResumeParseRunRead)
def get_parse_run(
    run_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.AI_EVALUATION, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> ResumeParseRunRead:
    return resume_parsing_service.get_parse_run(db, current_user.organization_id, run_id)


@router.post("/evaluate-application/{application_id}", response_model=AIEvaluationRead, status_code=202)
def evaluate_application(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.AI_EVALUATION, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> AIEvaluationRead:
    evaluation = evaluation_service.create_pending_evaluation(
        db, organization_id=current_user.organization_id, application_id=application_id, actor_id=current_user.id
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.AI_EVALUATION_TRIGGERED.value,
        resource_type="ai_evaluation",
        resource_id=str(evaluation.id),
    )
    db.commit()
    dispatch(evaluate_application_task, str(evaluation.id))
    return evaluation


@router.get("/evaluations/{evaluation_id}", response_model=AIEvaluationRead)
def get_evaluation(
    evaluation_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.AI_EVALUATION, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> AIEvaluationRead:
    return evaluation_service.get_evaluation(db, current_user.organization_id, evaluation_id)


@router.post("/evaluations/{evaluation_id}/override", response_model=AIEvaluationRead)
def override_evaluation(
    evaluation_id: uuid.UUID,
    payload: AIEvaluationOverrideRequest,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.AI_EVALUATION, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> AIEvaluationRead:
    evaluation = evaluation_service.get_evaluation(db, current_user.organization_id, evaluation_id)
    evaluation = evaluation_service.override_evaluation(
        db, evaluation, actor_id=current_user.id, new_recommendation=payload.recommendation_label, note=payload.note
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.AI_EVALUATION_OVERRIDDEN.value,
        resource_type="ai_evaluation",
        resource_id=str(evaluation.id),
        metadata={"recommendation_label": payload.recommendation_label},
    )
    db.commit()
    return evaluation


@router.get("/compare/jd-resume/{application_id}", response_model=JDResumeComparisonRead)
def compare_jd_resume(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.AI_EVALUATION, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> JDResumeComparisonRead:
    return evaluation_service.compare_jd_resume(db, current_user.organization_id, application_id)
