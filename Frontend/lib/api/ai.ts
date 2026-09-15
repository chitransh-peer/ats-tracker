import { apiClient, ApiError } from "./client";
import type { AIConfig, AIEvaluation, JDResumeComparison } from "./types";

export function evaluateApplication(applicationId: string) {
  return apiClient.post<AIEvaluation>(`/ai/evaluate-application/${applicationId}`);
}

export function getEvaluation(evaluationId: string) {
  return apiClient.get<AIEvaluation>(`/ai/evaluations/${evaluationId}`);
}

export function overrideEvaluation(
  evaluationId: string,
  recommendationLabel: string,
  note?: string,
) {
  return apiClient.post<AIEvaluation>(`/ai/evaluations/${evaluationId}/override`, {
    recommendation_label: recommendationLabel,
    note,
  });
}

export async function getLatestAiReview(applicationId: string): Promise<AIEvaluation | null> {
  try {
    return await apiClient.get<AIEvaluation>(`/applications/${applicationId}/ai-review`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export function compareJdResume(applicationId: string) {
  return apiClient.get<JDResumeComparison>(`/ai/compare/jd-resume/${applicationId}`);
}

export function getAiConfig() {
  return apiClient.get<AIConfig>("/ai/config");
}
