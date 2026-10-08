import { apiClient } from "./client";
import type {
  Job,
  JobCreateInput,
  JobOption,
  JobSummary,
  JobCustomField,
  JobCustomFieldInput,
  JobDocument,
  JobNote,
  JobNoteInput,
  JobSearchCriteria,
  JobSearchCriteriaInput,
  JobSubmissionsSummary,
} from "./types";

export interface JobFilters {
  status?: string;
  department?: string;
  client_id?: string;
  recruiter_id?: string;
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

function jobQuery(filters: JobFilters): string {
  return buildQuery({
    ...filters,
    limit: filters.limit?.toString(),
    offset: filters.offset?.toString(),
  });
}

/** One page of jobs (50 unless `limit` says otherwise, 200 at most). */
export function listJobs(filters: JobFilters = {}) {
  return apiClient.get<Job[]>(`/jobs${jobQuery(filters)}`);
}

/** One page of jobs plus the total matching, for a pager. */
export function listJobsPage(filters: JobFilters = {}) {
  return apiClient.getPage<Job>(`/jobs${jobQuery(filters)}`);
}

export function getJobSummary() {
  return apiClient.get<JobSummary>("/jobs/summary");
}

/** Up to 20 jobs matching `search` (title, job code, client), or exactly `ids`. */
export function searchJobOptions(search: string, ids: string[] = [], status?: string) {
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  if (status) query.set("status", status);
  for (const id of ids) query.append("ids", id);
  const qs = query.toString();
  return apiClient.get<JobOption[]>(`/jobs/options${qs ? `?${qs}` : ""}`);
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

export function jobSubmissions(jobId: string) {
  return apiClient.get<JobSubmissionsSummary>(`/jobs/${jobId}/submissions`);
}

export function listJobNotes(jobId: string) {
  return apiClient.get<JobNote[]>(`/jobs/${jobId}/notes`);
}

export function addJobNote(jobId: string, input: JobNoteInput) {
  return apiClient.post<JobNote>(`/jobs/${jobId}/notes`, input);
}

export function listJobDocuments(jobId: string) {
  return apiClient.get<JobDocument[]>(`/jobs/${jobId}/documents`);
}

export function saveJobSearchCriteria(jobId: string, input: JobSearchCriteriaInput) {
  return apiClient.put<JobSearchCriteria>(`/jobs/${jobId}/search-criteria`, input);
}

export function setJobCustomField(jobId: string, input: JobCustomFieldInput) {
  return apiClient.put<JobCustomField>(`/jobs/${jobId}/custom-fields`, input);
}

export const JOB_STATUSES = ["Draft", "Active", "On Hold", "Closed", "Cancelled"] as const;

export const REMOTE_OPTIONS = ["Onsite", "Remote", "Hybrid"] as const;

export const JOB_TYPES = [
  "Full-time",
  "Contract",
  "Contract to Hire",
  "Part-time",
  "Intern",
] as const;

export const RESPOND_BY_OPTIONS = ["Open Until Filled", "Specific Date"] as const;

export const TURNAROUND_UNITS = ["In Days", "In Hours", "In Weeks"] as const;

export const RATE_UNITS = ["Hourly", "Daily", "Weekly", "Monthly", "Yearly"] as const;

export const RATE_TYPES = ["C2C", "W-2", "1099", "Full Time"] as const;

export const CURRENCIES = ["USD", "CAD", "INR", "GBP", "AUD"] as const;

export const TAX_TERM_OPTIONS = ["C2C", "W-2", "1099", "W-2 Hourly", "Full Time"] as const;

export const JOB_REQUIRED_DOCUMENTS = [
  "Resume",
  "Right to Represent",
  "Work Authorization",
  "Photo ID",
  "Background Check",
  "Drug Test",
  "References",
  "Certifications",
] as const;

export const EMPLOYMENT_LEVELS = [
  "Entry Level",
  "Associate",
  "Mid-Senior Level",
  "Director",
  "Executive",
] as const;

export const INTERVIEW_MODES = [
  "Telephonic",
  "Visual Round",
  "In Person",
  "Telephonic + Visual Round",
  "Visual Round + In Person",
] as const;

/** Jobs saved under the older "Video" / "Virtual Round" labels keep that text. */
export function normalizeInterviewMode(mode: string | null | undefined): string {
  return (mode ?? "").replace(/\b(?:Video|Virtual Round)\b/g, "Visual Round");
}

export const DEGREE_OPTIONS = [
  "High School",
  "Associate",
  "Bachelors",
  "Masters",
  "Doctorate",
  "None",
] as const;

export const JOB_NOTE_TYPES = ["Job Posting", "Applicant Reference"] as const;

export const JOB_NOTE_ACTIONS = ["Call", "Email", "Meeting", "Update", "General"] as const;

export const RADIUS_OPTIONS = [5, 10, 25, 50, 100, 250] as const;
