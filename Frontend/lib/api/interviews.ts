import { apiClient } from "./client";
import type { Interview } from "./types";

export interface InterviewFilters {
  application_id?: string;
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

export function listInterviews(filters: InterviewFilters = {}) {
  return apiClient.get<Interview[]>(`/interviews${buildQuery(filters)}`);
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
