import { apiClient } from "./client";
import type { BenchProfile, BenchProfileInput, BenchSubmission, BenchSummary } from "./types";

export interface BenchFilters {
  status?: string;
  sub_status?: string;
  work_auth?: string;
  owner_id?: string;
  search?: string;
  limit?: number;
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

export function listBenchProfiles(filters: BenchFilters = {}) {
  return apiClient.get<BenchProfile[]>(`/talent-bench${buildQuery(filters)}`);
}

/** Paginated variant for the Talent Bench grid. Pagination is opt-in on this
 * endpoint (see the backend route) so the hotlist builder's unpaginated
 * consultant picker keeps working. */
export function listBenchProfilesPage(filters: BenchFilters = {}) {
  return apiClient.getPage<BenchProfile>(
    `/talent-bench${buildQuery({
      ...filters,
      limit: filters.limit?.toString(),
      offset: filters.offset?.toString(),
    })}`,
  );
}

export function getBenchSummary() {
  return apiClient.get<BenchSummary>("/talent-bench/summary");
}

export function getBenchProfile(profileId: string) {
  return apiClient.get<BenchProfile>(`/talent-bench/${profileId}`);
}

export function addToBench(input: BenchProfileInput & { candidate_id: string }) {
  return apiClient.post<BenchProfile>("/talent-bench", input);
}

export function updateBenchProfile(profileId: string, input: BenchProfileInput) {
  return apiClient.patch<BenchProfile>(`/talent-bench/${profileId}`, input);
}

export function removeFromBench(profileId: string) {
  return apiClient.delete<void>(`/talent-bench/${profileId}`);
}

export function listBenchSubmissions(profileId: string) {
  return apiClient.get<BenchSubmission[]>(`/talent-bench/${profileId}/submissions`);
}

export function addBenchSubmission(
  profileId: string,
  input: {
    client_id?: string | null;
    vendor_id?: string | null;
    job_id?: string | null;
    submitted_rate?: number | null;
    status?: string | null;
    note?: string | null;
  },
) {
  return apiClient.post<BenchSubmission>(`/talent-bench/${profileId}/submissions`, input);
}

export interface BulkBenchResult {
  succeeded: string[];
  failed: { candidate_id: string; reason: string }[];
}

export function bulkAddToBench(candidateIds: string[]) {
  return apiClient.post<BulkBenchResult>("/talent-bench/bulk", { candidate_ids: candidateIds });
}
