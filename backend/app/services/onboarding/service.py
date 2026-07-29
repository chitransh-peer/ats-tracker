import uuid
from datetime import datetime, timezone

from sqlalchemy import false, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import (
    ApplicationStatus,
    OnboardingStatus,
    OnboardingTaskCategory,
    OnboardingTaskStatus,
    RoleName,
)
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.scoping import scoped_roles
from app.db.models.application import Application
from app.db.models.job import Job
from app.db.models.offer import Offer
from app.db.models.onboarding import OnboardingCase, OnboardingTask
from app.schemas.auth import CurrentUser

# Default checklist seeded when a case is opened. Order matters for display.
_DEFAULT_TASKS: list[tuple[str, OnboardingTaskCategory]] = [
    ("Collect signed offer letter", OnboardingTaskCategory.DOCUMENTATION),
    ("Collect government ID & tax forms", OnboardingTaskCategory.DOCUMENTATION),
    ("Complete background verification", OnboardingTaskCategory.COMPLIANCE),
    ("Provision laptop & hardware", OnboardingTaskCategory.EQUIPMENT),
    ("Create email & system accounts", OnboardingTaskCategory.PROVISIONING),
    ("Schedule day-one orientation", OnboardingTaskCategory.ORIENTATION),
]


def _scope_filter(query, viewer: CurrentUser | None):
    if viewer is None:
        return query
    scopes = scoped_roles(viewer.roles)
    if not scopes:
        return query

    # Only Hiring Manager has any onboarding read scope; other scoped roles see nothing.
    if RoleName.HIRING_MANAGER.value not in scopes:
        return query.where(false())

    return query.where(
        OnboardingCase.application_id.in_(
            select(Application.id).join(Job, Job.id == Application.job_id).where(Job.hiring_manager_id == viewer.id)
        )
    )


def _load(query):
    return query.options(selectinload(OnboardingCase.tasks))


def open_case_for_application(
    db: Session,
    *,
    organization_id: uuid.UUID,
    application_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    start_date=None,
) -> OnboardingCase:
    """Open an onboarding case with the default checklist.

    Idempotent: if a case already exists for the application it is returned
    unchanged, so the offer-acceptance hook can call this safely more than once.
    """
    existing = db.scalar(
        _load(select(OnboardingCase)).where(OnboardingCase.application_id == application_id)
    )
    if existing is not None:
        return existing

    application = db.get(Application, application_id)
    if application is None or application.organization_id != organization_id:
        raise NotFoundError("Application not found")

    case = OnboardingCase(
        organization_id=organization_id,
        application_id=application_id,
        status=OnboardingStatus.IN_PROGRESS.value,
        start_date=start_date,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(case)
    db.flush()

    for index, (title, category) in enumerate(_DEFAULT_TASKS):
        db.add(
            OnboardingTask(
                case_id=case.id,
                title=title,
                category=category.value,
                status=OnboardingTaskStatus.PENDING.value,
                order_index=index,
            )
        )
    db.flush()
    db.refresh(case)
    return case


def open_case_for_offer(db: Session, offer: Offer, *, actor_id: uuid.UUID | None) -> OnboardingCase:
    return open_case_for_application(
        db,
        organization_id=offer.organization_id,
        application_id=offer.application_id,
        actor_id=actor_id,
        start_date=offer.joining_date,
    )


def get_case(
    db: Session, organization_id: uuid.UUID, case_id: uuid.UUID, *, viewer: CurrentUser | None = None
) -> OnboardingCase:
    query = _load(select(OnboardingCase)).where(
        OnboardingCase.id == case_id, OnboardingCase.organization_id == organization_id
    )
    case = db.scalar(_scope_filter(query, viewer))
    if case is None:
        raise NotFoundError("Onboarding case not found")
    return case


def list_cases(
    db: Session,
    organization_id: uuid.UUID,
    *,
    status: str | None = None,
    application_id: uuid.UUID | None = None,
    viewer: CurrentUser | None = None,
) -> list[OnboardingCase]:
    query = _load(select(OnboardingCase)).where(OnboardingCase.organization_id == organization_id)
    if status is not None:
        query = query.where(OnboardingCase.status == status)
    if application_id is not None:
        query = query.where(OnboardingCase.application_id == application_id)
    query = _scope_filter(query, viewer)
    return list(db.scalars(query.order_by(OnboardingCase.created_at.desc())).all())


def update_case(db: Session, case: OnboardingCase, *, actor_id: uuid.UUID | None, **fields) -> OnboardingCase:
    if case.status != OnboardingStatus.IN_PROGRESS.value:
        raise ValidationAppError("Only in-progress onboarding cases can be edited")
    for key, value in fields.items():
        if value is not None:
            setattr(case, key, value)
    case.updated_by = actor_id
    db.flush()
    db.refresh(case)
    return case


def add_task(db: Session, case: OnboardingCase, *, title: str, category: str, assignee_id=None, due_date=None) -> OnboardingTask:
    if case.status != OnboardingStatus.IN_PROGRESS.value:
        raise ValidationAppError("Cannot add tasks to a closed onboarding case")
    next_index = max((t.order_index for t in case.tasks), default=-1) + 1
    task = OnboardingTask(
        case_id=case.id,
        title=title,
        category=category,
        status=OnboardingTaskStatus.PENDING.value,
        assignee_id=assignee_id,
        due_date=due_date,
        order_index=next_index,
    )
    db.add(task)
    db.flush()
    db.refresh(case)
    return task


def get_task(db: Session, organization_id: uuid.UUID, task_id: uuid.UUID) -> OnboardingTask:
    task = db.scalar(
        select(OnboardingTask)
        .join(OnboardingCase, OnboardingCase.id == OnboardingTask.case_id)
        .where(OnboardingTask.id == task_id, OnboardingCase.organization_id == organization_id)
    )
    if task is None:
        raise NotFoundError("Onboarding task not found")
    return task


def update_task(db: Session, task: OnboardingTask, **fields) -> OnboardingTask:
    status = fields.get("status")
    for key, value in fields.items():
        if value is not None:
            setattr(task, key, value)
    if status == OnboardingTaskStatus.COMPLETED.value:
        task.completed_at = datetime.now(timezone.utc)
    elif status is not None:
        task.completed_at = None
    db.flush()
    db.refresh(task)
    return task


def complete_case(db: Session, case: OnboardingCase) -> OnboardingCase:
    if case.status != OnboardingStatus.IN_PROGRESS.value:
        raise ValidationAppError("Only in-progress onboarding cases can be completed")
    incomplete = [t for t in case.tasks if t.status != OnboardingTaskStatus.COMPLETED.value]
    if incomplete:
        raise ValidationAppError(f"{len(incomplete)} task(s) still incomplete")

    case.status = OnboardingStatus.COMPLETED.value
    case.completed_at = datetime.now(timezone.utc)

    application = db.get(Application, case.application_id)
    if application is not None:
        application.status = ApplicationStatus.HIRED.value
    db.flush()
    db.refresh(case)
    return case


def cancel_case(db: Session, case: OnboardingCase) -> OnboardingCase:
    if case.status != OnboardingStatus.IN_PROGRESS.value:
        raise ValidationAppError("Only in-progress onboarding cases can be cancelled")
    case.status = OnboardingStatus.CANCELLED.value
    db.flush()
    db.refresh(case)
    return case
