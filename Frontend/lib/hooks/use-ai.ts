import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as aiApi from "@/lib/api/ai";
import type { AIEvaluation } from "@/lib/api/types";

const PENDING_STATUSES = new Set(["pending", "processing"]);

export function useAiReview(applicationId: string | undefined) {
  return useQuery({
    queryKey: ["ai-review", applicationId],
    queryFn: () => aiApi.getLatestAiReview(applicationId as string),
    enabled: !!applicationId,
  });
}

export function useEvaluation(evaluationId: string | undefined) {
  return useQuery({
    queryKey: ["ai-evaluations", evaluationId],
    queryFn: () => aiApi.getEvaluation(evaluationId as string),
    enabled: !!evaluationId,
    refetchInterval: (query) => {
      const data = query.state.data as AIEvaluation | undefined;
      return data && PENDING_STATUSES.has(data.status) ? 1500 : false;
    },
  });
}

export function useJdResumeComparison(applicationId: string | undefined) {
  return useQuery({
    queryKey: ["ai-jd-comparison", applicationId],
    queryFn: () => aiApi.compareJdResume(applicationId as string),
    enabled: !!applicationId,
  });
}

export function useEvaluateApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (applicationId: string) => aiApi.evaluateApplication(applicationId),
    onSuccess: (evaluation) => {
      queryClient.invalidateQueries({ queryKey: ["ai-review", evaluation.application_id] });
      queryClient.invalidateQueries({ queryKey: ["ai-evaluations", evaluation.id] });
    },
  });
}

export function useOverrideEvaluation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      evaluationId,
      recommendationLabel,
      note,
    }: {
      evaluationId: string;
      recommendationLabel: string;
      note?: string;
    }) => aiApi.overrideEvaluation(evaluationId, recommendationLabel, note),
    onSuccess: (evaluation) => {
      queryClient.invalidateQueries({ queryKey: ["ai-review", evaluation.application_id] });
      queryClient.invalidateQueries({ queryKey: ["ai-evaluations", evaluation.id] });
    },
  });
}

export function useAiConfig() {
  return useQuery({ queryKey: ["ai", "config"], queryFn: aiApi.getAiConfig });
}
