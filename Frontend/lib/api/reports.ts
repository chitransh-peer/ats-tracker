import { apiClient } from "./client";
import type { AgingJobRow, AuditLogEntry, FunnelStage, SourceEffectivenessRow } from "./types";

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

export function getAuditLogs() {
  return apiClient.get<AuditLogEntry[]>("/audit-logs");
}
