import { apiClient } from "./client";
import type { Application, ApplicationStageHistoryEntry } from "./types";

export interface ApplicationFilters {
  job_id?: string;
  candidate_id?: string;
  status?: string;
  page_size?: number;
  offset?: number;
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

/** Paginated variant for the Applications grid. Server-side pagination is
 * opt-in on this endpoint (see the backend route) so it doesn't disturb the
 * many pages that still fetch every application for client-side lookups. */
export function listApplicationsPage(filters: ApplicationFilters = {}) {
  return apiClient.getPage<Application>(
    `/applications${buildQuery({
      ...filters,
      page_size: filters.page_size?.toString(),
      offset: filters.offset?.toString(),
    })}`,
  );
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

export function getApplication(applicationId: string) {
  return apiClient.get<Application>(`/applications/${applicationId}`);
}

export interface BulkActionResult {
  succeeded: string[];
  failed: { application_id: string; reason: string }[];
}

export function bulkRejectApplications(applicationIds: string[], note?: string) {
  return apiClient.post<BulkActionResult>("/applications/bulk-reject", {
    application_ids: applicationIds,
    note,
  });
}

export function bulkHoldApplications(applicationIds: string[], note?: string) {
  return apiClient.post<BulkActionResult>("/applications/bulk-hold", {
    application_ids: applicationIds,
    note,
  });
}
