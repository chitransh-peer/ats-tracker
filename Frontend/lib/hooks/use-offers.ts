import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as offersApi from "@/lib/api/offers";

export function useOffers(filters: offersApi.OfferFilters = {}) {
  return useQuery({
    queryKey: ["offers", filters],
    queryFn: () => offersApi.listOffers(filters),
  });
}

export function useCreateOffer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: offersApi.createOffer,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["offers"] }),
  });
}

export function useOfferAction() {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["offers"] });
  return {
    submitForApproval: useMutation({
      mutationFn: (id: string) => offersApi.submitOfferForApproval(id),
      onSuccess: invalidate,
    }),
    approve: useMutation({
      mutationFn: (id: string) => offersApi.approveOffer(id),
      onSuccess: invalidate,
    }),
    reject: useMutation({
      mutationFn: (id: string) => offersApi.rejectOffer(id),
      onSuccess: invalidate,
    }),
    send: useMutation({
      mutationFn: (id: string) => offersApi.sendOffer(id),
      onSuccess: invalidate,
    }),
    accept: useMutation({
      mutationFn: (id: string) => offersApi.acceptOffer(id),
      onSuccess: invalidate,
    }),
    decline: useMutation({
      mutationFn: (id: string) => offersApi.declineOffer(id),
      onSuccess: invalidate,
    }),
  };
}
