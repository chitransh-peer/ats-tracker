import uuid

from pydantic import BaseModel


class FunnelStage(BaseModel):
    stage: str
    value: int


class SourceEffectiveness(BaseModel):
    source: str
    value: int


class RecruiterPerformance(BaseModel):
    recruiter_id: uuid.UUID
    recruiter_name: str
    open_jobs: int
    applications: int
    hires: int


class AgingJob(BaseModel):
    job_id: uuid.UUID
    title: str
    status: str
    posted_at: str | None
    age_days: int | None


class TimeToFillSummary(BaseModel):
    average_days: float | None
    filled_jobs_count: int


class HiringTrendPoint(BaseModel):
    month: str
    offers: int
    hires: int


class ScoreDistributionBucket(BaseModel):
    bucket: str
    count: int


class OfferMetrics(BaseModel):
    sent: int
    accepted: int
    declined: int
    pending: int
    acceptance_rate: float | None


class RecruiterDashboard(BaseModel):
    open_jobs: int
    applications_this_week: int
    interviews_scheduled: int
    offers_pending: int


class ExecutiveDashboard(BaseModel):
    total_open_jobs: int
    total_candidates: int
    total_hires: int
    funnel: list[FunnelStage]
