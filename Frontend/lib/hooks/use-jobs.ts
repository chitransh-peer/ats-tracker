import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as jobsApi from "@/lib/api/jobs";
import type {
  JobCreateInput,
  JobCustomFieldInput,
  JobNoteInput,
  JobSearchCriteriaInput,
  JobUpdateInput,
} from "@/lib/api/types";

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

export function useJobSubmissions(jobId: string) {
  return useQuery({
    queryKey: ["jobs", jobId, "submissions"],
    queryFn: () => jobsApi.jobSubmissions(jobId),
    enabled: Boolean(jobId),
  });
}

export function useJobNotes(jobId: string) {
  return useQuery({
    queryKey: ["jobs", jobId, "notes"],
    queryFn: () => jobsApi.listJobNotes(jobId),
    enabled: Boolean(jobId),
  });
}

export function useAddJobNote(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: JobNoteInput) => jobsApi.addJobNote(jobId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs", jobId, "notes"] }),
  });
}

export function useJobDocuments(jobId: string) {
  return useQuery({
    queryKey: ["jobs", jobId, "documents"],
    queryFn: () => jobsApi.listJobDocuments(jobId),
    enabled: Boolean(jobId),
  });
}

export function useSaveJobSearchCriteria(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: JobSearchCriteriaInput) => jobsApi.saveJobSearchCriteria(jobId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs", jobId] }),
  });
}

export function useSetJobCustomField(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: JobCustomFieldInput) => jobsApi.setJobCustomField(jobId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs", jobId] }),
  });
}

export function useUpdateJob(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: JobUpdateInput) => jobsApi.updateJob(jobId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId] });
    },
  });
}
