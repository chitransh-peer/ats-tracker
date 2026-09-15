import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as hotlistsApi from "@/lib/api/hotlists";
import type { HotlistInput } from "@/lib/api/types";

export function useHotlists(status?: string) {
  return useQuery({
    queryKey: ["hotlists", status ?? "all"],
    queryFn: () => hotlistsApi.listHotlists(status),
  });
}

export function useHotlist(hotlistId: string | undefined) {
  return useQuery({
    queryKey: ["hotlists", hotlistId],
    queryFn: () => hotlistsApi.getHotlist(hotlistId as string),
    enabled: !!hotlistId,
  });
}

export function useHotlistSends(hotlistId: string | undefined) {
  return useQuery({
    queryKey: ["hotlists", hotlistId, "sends"],
    queryFn: () => hotlistsApi.listHotlistSends(hotlistId as string),
    enabled: !!hotlistId,
    // A send runs in the background; poll briefly so counts fill in live.
    refetchInterval: (query) => {
      const rows = query.state.data ?? [];
      return rows.some((s) => s.status === "pending" || s.status === "sending") ? 2000 : false;
    },
  });
}

export function useSuggestedMembers() {
  return useQuery({ queryKey: ["hotlists", "suggested"], queryFn: hotlistsApi.suggestedMembers });
}

function useInvalidateHotlists() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["hotlists"] });
}

export function useCreateHotlist() {
  const invalidate = useInvalidateHotlists();
  return useMutation({
    mutationFn: (input: HotlistInput & { name: string }) => hotlistsApi.createHotlist(input),
    onSuccess: invalidate,
  });
}

export function useUpdateHotlist(hotlistId: string) {
  const invalidate = useInvalidateHotlists();
  return useMutation({
    mutationFn: (input: HotlistInput) => hotlistsApi.updateHotlist(hotlistId, input),
    onSuccess: invalidate,
  });
}

export function useDeleteHotlist() {
  const invalidate = useInvalidateHotlists();
  return useMutation({
    mutationFn: (hotlistId: string) => hotlistsApi.deleteHotlist(hotlistId),
    onSuccess: invalidate,
  });
}

export function useSetHotlistMembers(hotlistId: string) {
  const invalidate = useInvalidateHotlists();
  return useMutation({
    mutationFn: (benchProfileIds: string[]) =>
      hotlistsApi.setHotlistMembers(hotlistId, benchProfileIds),
    onSuccess: invalidate,
  });
}

export function useAddRecipients(hotlistId: string) {
  const invalidate = useInvalidateHotlists();
  return useMutation({
    mutationFn: (
      recipients: {
        first_name?: string | null;
        last_name?: string | null;
        email: string;
        company?: string | null;
      }[],
    ) => hotlistsApi.addHotlistRecipients(hotlistId, recipients),
    onSuccess: invalidate,
  });
}

export function useAddRecipientsFromParties(hotlistId: string) {
  const invalidate = useInvalidateHotlists();
  return useMutation({
    mutationFn: (input: { client_ids?: string[]; vendor_ids?: string[] }) =>
      hotlistsApi.addRecipientsFromParties(hotlistId, input),
    onSuccess: invalidate,
  });
}

export function useImportRecipients(hotlistId: string) {
  const invalidate = useInvalidateHotlists();
  return useMutation({
    mutationFn: (file: File) => hotlistsApi.importRecipients(hotlistId, file),
    onSuccess: invalidate,
  });
}

export function useRemoveRecipient(hotlistId: string) {
  const invalidate = useInvalidateHotlists();
  return useMutation({
    mutationFn: (recipientId: string) => hotlistsApi.removeHotlistRecipient(hotlistId, recipientId),
    onSuccess: invalidate,
  });
}

export function useSetRecipientUnsubscribed(hotlistId: string) {
  const invalidate = useInvalidateHotlists();
  return useMutation({
    mutationFn: ({ recipientId, unsubscribed }: { recipientId: string; unsubscribed: boolean }) =>
      hotlistsApi.setRecipientUnsubscribed(hotlistId, recipientId, unsubscribed),
    onSuccess: invalidate,
  });
}

export function useSendHotlist(hotlistId: string) {
  const invalidate = useInvalidateHotlists();
  return useMutation({
    mutationFn: () => hotlistsApi.sendHotlist(hotlistId),
    onSuccess: invalidate,
  });
}
