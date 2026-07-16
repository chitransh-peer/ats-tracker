import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as jobsApi from "@/lib/api/jobs";
import type { JobCreateInput } from "@/lib/api/types";

export function useJobs(filters: jobsApi.JobFilters = {}) {
  return useQuery({
    queryKey: ["jobs", filters],
    queryFn: () => jobsApi.listJobs(filters),
  });
}

export function useJob(jobId: string | undefined) {
  return useQuery({
    queryKey: ["jobs", jobId],
    queryFn: () => jobsApi.getJob(jobId as string),
    enabled: !!jobId,
  });
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: JobCreateInput) => jobsApi.createJob(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useJobAction(jobId: string) {
  const queryClient = useQueryClient();
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
  };
  return {
    publish: useMutation({ mutationFn: () => jobsApi.publishJob(jobId), onSuccess: invalidate }),
    unpublish: useMutation({
      mutationFn: () => jobsApi.unpublishJob(jobId),
      onSuccess: invalidate,
    }),
    close: useMutation({ mutationFn: () => jobsApi.closeJob(jobId), onSuccess: invalidate }),
    hold: useMutation({ mutationFn: () => jobsApi.holdJob(jobId), onSuccess: invalidate }),
    cancel: useMutation({ mutationFn: () => jobsApi.cancelJob(jobId), onSuccess: invalidate }),
  };
}
