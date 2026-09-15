import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as candidatesApi from "@/lib/api/candidates";
import type { CandidateCreateInput, SendMessageInput } from "@/lib/api/types";

export function useCandidates(filters: candidatesApi.CandidateFilters = {}) {
  return useQuery({
    queryKey: ["candidates", filters],
    queryFn: () => candidatesApi.listCandidates(filters),
  });
}

/** Paginated variant for the Candidates grid — returns `{ data, total }` so
 * the page can render a pager instead of silently showing only the first
 * page's worth of rows. */
export function useCandidatesPage(filters: candidatesApi.CandidateFilters = {}) {
  return useQuery({
    queryKey: ["candidates", "page", filters],
    queryFn: () => candidatesApi.listCandidatesPage(filters),
    placeholderData: (previous) => previous,
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

export function useCandidateMessages(candidateId: string | undefined) {
  return useQuery({
    queryKey: ["candidates", candidateId, "messages"],
    queryFn: () => candidatesApi.listCandidateMessages(candidateId as string),
    enabled: !!candidateId,
  });
}

export function useSendCandidateMessage(candidateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SendMessageInput) => candidatesApi.sendCandidateMessage(candidateId, input),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["candidates", candidateId, "messages"] }),
  });
}
