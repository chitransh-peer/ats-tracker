import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as candidatesApi from "@/lib/api/candidates";
import type { CandidateCreateInput } from "@/lib/api/types";

export function useCandidates(filters: candidatesApi.CandidateFilters = {}) {
  return useQuery({
    queryKey: ["candidates", filters],
    queryFn: () => candidatesApi.listCandidates(filters),
  });
}

export function useCandidate(candidateId: string | undefined) {
  return useQuery({
    queryKey: ["candidates", candidateId],
    queryFn: () => candidatesApi.getCandidate(candidateId as string),
    enabled: !!candidateId,
  });
}

export function useCreateCandidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CandidateCreateInput) => candidatesApi.createCandidate(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["candidates"] }),
  });
}

export function useUpdateCandidate(candidateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: Parameters<typeof candidatesApi.updateCandidate>[1]) =>
      candidatesApi.updateCandidate(candidateId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["candidates"] });
    },
  });
}

export function useCandidateNotes(candidateId: string | undefined) {
  return useQuery({
    queryKey: ["candidates", candidateId, "notes"],
    queryFn: () => candidatesApi.listCandidateNotes(candidateId as string),
    enabled: !!candidateId,
  });
}

export function useAddCandidateNote(candidateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => candidatesApi.addCandidateNote(candidateId, body),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["candidates", candidateId, "notes"] }),
  });
}
