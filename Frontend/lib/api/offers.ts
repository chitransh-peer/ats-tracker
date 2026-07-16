import { apiClient } from "./client";
import type { Offer } from "./types";

export interface OfferFilters {
  application_id?: string;
  status?: string;
}

function buildQuery(params: object): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params as Record<string, string | undefined>)) {
    if (value) query.set(key, value);
  }
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export function listOffers(filters: OfferFilters = {}) {
  return apiClient.get<Offer[]>(`/offers${buildQuery(filters)}`);
}

export function createOffer(input: {
  application_id: string;
  base_salary: number;
  bonus?: number | null;
  equity?: string | null;
  joining_date?: string | null;
}) {
  return apiClient.post<Offer>("/offers", input);
}

export function submitOfferForApproval(offerId: string, note?: string) {
  return apiClient.post<Offer>(`/offers/${offerId}/submit-approval`, { note });
}

export function approveOffer(offerId: string, note?: string) {
  return apiClient.post<Offer>(`/offers/${offerId}/approve`, { note });
}

export function rejectOffer(offerId: string, note?: string) {
  return apiClient.post<Offer>(`/offers/${offerId}/reject`, { note });
}

export function sendOffer(offerId: string) {
  return apiClient.post<Offer>(`/offers/${offerId}/send`);
}

export function acceptOffer(offerId: string) {
  return apiClient.post<Offer>(`/offers/${offerId}/accept`);
}

export function declineOffer(offerId: string) {
  return apiClient.post<Offer>(`/offers/${offerId}/decline`);
}
