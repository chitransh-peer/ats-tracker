import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import AuditAction, PermissionAction, PermissionResource
from app.core.exceptions import AppError
from app.core.pagination import MAX_LIMIT
from app.schemas.auth import CurrentUser
from app.schemas.bench import (
    BenchProfileCreate,
    BenchProfileRead,
    BenchProfileUpdate,
    BenchSubmissionCreate,
    BenchSubmissionRead,
    BenchSummary,
    BulkAddToBenchRequest,
    BulkBenchFailure,
    BulkBenchResult,
)
from app.services.audit.service import record as record_audit
from app.services.bench import service as bench_service

router = APIRouter(prefix="/talent-bench", tags=["talent-bench"])

_read = require_permission(PermissionResource.TALENT_BENCH, PermissionAction.READ)
_create = require_permission(PermissionResource.TALENT_BENCH, PermissionAction.CREATE)
_update = require_permission(PermissionResource.TALENT_BENCH, PermissionAction.UPDATE)
_delete = require_permission(PermissionResource.TALENT_BENCH, PermissionAction.DELETE)


def _to_read(profile) -> BenchProfileRead:
    candidate = profile.candidate
    return BenchProfileRead(
        id=profile.id,
        organization_id=profile.organization_id,
        candidate_id=profile.candidate_id,
        bench_code=profile.bench_code,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        location=candidate.location,
        current_title=candidate.current_title,
        work_auth=candidate.work_auth,
        total_experience_years=(
            float(candidate.total_experience_years) if candidate.total_experience_years is not None else None
        ),
        skills=list(candidate.skills or []),
        marketing_title=profile.marketing_title,
        status=profile.status,
        sub_status=profile.sub_status,
        bench_start_date=profile.bench_start_date,
        bench_age_days=profile.bench_age_days,
        available_from=profile.available_from,
        desired_rate=float(profile.desired_rate) if profile.desired_rate is not None else None,
        rate_currency=profile.rate_currency,
        rate_unit=profile.rate_unit,
        tax_term=profile.tax_term,
        sales_team_member_id=profile.sales_team_member_id,
        account_manager_id=profile.account_manager_id,
        owner_ids=[o.user_id for o in profile.owners],
        preferred_locations=profile.preferred_locations,
        willing_to_relocate=profile.willing_to_relocate,
        marketing_summary=profile.marketing_summary,
        internal_notes=profile.internal_notes,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("", response_model=list[BenchProfileRead])
def list_bench(
    response: Response,
    status: str | None = None,
    sub_status: str | None = None,
    work_auth: str | None = None,
    owner_id: uuid.UUID | None = None,
    search: str | None = Query(default=None, max_length=200),
    # Pagination is opt-in — the hotlist builder fetches bench profiles
    # unpaginated to populate its consultant picker, and defaulting this to a
    # small page would silently hide bench members from that list.
    limit: int | None = None,
    offset: int = 0,
    current_user: CurrentUser = Depends(_read),
    db: Session = Depends(get_db_session),
) -> list[BenchProfileRead]:
    if limit is not None:
        limit = max(1, min(limit, MAX_LIMIT))
        query = bench_service.build_bench_query(
            current_user.organization_id,
            viewer=current_user,
            status=status,
            sub_status=sub_status,
            work_auth=work_auth,
            owner_id=owner_id,
            search=search,
        )
        total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
        profiles = list(db.scalars(query.limit(limit).offset(offset)).unique().all())
        response.headers["X-Total-Count"] = str(total)
    else:
        profiles = bench_service.list_profiles(
            db,
            current_user.organization_id,
            viewer=current_user,
            status=status,
            sub_status=sub_status,
            work_auth=work_auth,
            owner_id=owner_id,
            search=search,
        )
    return [_to_read(p) for p in profiles]


@router.get("/summary", response_model=BenchSummary)
def bench_summary(current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)) -> BenchSummary:
    return BenchSummary(**bench_service.bench_summary(db, current_user.organization_id, viewer=current_user))


@router.get("/{profile_id}", response_model=BenchProfileRead)
def get_bench_profile(
    profile_id: uuid.UUID,
    current_user: CurrentUser = Depends(_read),
    db: Session = Depends(get_db_session),
) -> BenchProfileRead:
    profile = bench_service.get_profile(db, current_user.organization_id, profile_id, viewer=current_user)
    return _to_read(profile)


@router.post("", response_model=BenchProfileRead, status_code=201)
def add_to_bench(
    payload: BenchProfileCreate,
    current_user: CurrentUser = Depends(_create),
    db: Session = Depends(get_db_session),
) -> BenchProfileRead:
    data = payload.model_dump(exclude_unset=True)
    candidate_id = data.pop("candidate_id")
    owner_ids = data.pop("owner_ids", None)

    profile = bench_service.create_profile(
        db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        candidate_id=candidate_id,
        owner_ids=owner_ids,
        **data,
    )
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.BENCH_PROFILE_CREATED.value,
        resource_type="bench_profile",
        resource_id=str(profile.id),
        metadata={"candidate_id": str(candidate_id), "bench_code": profile.bench_code},
    )
    db.commit()
    db.refresh(profile)
    return _to_read(profile)


@router.patch("/{profile_id}", response_model=BenchProfileRead)
def update_bench_profile(
    profile_id: uuid.UUID,
    payload: BenchProfileUpdate,
    current_user: CurrentUser = Depends(_update),
    db: Session = Depends(get_db_session),
) -> BenchProfileRead:
    profile = bench_service.get_profile(db, current_user.organization_id, profile_id, viewer=current_user)
    data = payload.model_dump(exclude_unset=True)
    owner_ids = data.pop("owner_ids", None)

    profile = bench_service.update_profile(db, profile, actor_id=current_user.id, owner_ids=owner_ids, **data)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.BENCH_PROFILE_UPDATED.value,
        resource_type="bench_profile",
        resource_id=str(profile.id),
        metadata={"changed": sorted(data.keys())},
    )
    db.commit()
    db.refresh(profile)
    return _to_read(profile)


@router.delete("/{profile_id}", status_code=204)
def remove_from_bench(
    profile_id: uuid.UUID,
    current_user: CurrentUser = Depends(_delete),
    db: Session = Depends(get_db_session),
) -> None:
    profile = bench_service.get_profile(db, current_user.organization_id, profile_id, viewer=current_user)
    record_audit(
        db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        action=AuditAction.BENCH_PROFILE_REMOVED.value,
        resource_type="bench_profile",
        resource_id=str(profile.id),
        metadata={"bench_code": profile.bench_code},
    )
    bench_service.remove_from_bench(db, profile, actor_id=current_user.id)


@router.get("/{profile_id}/submissions", response_model=list[BenchSubmissionRead])
def list_submissions(
    profile_id: uuid.UUID,
    current_user: CurrentUser = Depends(_read),
    db: Session = Depends(get_db_session),
) -> list[BenchSubmissionRead]:
    profile = bench_service.get_profile(db, current_user.organization_id, profile_id, viewer=current_user)
    return list(profile.submissions)


@router.post("/{profile_id}/submissions", response_model=BenchSubmissionRead, status_code=201)
def add_submission(
    profile_id: uuid.UUID,
    payload: BenchSubmissionCreate,
    current_user: CurrentUser = Depends(_update),
    db: Session = Depends(get_db_session),
) -> BenchSubmissionRead:
    profile = bench_service.get_profile(db, current_user.organization_id, profile_id, viewer=current_user)
    return bench_service.add_submission(db, profile, actor_id=current_user.id, **payload.model_dump(exclude_unset=True))


@router.post("/bulk", response_model=BulkBenchResult)
def bulk_add_to_bench(
    payload: BulkAddToBenchRequest,
    current_user: CurrentUser = Depends(_create),
    db: Session = Depends(get_db_session),
) -> BulkBenchResult:
    """Add several candidates at once — the counterpart to picking them one
    dialog at a time. Each candidate is committed independently so one
    already-benched candidate in the batch doesn't block the rest."""
    succeeded: list[uuid.UUID] = []
    failed: list[BulkBenchFailure] = []

    for candidate_id in payload.candidate_ids:
        try:
            profile = bench_service.create_profile(
                db,
                organization_id=current_user.organization_id,
                actor_id=current_user.id,
                candidate_id=candidate_id,
            )
            record_audit(
                db,
                organization_id=current_user.organization_id,
                actor_user_id=current_user.id,
                action=AuditAction.BENCH_PROFILE_CREATED.value,
                resource_type="bench_profile",
                resource_id=str(profile.id),
                metadata={"candidate_id": str(candidate_id), "bulk": True},
            )
            db.commit()
            succeeded.append(candidate_id)
        except AppError as exc:
            db.rollback()
            failed.append(BulkBenchFailure(candidate_id=candidate_id, reason=str(exc.detail)))

    return BulkBenchResult(succeeded=succeeded, failed=failed)
