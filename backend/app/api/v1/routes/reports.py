from collections.abc import Callable

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import PermissionAction, PermissionResource
from app.core.ttl_cache import TTLCache
from app.schemas.auth import CurrentUser
from app.schemas.report import (
    AgingJob,
    ExecutiveDashboard,
    FunnelStage,
    HiringTrendPoint,
    OfferMetrics,
    RecruiterDashboard,
    RecruiterPerformance,
    ScoreDistributionBucket,
    SourceEffectiveness,
    TimeToFillSummary,
)
from app.services.reports import service as report_service

router = APIRouter(prefix="/reports", tags=["reports"])

_read = require_permission(PermissionResource.REPORT, PermissionAction.READ)

# The dashboard asks for ten reports on every load, and the funnel alone reads
# every application and its stage history. Each report is organization-wide
# and the same for everyone who can see it, so each is computed at most once a
# minute per organization (per server instance). Figures can be up to a
# minute behind; for a dashboard that is the right trade.
REPORT_CACHE = TTLCache(ttl_seconds=60)


def _cached(name: str, current_user: CurrentUser, compute: Callable[[], object], *, per_user: bool = False):
    key = (name, current_user.organization_id, current_user.id if per_user else None)
    return REPORT_CACHE.get_or_compute(key, compute)


@router.get("/recruiter-dashboard", response_model=RecruiterDashboard)
def recruiter_dashboard(
    current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)
) -> RecruiterDashboard:
    return _cached(
        "recruiter-dashboard",
        current_user,
        lambda: report_service.recruiter_dashboard(db, current_user.organization_id, current_user.id),
        per_user=True,
    )


@router.get("/executive-dashboard", response_model=ExecutiveDashboard)
def executive_dashboard(
    current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)
) -> ExecutiveDashboard:
    return _cached(
        "executive-dashboard", current_user, lambda: report_service.executive_dashboard(db, current_user.organization_id)
    )


@router.get("/funnel", response_model=list[FunnelStage])
def funnel(current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)) -> list[FunnelStage]:
    return _cached("funnel", current_user, lambda: report_service.funnel(db, current_user.organization_id))


@router.get("/time-to-fill", response_model=TimeToFillSummary)
def time_to_fill(current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)) -> TimeToFillSummary:
    return _cached("time-to-fill", current_user, lambda: report_service.time_to_fill(db, current_user.organization_id))


@router.get("/source-effectiveness", response_model=list[SourceEffectiveness])
def source_effectiveness(
    current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)
) -> list[SourceEffectiveness]:
    return _cached(
        "source-effectiveness",
        current_user,
        lambda: report_service.source_effectiveness(db, current_user.organization_id),
    )


@router.get("/recruiter-performance", response_model=list[RecruiterPerformance])
def recruiter_performance(
    current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)
) -> list[RecruiterPerformance]:
    return _cached(
        "recruiter-performance",
        current_user,
        lambda: report_service.recruiter_performance(db, current_user.organization_id),
    )


@router.get("/hiring-trend", response_model=list[HiringTrendPoint])
def hiring_trend(
    current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)
) -> list[HiringTrendPoint]:
    return _cached("hiring-trend", current_user, lambda: report_service.hiring_trend(db, current_user.organization_id))


@router.get("/score-distribution", response_model=list[ScoreDistributionBucket])
def score_distribution(
    current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)
) -> list[ScoreDistributionBucket]:
    return _cached(
        "score-distribution", current_user, lambda: report_service.score_distribution(db, current_user.organization_id)
    )


@router.get("/offer-metrics", response_model=OfferMetrics)
def offer_metrics(current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)) -> OfferMetrics:
    return _cached("offer-metrics", current_user, lambda: report_service.offer_metrics(db, current_user.organization_id))


@router.get("/aging-jobs", response_model=list[AgingJob])
def aging_jobs(current_user: CurrentUser = Depends(_read), db: Session = Depends(get_db_session)) -> list[AgingJob]:
    return _cached("aging-jobs", current_user, lambda: report_service.aging_jobs(db, current_user.organization_id))
