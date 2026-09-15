import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as applicationsApi from "@/lib/api/applications";

export function useApplications(filters: applicationsApi.ApplicationFilters = {}) {
  return useQuery({
    queryKey: ["applications", filters],
    queryFn: () => applicationsApi.listApplications(filters),
  });
}

/** Paginated variant for the Applications grid — returns `{ data, total }`. */
export function useApplicationsPage(filters: applicationsApi.ApplicationFilters = {}) {
  return useQuery({
    queryKey: ["applications", "page", filters],
    queryFn: () => applicationsApi.listApplicationsPage(filters),
    placeholderData: (previous) => previous,
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

export function useApplication(applicationId: string | undefined) {
  return useQuery({
    queryKey: ["applications", applicationId, "detail"],
    queryFn: () => applicationsApi.getApplication(applicationId as string),
    enabled: !!applicationId,
  });
}

export function useBulkRejectApplications() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ applicationIds, note }: { applicationIds: string[]; note?: string }) =>
      applicationsApi.bulkRejectApplications(applicationIds, note),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });
}

export function useBulkHoldApplications() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ applicationIds, note }: { applicationIds: string[]; note?: string }) =>
      applicationsApi.bulkHoldApplications(applicationIds, note),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });
}
