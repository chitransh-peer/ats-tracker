import { apiClient } from "./client";
import type { ConsolidatedFeedback, Interview, InterviewSummary } from "./types";

export interface InterviewFilters {
  application_id?: string;
  candidate_id?: string;
  status?: string;
  /** Scheduled interviews still ahead, soonest first. */
  upcoming?: boolean;
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

function interviewQuery(filters: InterviewFilters): string {
  return buildQuery({
    ...filters,
    upcoming: filters.upcoming ? "true" : undefined,
    limit: filters.limit?.toString(),
    offset: filters.offset?.toString(),
  });
}

/** One page of interviews, newest first (50 unless `limit` says otherwise). */
export function listInterviews(filters: InterviewFilters = {}) {
  return apiClient.get<Interview[]>(`/interviews${interviewQuery(filters)}`);
}

export function listInterviewsPage(filters: InterviewFilters = {}) {
  return apiClient.getPage<Interview>(`/interviews${interviewQuery(filters)}`);
}

export function getInterviewSummary() {
  return apiClient.get<InterviewSummary>("/interviews/summary");
}

export function createInterview(input: {
  application_id: string;
  round_name: string;
  mode: string;
  scheduled_at: string;
  panel_user_ids?: string[];
  primary_interviewer_id?: string;
}) {
  return apiClient.post<Interview>("/interviews", input);
}

export function updateInterview(
  interviewId: string,
  input: { status?: string; scheduled_at?: string },
) {
  return apiClient.patch<Interview>(`/interviews/${interviewId}`, input);
}

export function submitInterviewFeedback(
  interviewId: string,
  input: { rating: number; recommendation: string; notes?: string },
) {
  return apiClient.post(`/interviews/${interviewId}/feedback`, input);
}

export function getInterview(interviewId: string) {
  return apiClient.get<Interview>(`/interviews/${interviewId}`);
}

export function getConsolidatedFeedback(interviewId: string) {
  return apiClient.get<ConsolidatedFeedback>(`/interviews/${interviewId}/consolidated-feedback`);
}

/** How an interview mode reads on screen. "Video" is stored for existing
 * interviews and shown as "Visual Round". */
export function interviewModeLabel(mode: string | null | undefined): string {
  if (!mode) return "";
  return mode === "Video" ? "Visual Round" : mode;
}
