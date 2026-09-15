import { apiClient } from "./client";
import type {
  AgingJobRow,
  AuditLogEntry,
  ExecutiveDashboard,
  FunnelStage,
  HiringTrendPoint,
  OfferMetrics,
  RecruiterPerformanceRow,
  ScoreDistributionBucket,
  SourceEffectivenessRow,
  TimeToFillSummary,
} from "./types";

export function getFunnel() {
  return apiClient.get<FunnelStage[]>("/reports/funnel");
}

export function getSourceEffectiveness() {
  return apiClient.get<SourceEffectivenessRow[]>("/reports/source-effectiveness");
}

export function getAgingJobs() {
  return apiClient.get<AgingJobRow[]>("/reports/aging-jobs");
}

export function getRecruiterDashboard() {
  return apiClient.get<{
    open_jobs: number;
    applications_this_week: number;
    interviews_scheduled: number;
    offers_pending: number;
  }>("/reports/recruiter-dashboard");
}

export function getExecutiveDashboard() {
  return apiClient.get<ExecutiveDashboard>("/reports/executive-dashboard");
}

export function getHiringTrend() {
  return apiClient.get<HiringTrendPoint[]>("/reports/hiring-trend");
}

export function getScoreDistribution() {
  return apiClient.get<ScoreDistributionBucket[]>("/reports/score-distribution");
}

export function getOfferMetrics() {
  return apiClient.get<OfferMetrics>("/reports/offer-metrics");
}

export function getTimeToFill() {
  return apiClient.get<TimeToFillSummary>("/reports/time-to-fill");
}

export function getRecruiterPerformance() {
  return apiClient.get<RecruiterPerformanceRow[]>("/reports/recruiter-performance");
}

export function getAuditLogs() {
  return apiClient.get<AuditLogEntry[]>("/audit-logs");
}
