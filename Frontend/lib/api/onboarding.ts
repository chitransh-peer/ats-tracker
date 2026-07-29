import { apiClient } from "./client";
import type { OnboardingCase, OnboardingTask } from "./types";

export interface OnboardingFilters {
  status?: string;
  application_id?: string;
}

function buildQuery(params: object): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params as Record<string, string | undefined>)) {
    if (value) query.set(key, value);
  }
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export function listOnboardingCases(filters: OnboardingFilters = {}) {
  return apiClient.get<OnboardingCase[]>(`/onboarding${buildQuery(filters)}`);
}

export function getOnboardingCase(caseId: string) {
  return apiClient.get<OnboardingCase>(`/onboarding/${caseId}`);
}

export function updateOnboardingCase(
  caseId: string,
  input: { start_date?: string | null; coordinator_id?: string | null; notes?: string | null },
) {
  return apiClient.patch<OnboardingCase>(`/onboarding/${caseId}`, input);
}

export function completeOnboardingCase(caseId: string) {
  return apiClient.post<OnboardingCase>(`/onboarding/${caseId}/complete`);
}

export function cancelOnboardingCase(caseId: string) {
  return apiClient.post<OnboardingCase>(`/onboarding/${caseId}/cancel`);
}

export function addOnboardingTask(
  caseId: string,
  input: { title: string; category: string; assignee_id?: string | null; due_date?: string | null },
) {
  return apiClient.post<OnboardingTask>(`/onboarding/${caseId}/tasks`, input);
}

export function updateOnboardingTask(
  taskId: string,
  input: {
    title?: string;
    category?: string;
    status?: string;
    assignee_id?: string | null;
    due_date?: string | null;
  },
) {
  return apiClient.patch<OnboardingTask>(`/onboarding/tasks/${taskId}`, input);
}
