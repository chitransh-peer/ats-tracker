import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as vendorsApi from "@/lib/api/vendors";
import type {
  VendorAccountInput,
  VendorBankAccountInput,
  VendorContactInput,
  VendorCreateInput,
  VendorMeetingInput,
  VendorNoteInput,
  VendorUpdateInput,
} from "@/lib/api/types";

export function useVendors() {
  return useQuery({ queryKey: ["vendors"], queryFn: vendorsApi.listVendors });
}

export function useVendor(vendorId: string) {
  return useQuery({
    queryKey: ["vendors", vendorId],
    queryFn: () => vendorsApi.getVendor(vendorId),
    enabled: Boolean(vendorId),
  });
}

export function useCreateVendor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: VendorCreateInput) => vendorsApi.createVendor(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vendors"] }),
  });
}

export function useUpdateVendor(vendorId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: VendorUpdateInput) => vendorsApi.updateVendor(vendorId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      queryClient.invalidateQueries({ queryKey: ["vendors", vendorId] });
    },
  });
}

export function useAddVendorContact(vendorId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: VendorContactInput) => vendorsApi.addVendorContact(vendorId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vendors", vendorId] }),
  });
}

export function useAddVendorAccount(vendorId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: VendorAccountInput) => vendorsApi.addVendorAccount(vendorId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vendors", vendorId] }),
  });
}

export function useAddVendorBankAccount(vendorId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: VendorBankAccountInput) => vendorsApi.addVendorBankAccount(vendorId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vendors", vendorId] }),
  });
}

export function useVendorNotes(vendorId: string) {
  return useQuery({
    queryKey: ["vendors", vendorId, "notes"],
    queryFn: () => vendorsApi.listVendorNotes(vendorId),
    enabled: Boolean(vendorId),
  });
}

export function useAddVendorNote(vendorId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: VendorNoteInput) => vendorsApi.addVendorNote(vendorId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vendors", vendorId, "notes"] }),
  });
}

export function useVendorMeetings(vendorId: string) {
  return useQuery({
    queryKey: ["vendors", vendorId, "meetings"],
    queryFn: () => vendorsApi.listVendorMeetings(vendorId),
    enabled: Boolean(vendorId),
  });
}

export function useAddVendorMeeting(vendorId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: VendorMeetingInput) => vendorsApi.addVendorMeeting(vendorId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vendors", vendorId, "meetings"] }),
  });
}

export function useVendorDocuments(vendorId: string) {
  return useQuery({
    queryKey: ["vendors", vendorId, "documents"],
    queryFn: () => vendorsApi.listVendorDocuments(vendorId),
    enabled: Boolean(vendorId),
  });
}
