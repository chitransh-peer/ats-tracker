import { apiClient } from "./client";
import type { Job, JobCreateInput } from "./types";

export interface JobFilters {
  status?: string;
  department?: string;
  client_id?: string;
  recruiter_id?: string;
}

function buildQuery(params: object): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params as Record<string, string | undefined>)) {
    if (value) query.set(key, value);
  }
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export function listJobs(filters: JobFilters = {}) {
  return apiClient.get<Job[]>(`/jobs${buildQuery(filters)}`);
}

export function getJob(jobId: string) {
  return apiClient.get<Job>(`/jobs/${jobId}`);
}

export function createJob(input: JobCreateInput) {
  return apiClient.post<Job>("/jobs", input);
}

export function updateJob(jobId: string, input: Partial<JobCreateInput>) {
  return apiClient.patch<Job>(`/jobs/${jobId}`, input);
}

export function publishJob(jobId: string) {
  return apiClient.post<Job>(`/jobs/${jobId}/publish`);
}

export function unpublishJob(jobId: string) {
  return apiClient.post<Job>(`/jobs/${jobId}/unpublish`);
}

export function closeJob(jobId: string) {
  return apiClient.post<Job>(`/jobs/${jobId}/close`);
}

export function holdJob(jobId: string) {
  return apiClient.post<Job>(`/jobs/${jobId}/hold`);
}

export function cancelJob(jobId: string) {
  return apiClient.post<Job>(`/jobs/${jobId}/cancel`);
}
