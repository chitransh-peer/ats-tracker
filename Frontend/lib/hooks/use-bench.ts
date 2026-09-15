import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as benchApi from "@/lib/api/bench";
import type { BenchProfileInput } from "@/lib/api/types";

export function useBenchProfiles(filters: benchApi.BenchFilters = {}) {
  return useQuery({
    queryKey: ["talent-bench", filters],
    queryFn: () => benchApi.listBenchProfiles(filters),
  });
}

/** Paginated variant for the Talent Bench grid — returns `{ data, total }`. */
export function useBenchProfilesPage(filters: benchApi.BenchFilters = {}) {
  return useQuery({
    queryKey: ["talent-bench", "page", filters],
    queryFn: () => benchApi.listBenchProfilesPage(filters),
    placeholderData: (previous) => previous,
  });
}

export function useBenchSummary() {
  return useQuery({ queryKey: ["talent-bench", "summary"], queryFn: benchApi.getBenchSummary });
}

export function useBenchProfile(profileId: string | undefined) {
  return useQuery({
    queryKey: ["talent-bench", profileId, "detail"],
    queryFn: () => benchApi.getBenchProfile(profileId as string),
    enabled: !!profileId,
  });
}

function useInvalidateBench() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["talent-bench"] });
}

export function useAddToBench() {
  const invalidate = useInvalidateBench();
  return useMutation({
    mutationFn: (input: BenchProfileInput & { candidate_id: string }) => benchApi.addToBench(input),
    onSuccess: invalidate,
  });
}

export function useUpdateBenchProfile() {
  const invalidate = useInvalidateBench();
  return useMutation({
    mutationFn: ({ profileId, input }: { profileId: string; input: BenchProfileInput }) =>
      benchApi.updateBenchProfile(profileId, input),
    onSuccess: invalidate,
  });
}

export function useRemoveFromBench() {
  const invalidate = useInvalidateBench();
  return useMutation({
    mutationFn: (profileId: string) => benchApi.removeFromBench(profileId),
    onSuccess: invalidate,
  });
}

export function useBenchSubmissions(profileId: string | undefined) {
  return useQuery({
    queryKey: ["talent-bench", profileId, "submissions"],
    queryFn: () => benchApi.listBenchSubmissions(profileId as string),
    enabled: !!profileId,
  });
}

export function useBulkAddToBench() {
  const invalidate = useInvalidateBench();
  return useMutation({
    mutationFn: (candidateIds: string[]) => benchApi.bulkAddToBench(candidateIds),
    onSuccess: invalidate,
  });
}
