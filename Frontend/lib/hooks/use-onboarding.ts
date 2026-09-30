import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as onboardingApi from "@/lib/api/onboarding";

export function useOnboardingCases(filters: onboardingApi.OnboardingFilters = {}) {
  return useQuery({
    queryKey: ["onboarding", filters],
    queryFn: () => onboardingApi.listOnboardingCases(filters),
  });
}

export function useOnboardingCasesPage(filters: onboardingApi.OnboardingFilters = {}) {
  return useQuery({
    queryKey: ["onboarding", "page", filters],
    queryFn: () => onboardingApi.listOnboardingCasesPage(filters),
    placeholderData: (previous) => previous,
  });
}

export function useOnboardingSummary() {
  return useQuery({
    queryKey: ["onboarding", "summary"],
    queryFn: onboardingApi.getOnboardingSummary,
  });
}

export function useOnboardingActions() {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["onboarding"] });
  return {
    updateCase: useMutation({
      mutationFn: ({
        id,
        ...input
      }: { id: string } & Parameters<typeof onboardingApi.updateOnboardingCase>[1]) =>
        onboardingApi.updateOnboardingCase(id, input),
      onSuccess: invalidate,
    }),
    complete: useMutation({
      mutationFn: (id: string) => onboardingApi.completeOnboardingCase(id),
      onSuccess: invalidate,
    }),
    cancel: useMutation({
      mutationFn: (id: string) => onboardingApi.cancelOnboardingCase(id),
      onSuccess: invalidate,
    }),
    addTask: useMutation({
      mutationFn: ({
        caseId,
        ...input
      }: { caseId: string } & Parameters<typeof onboardingApi.addOnboardingTask>[1]) =>
        onboardingApi.addOnboardingTask(caseId, input),
      onSuccess: invalidate,
    }),
    updateTask: useMutation({
      mutationFn: ({
        taskId,
        ...input
      }: { taskId: string } & Parameters<typeof onboardingApi.updateOnboardingTask>[1]) =>
        onboardingApi.updateOnboardingTask(taskId, input),
      onSuccess: invalidate,
    }),
  };
}
