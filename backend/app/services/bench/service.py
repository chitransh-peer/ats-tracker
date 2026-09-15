"""Talent Bench operations, including who is allowed to see which consultant.

## Visibility model

Holding `talent_bench:read` gets a user into the module. It does not entitle
them to every consultant on it. Row-level rules:

  * **Super Admin, Admin, Executive** — see the whole bench.
  * **Recruiter** — sees a profile only if they are connected to it: an owner,
    the sales team member, the account manager, or its creator.
  * **Hiring Manager** — read-only, and only profiles marked as available to
    market (`Active Bench`). A benched consultant flagged `Do Not Market` is
    hidden, because that flag usually means a commercial or personal reason
    that is not the hiring manager's business.
  * Everyone else — no access at all.

Enforced in SQL rather than by filtering in Python, so an unauthorised row is
never loaded and pagination stays correct.
"""

import uuid
from datetime import UTC, date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import BenchStatus, RoleName
from app.core.exceptions import ConflictError, NotFoundError
from app.db.models.bench import BenchProfile, BenchProfileOwner, BenchSubmission
from app.db.models.candidate import Candidate
from app.schemas.auth import CurrentUser

# Roles that see the entire bench.
_UNRESTRICTED_ROLES = {RoleName.SUPER_ADMIN.value, RoleName.ADMIN.value, RoleName.EXECUTIVE.value}
# Read-only roles limited to consultants that are actively being marketed.
_MARKETABLE_ONLY_ROLES = {RoleName.HIRING_MANAGER.value}


def _load(query):
    return query.options(
        selectinload(BenchProfile.candidate).selectinload(Candidate.tags),
        selectinload(BenchProfile.owners),
    )


def _visibility_filter(query, viewer: CurrentUser | None):
    """Narrow a bench query to the rows this viewer may see."""
    if viewer is None:
        return query

    roles = set(viewer.roles)
    if roles & _UNRESTRICTED_ROLES:
        return query

    if roles & _MARKETABLE_ONLY_ROLES:
        return query.where(BenchProfile.status == BenchStatus.ACTIVE.value)

    # Recruiters and anything else: only profiles they are attached to.
    return query.where(
        or_(
            BenchProfile.sales_team_member_id == viewer.id,
            BenchProfile.account_manager_id == viewer.id,
            BenchProfile.created_by == viewer.id,
            BenchProfile.id.in_(select(BenchProfileOwner.bench_profile_id).where(BenchProfileOwner.user_id == viewer.id)),
        )
    )


def can_view(profile: BenchProfile, viewer: CurrentUser | None) -> bool:
    """In-Python mirror of `_visibility_filter`, for already-loaded rows."""
    if viewer is None:
        return True
    roles = set(viewer.roles)
    if roles & _UNRESTRICTED_ROLES:
        return True
    if roles & _MARKETABLE_ONLY_ROLES:
        return profile.status == BenchStatus.ACTIVE.value
    return viewer.id in {
        profile.sales_team_member_id,
        profile.account_manager_id,
        profile.created_by,
        *(o.user_id for o in profile.owners),
    }


def _next_bench_code(db: Session, organization_id: uuid.UUID) -> int:
    current = db.scalar(select(func.max(BenchProfile.bench_code)).where(BenchProfile.organization_id == organization_id))
    return (current or 0) + 1


def build_bench_query(
    organization_id: uuid.UUID,
    *,
    viewer: CurrentUser | None = None,
    status: str | None = None,
    sub_status: str | None = None,
    work_auth: str | None = None,
    owner_id: uuid.UUID | None = None,
    search: str | None = None,
):
    """Filters + visibility scoping only, unexecuted."""
    query = _load(
        select(BenchProfile)
        .join(Candidate, Candidate.id == BenchProfile.candidate_id)
        .where(
            BenchProfile.organization_id == organization_id,
            BenchProfile.deleted_at.is_(None),
            Candidate.deleted_at.is_(None),
        )
    )

    if status:
        query = query.where(BenchProfile.status == status)
    if sub_status:
        query = query.where(BenchProfile.sub_status == sub_status)
    if work_auth:
        query = query.where(Candidate.work_auth == work_auth)
    if owner_id:
        query = query.where(
            or_(
                BenchProfile.sales_team_member_id == owner_id,
                BenchProfile.account_manager_id == owner_id,
                BenchProfile.id.in_(select(BenchProfileOwner.bench_profile_id).where(BenchProfileOwner.user_id == owner_id)),
            )
        )
    if search:
        like = f"%{search}%"
        query = query.where(
            or_(
                Candidate.full_name.ilike(like),
                Candidate.email.ilike(like),
                BenchProfile.marketing_title.ilike(like),
                Candidate.current_title.ilike(like),
            )
        )

    query = _visibility_filter(query, viewer)
    return query.order_by(BenchProfile.bench_start_date.desc(), BenchProfile.bench_code.desc())


# The hotlist builder fetches active bench profiles unpaginated to populate
# its "pick a consultant" list. Capped here rather than truly unbounded.
_UNPAGINATED_SAFETY_LIMIT = 1000


def list_profiles(
    db: Session,
    organization_id: uuid.UUID,
    *,
    viewer: CurrentUser | None = None,
    status: str | None = None,
    sub_status: str | None = None,
    work_auth: str | None = None,
    owner_id: uuid.UUID | None = None,
    search: str | None = None,
) -> list[BenchProfile]:
    query = build_bench_query(
        organization_id,
        viewer=viewer,
        status=status,
        sub_status=sub_status,
        work_auth=work_auth,
        owner_id=owner_id,
        search=search,
    )
    return list(db.scalars(query.limit(_UNPAGINATED_SAFETY_LIMIT)).unique().all())


def get_profile(
    db: Session, organization_id: uuid.UUID, profile_id: uuid.UUID, *, viewer: CurrentUser | None = None
) -> BenchProfile:
    query = _load(
        select(BenchProfile).where(
            BenchProfile.id == profile_id,
            BenchProfile.organization_id == organization_id,
            BenchProfile.deleted_at.is_(None),
        )
    )
    query = _visibility_filter(query, viewer)
    profile = db.scalars(query).unique().one_or_none()
    if profile is None:
        # Deliberately indistinguishable from "does not exist": telling an
        # unauthorised caller that a consultant exists but is hidden leaks the
        # roster.
        raise NotFoundError("Bench profile not found")
    return profile


def get_profiles_by_ids(
    db: Session, organization_id: uuid.UUID, profile_ids: list[uuid.UUID], *, viewer: CurrentUser | None = None
) -> list[BenchProfile]:
    """Fetch several profiles, silently dropping any the viewer cannot see."""
    if not profile_ids:
        return []
    query = _load(
        select(BenchProfile).where(
            BenchProfile.id.in_(profile_ids),
            BenchProfile.organization_id == organization_id,
            BenchProfile.deleted_at.is_(None),
        )
    )
    query = _visibility_filter(query, viewer)
    return list(db.scalars(query).unique().all())


def create_profile(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    candidate_id: uuid.UUID,
    owner_ids: list[uuid.UUID] | None = None,
    **fields,
) -> BenchProfile:
    candidate = db.scalar(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.organization_id == organization_id,
            Candidate.deleted_at.is_(None),
        )
    )
    if candidate is None:
        raise NotFoundError("Candidate not found")

    existing = db.scalar(
        select(BenchProfile).where(
            BenchProfile.candidate_id == candidate_id, BenchProfile.organization_id == organization_id
        )
    )
    if existing is not None:
        if existing.deleted_at is None:
            raise ConflictError(f"{candidate.full_name} is already on the talent bench")
        # Previously removed from the bench — reinstate rather than creating a
        # second profile, so the person keeps one bench history.
        existing.deleted_at = None
        existing.status = fields.get("status") or BenchStatus.ACTIVE.value
        existing.bench_start_date = fields.get("bench_start_date") or date.today()
        existing.updated_by = actor_id
        db.commit()
        db.refresh(existing)
        return existing

    profile = BenchProfile(
        organization_id=organization_id,
        candidate_id=candidate_id,
        bench_code=_next_bench_code(db, organization_id),
        created_by=actor_id,
        updated_by=actor_id,
        **{k: v for k, v in fields.items() if v is not None},
    )
    if profile.bench_start_date is None:
        profile.bench_start_date = date.today()
    db.add(profile)
    db.flush()

    # The creator is always an owner, otherwise a recruiter could add someone
    # to the bench and immediately lose sight of them.
    for user_id in {*(owner_ids or []), *([actor_id] if actor_id else [])}:
        db.add(BenchProfileOwner(bench_profile_id=profile.id, user_id=user_id))

    db.commit()
    db.refresh(profile)
    return profile


def update_profile(
    db: Session,
    profile: BenchProfile,
    *,
    actor_id: uuid.UUID | None,
    owner_ids: list[uuid.UUID] | None = None,
    **fields,
) -> BenchProfile:
    for key, value in fields.items():
        if value is not None:
            setattr(profile, key, value)
    profile.updated_by = actor_id

    if owner_ids is not None:
        current = {o.user_id: o for o in profile.owners}
        wanted = set(owner_ids)
        for user_id, row in current.items():
            if user_id not in wanted:
                db.delete(row)
        for user_id in wanted - set(current):
            db.add(BenchProfileOwner(bench_profile_id=profile.id, user_id=user_id))

    db.commit()
    db.refresh(profile)
    return profile


def remove_from_bench(db: Session, profile: BenchProfile, *, actor_id: uuid.UUID | None) -> None:
    """Soft delete: the candidate record and marketing history are preserved."""
    from datetime import datetime

    profile.deleted_at = datetime.now(UTC)
    profile.updated_by = actor_id
    db.commit()


def add_submission(db: Session, profile: BenchProfile, *, actor_id: uuid.UUID | None, **fields) -> BenchSubmission:
    submission = BenchSubmission(
        bench_profile_id=profile.id,
        submitted_by=actor_id,
        **{k: v for k, v in fields.items() if v is not None},
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def bench_summary(db: Session, organization_id: uuid.UUID, *, viewer: CurrentUser | None = None) -> dict:
    """Counts for the bench dashboard cards, respecting visibility."""
    base = select(BenchProfile).where(BenchProfile.organization_id == organization_id, BenchProfile.deleted_at.is_(None))
    profiles = list(db.scalars(_visibility_filter(base, viewer)).unique().all())

    ages = [p.bench_age_days for p in profiles if p.status == BenchStatus.ACTIVE.value]
    return {
        "total": len(profiles),
        "active": sum(1 for p in profiles if p.status == BenchStatus.ACTIVE.value),
        "inactive": sum(1 for p in profiles if p.status == BenchStatus.INACTIVE.value),
        "placed": sum(1 for p in profiles if p.status == BenchStatus.PLACED.value),
        "average_bench_age_days": round(sum(ages) / len(ages), 1) if ages else None,
        # Long-benched consultants are the ones losing money.
        "aging_over_60_days": sum(1 for a in ages if a >= 60),
    }
