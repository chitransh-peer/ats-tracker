import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.core.exceptions import AppError
from app.core.pagination import MAX_LIMIT
from app.schemas.ai import AIEvaluationRead
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListItem,
    ApplicationOption,
    ApplicationRead,
    ApplicationStageHistoryRead,
    BulkActionFailure,
    BulkActionResult,
    BulkApplicationActionRequest,
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
    response: Response,
    job_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None,
    # Pagination is opt-in: every list page passes `page_size`. Omitting it
    # returns up to 2,000 rows, for callers with a narrow filter such as one
    # candidate's applications.
    page_size: int | None = None,
    offset: int = 0,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.APPLICATION, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[ApplicationListItem]:
    if page_size is not None:
        page_size = max(1, min(page_size, MAX_LIMIT))
        query = application_service.build_applications_query(
            current_user.organization_id,
            job_id=job_id,
            candidate_id=candidate_id,
            status=status,
            search=search,
            viewer=current_user,
        )
        total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
        applications = list(db.scalars(query.limit(page_size).offset(offset)).unique().all())
        response.headers["X-Total-Count"] = str(total)
    else:
        applications = application_service.list_applications(
            db, current_user.organization_id, job_id=job_id, candidate_id=candidate_id, status=status, viewer=current_user
        )

    ids = [a.id for a in applications]
    scores = ai_evaluation_service.latest_scores(db, current_user.organization_id, ids)
    labels = application_service.application_labels(db, ids)
    items: list[ApplicationListItem] = []
    for application in applications:
        score, recommendation = scores.get(application.id, (None, None))
        item = ApplicationListItem.model_validate(application)
        item.ai_score = score
        item.ai_recommendation = recommendation
        label = labels.get(application.id, {})
        item.candidate_name = label.get("candidate_name")
        item.job_title = label.get("job_title")
        item.job_req_id = label.get("job_req_id")
        items.append(item)
    return items


@router.get("/options", response_model=list[ApplicationOption])
def application_options(
    search: str | None = None,
    status: str | None = None,
    ids: list[uuid.UUID] = Query(default=[]),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: CurrentUser = Depends(require_permission(PermissionResource.APPLICATION, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[ApplicationOption]:
    """Type-to-search "candidate — job" matches, for the pickers that used to
    load every application, candidate and job to fill a dropdown."""
    rows = application_service.application_options(
        db, current_user.organization_id, search=search, status=status, ids=ids, limit=limit, viewer=current_user
    )
    return [ApplicationOption(id=aid, candidate_name=name, job_title=title) for aid, name, title in rows]


@router.post("", response_model=ApplicationRead, status_code=201)
def create_application(
    payload: ApplicationCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.APPLICATION, PermissionAction.CREATE)),
    db: Session = Depends(get_db_session),
) -> ApplicationRead:
    application_service.check_viewer_may_apply(
        db,
        current_user.organization_id,
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        viewer=current_user,
    )
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
    # Through the viewer's scope first: AI read is granted org-wide, the
    # application it scores is not.
    application_service.get_application(db, current_user.organization_id, application_id, viewer=current_user)
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


def _bulk_apply(
    db: Session,
    current_user: CurrentUser,
    payload: BulkApplicationActionRequest,
    *,
    action,
    audit_action: str,
) -> BulkActionResult:
    """Shared runner for bulk pipeline actions.

    Each application is committed independently — one already-rejected
    application or one the caller can't see must not roll back the 40 valid
    ones sitting next to it in the same batch. Every outcome, success or
    failure, is reported back so the UI can show exactly what happened.
    """
    succeeded: list[uuid.UUID] = []
    failed: list[BulkActionFailure] = []

    for application_id in payload.application_ids:
        try:
            application = application_service.get_application(
                db, current_user.organization_id, application_id, viewer=current_user
            )
            action(db, application, actor_id=current_user.id, note=payload.note)
            record_audit(
                db,
                organization_id=current_user.organization_id,
                actor_user_id=current_user.id,
                action=audit_action,
                resource_type="application",
                resource_id=str(application.id),
                metadata={"bulk": True},
            )
            db.commit()
            succeeded.append(application_id)
        except AppError as exc:
            db.rollback()
            failed.append(BulkActionFailure(application_id=application_id, reason=str(exc.detail)))

    return BulkActionResult(succeeded=succeeded, failed=failed)


@router.post("/bulk-reject", response_model=BulkActionResult)
def bulk_reject_applications(
    payload: BulkApplicationActionRequest,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.PIPELINE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> BulkActionResult:
    return _bulk_apply(
        db,
        current_user,
        payload,
        action=pipeline_service.reject_application,
        audit_action=AuditAction.APPLICATION_REJECTED.value,
    )


@router.post("/bulk-hold", response_model=BulkActionResult)
def bulk_hold_applications(
    payload: BulkApplicationActionRequest,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.PIPELINE, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> BulkActionResult:
    return _bulk_apply(
        db, current_user, payload, action=pipeline_service.hold_application, audit_action=AuditAction.APPLICATION_HELD.value
    )
