import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as applicationsApi from "@/lib/api/applications";

export function useApplications(filters: applicationsApi.ApplicationFilters = {}) {
  return useQuery({
    queryKey: ["applications", filters],
    queryFn: () => applicationsApi.listApplications(filters),
  });
}

export function useApplicationTimeline(applicationId: string | undefined) {
  return useQuery({
    queryKey: ["applications", applicationId, "timeline"],
    queryFn: () => applicationsApi.getApplicationTimeline(applicationId as string),
    enabled: !!applicationId,
  });
}

export function useCreateApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: applicationsApi.createApplication,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });
}

export function useMoveApplicationStage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      applicationId,
      toStageId,
      note,
    }: {
      applicationId: string;
      toStageId: string;
      note?: string;
    }) => applicationsApi.moveApplicationStage(applicationId, toStageId, note),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });
}

export function useApplicationAction() {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["applications"] });
  return {
    hold: useMutation({
      mutationFn: ({ applicationId, note }: { applicationId: string; note?: string }) =>
        applicationsApi.holdApplication(applicationId, note),
      onSuccess: invalidate,
    }),
    reject: useMutation({
      mutationFn: ({ applicationId, note }: { applicationId: string; note?: string }) =>
        applicationsApi.rejectApplication(applicationId, note),
      onSuccess: invalidate,
    }),
    restore: useMutation({
      mutationFn: ({ applicationId, note }: { applicationId: string; note?: string }) =>
        applicationsApi.restoreApplication(applicationId, note),
      onSuccess: invalidate,
    }),
  };
}
