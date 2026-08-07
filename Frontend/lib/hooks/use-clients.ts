import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as clientsApi from "@/lib/api/clients";
import type {
  ClientAccountInput,
  ClientAssignmentInput,
  ClientContactInput,
  ClientCreateInput,
  ClientNoteInput,
  ClientUpdateInput,
} from "@/lib/api/types";

export function useClients() {
  return useQuery({ queryKey: ["clients"], queryFn: clientsApi.listClients });
}

export function useClient(clientId: string) {
  return useQuery({
    queryKey: ["clients", clientId],
    queryFn: () => clientsApi.getClient(clientId),
    enabled: Boolean(clientId),
  });
}

export function useCreateClient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ClientCreateInput) => clientsApi.createClient(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clients"] }),
  });
}

export function useUpdateClient(clientId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ClientUpdateInput) => clientsApi.updateClient(clientId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.invalidateQueries({ queryKey: ["clients", clientId] });
    },
  });
}

export function useAddClientContact(clientId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ClientContactInput) => clientsApi.addClientContact(clientId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clients", clientId] }),
  });
}

export function useAddClientAccount(clientId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ClientAccountInput) => clientsApi.addClientAccount(clientId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clients", clientId] }),
  });
}

export function useAddClientAssignment(clientId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ClientAssignmentInput) => clientsApi.addClientAssignment(clientId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clients", clientId] }),
  });
}

export function useClientNotes(clientId: string) {
  return useQuery({
    queryKey: ["clients", clientId, "notes"],
    queryFn: () => clientsApi.listClientNotes(clientId),
    enabled: Boolean(clientId),
  });
}

export function useAddClientNote(clientId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ClientNoteInput) => clientsApi.addClientNote(clientId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clients", clientId, "notes"] }),
  });
}

export function useClientDocuments(clientId: string) {
  return useQuery({
    queryKey: ["clients", clientId, "documents"],
    queryFn: () => clientsApi.listClientDocuments(clientId),
    enabled: Boolean(clientId),
  });
}
