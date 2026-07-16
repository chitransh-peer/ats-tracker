import { apiClient } from "./client";
import type { Application, ApplicationStageHistoryEntry } from "./types";

export interface ApplicationFilters {
  job_id?: string;
  candidate_id?: string;
  status?: string;
}

function buildQuery(params: object): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params as Record<string, string | undefined>)) {
    if (value) query.set(key, value);
  }
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export function listApplications(filters: ApplicationFilters = {}) {
  return apiClient.get<Application[]>(`/applications${buildQuery(filters)}`);
}

export function createApplication(input: {
  candidate_id: string;
  job_id: string;
  source?: string;
}) {
  return apiClient.post<Application>("/applications", input);
}

export function getApplicationTimeline(applicationId: string) {
  return apiClient.get<ApplicationStageHistoryEntry[]>(`/applications/${applicationId}/timeline`);
}

export function moveApplicationStage(applicationId: string, toStageId: string, note?: string) {
  return apiClient.post<Application>(`/applications/${applicationId}/move-stage`, {
    to_stage_id: toStageId,
    note,
  });
}

export function holdApplication(applicationId: string, note?: string) {
  return apiClient.post<Application>(`/applications/${applicationId}/hold`, { note });
}

export function rejectApplication(applicationId: string, note?: string) {
  return apiClient.post<Application>(`/applications/${applicationId}/reject`, { note });
}

export function restoreApplication(applicationId: string, note?: string) {
  return apiClient.post<Application>(`/applications/${applicationId}/restore`, { note });
}
