import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as interviewsApi from "@/lib/api/interviews";

export function useInterviews(filters: interviewsApi.InterviewFilters = {}) {
  return useQuery({
    queryKey: ["interviews", filters],
    queryFn: () => interviewsApi.listInterviews(filters),
  });
}

export function useCreateInterview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: interviewsApi.createInterview,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["interviews"] }),
  });
}

export function useSubmitInterviewFeedback(interviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: Parameters<typeof interviewsApi.submitInterviewFeedback>[1]) =>
      interviewsApi.submitInterviewFeedback(interviewId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["interviews"] }),
  });
}

export function useInterview(interviewId: string | undefined) {
  return useQuery({
    queryKey: ["interviews", interviewId, "detail"],
    queryFn: () => interviewsApi.getInterview(interviewId as string),
    enabled: !!interviewId,
  });
}

export function useConsolidatedFeedback(interviewId: string | undefined) {
  return useQuery({
    queryKey: ["interviews", interviewId, "consolidated-feedback"],
    queryFn: () => interviewsApi.getConsolidatedFeedback(interviewId as string),
    enabled: !!interviewId,
  });
}

export function useUpdateInterview(interviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { status?: string; scheduled_at?: string }) =>
      interviewsApi.updateInterview(interviewId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["interviews"] }),
  });
}
