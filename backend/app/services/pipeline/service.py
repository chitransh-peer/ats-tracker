import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ApplicationStatus, TerminalOutcome
from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.models.application import Application, ApplicationStageHistory
from app.db.models.pipeline_stage import StageTemplate, StageTemplateStage

DEFAULT_STAGE_NAMES: list[str] = [
    "Applied",
    "Screening",
    "Shortlisted",
    "Recruiter Interview",
    "Technical Assessment",
    "Hiring Manager Interview",
    "Panel Interview",
    "Background Check",
    "Offer",
    "Offer Accepted",
    "Onboarding",
    "Hired",
]


def seed_default_stage_template(db: Session, organization_id: uuid.UUID) -> StageTemplate:
    existing = db.scalar(
        select(StageTemplate).where(StageTemplate.organization_id == organization_id, StageTemplate.is_default.is_(True))
    )
    if existing is not None:
        return existing

    template = StageTemplate(organization_id=organization_id, name="Default Pipeline", is_default=True)
    db.add(template)
    db.flush()

    for order, name in enumerate(DEFAULT_STAGE_NAMES):
        terminal_outcome = TerminalOutcome.HIRED.value if name == "Hired" else TerminalOutcome.NONE.value
        db.add(
            StageTemplateStage(
                template_id=template.id, name=name, sort_order=order, terminal_outcome=terminal_outcome
            )
        )
    db.commit()
    db.refresh(template)
    return template


def get_default_stage_template(db: Session, organization_id: uuid.UUID) -> StageTemplate | None:
    return db.scalar(
        select(StageTemplate)
        .where(StageTemplate.organization_id == organization_id, StageTemplate.is_default.is_(True))
        .options(selectinload(StageTemplate.stages))
    )


def get_stage(db: Session, organization_id: uuid.UUID, stage_id: uuid.UUID) -> StageTemplateStage:
    stage = db.scalar(
        select(StageTemplateStage)
        .join(StageTemplate)
        .where(StageTemplateStage.id == stage_id, StageTemplate.organization_id == organization_id)
    )
    if stage is None:
        raise NotFoundError("Pipeline stage not found")
    return stage


def move_stage(
    db: Session,
    application: Application,
    *,
    to_stage_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    note: str | None = None,
) -> Application:
    if application.status != ApplicationStatus.ACTIVE.value:
        raise ValidationAppError("Only active applications can move between pipeline stages")

    to_stage = get_stage(db, application.organization_id, to_stage_id)
    from_stage_id = application.current_stage_id

    application.current_stage_id = to_stage.id
    if to_stage.terminal_outcome == TerminalOutcome.HIRED.value:
        application.status = ApplicationStatus.HIRED.value

    db.add(
        ApplicationStageHistory(
            application_id=application.id, from_stage_id=from_stage_id, to_stage_id=to_stage.id,
            changed_by=actor_id, note=note,
        )
    )
    db.commit()
    db.refresh(application)
    return application


def reject_application(
    db: Session, application: Application, *, actor_id: uuid.UUID | None, note: str | None = None
) -> Application:
    if application.status == ApplicationStatus.REJECTED.value:
        raise ValidationAppError("Application is already rejected")

    from_stage_id = application.current_stage_id
    application.status = ApplicationStatus.REJECTED.value
    db.add(
        ApplicationStageHistory(
            application_id=application.id, from_stage_id=from_stage_id, to_stage_id=from_stage_id,
            changed_by=actor_id, note=note or "Rejected",
        )
    )
    db.commit()
    db.refresh(application)
    return application


def hold_application(
    db: Session, application: Application, *, actor_id: uuid.UUID | None, note: str | None = None
) -> Application:
    if application.status != ApplicationStatus.ACTIVE.value:
        raise ValidationAppError("Only active applications can be put on hold")

    application.status = ApplicationStatus.ON_HOLD.value
    db.add(
        ApplicationStageHistory(
            application_id=application.id, from_stage_id=application.current_stage_id,
            to_stage_id=application.current_stage_id, changed_by=actor_id, note=note or "On hold",
        )
    )
    db.commit()
    db.refresh(application)
    return application


def restore_application(
    db: Session, application: Application, *, actor_id: uuid.UUID | None, note: str | None = None
) -> Application:
    if application.status not in {ApplicationStatus.ON_HOLD.value, ApplicationStatus.REJECTED.value}:
        raise ValidationAppError("Only held or rejected applications can be restored")

    application.status = ApplicationStatus.ACTIVE.value
    db.add(
        ApplicationStageHistory(
            application_id=application.id, from_stage_id=application.current_stage_id,
            to_stage_id=application.current_stage_id, changed_by=actor_id, note=note or "Restored",
        )
    )
    db.commit()
    db.refresh(application)
    return application
