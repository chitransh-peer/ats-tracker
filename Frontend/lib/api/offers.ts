import { apiClient } from "./client";
import type { Offer, OfferSummary } from "./types";

export interface OfferFilters {
  application_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

function buildQuery(params: object): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params as Record<string, string | undefined>)) {
    if (value) query.set(key, value);
  }
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

function offerQuery(filters: OfferFilters): string {
  return buildQuery({
    ...filters,
    limit: filters.limit?.toString(),
    offset: filters.offset?.toString(),
  });
}

export function listOffers(filters: OfferFilters = {}) {
  return apiClient.get<Offer[]>(`/offers${offerQuery(filters)}`);
}

export function listOffersPage(filters: OfferFilters = {}) {
  return apiClient.getPage<Offer>(`/offers${offerQuery(filters)}`);
}

export function getOfferSummary() {
  return apiClient.get<OfferSummary>("/offers/summary");
}

export const OFFER_PAY_TYPES = ["Salary", "Hourly"] as const;
export const OFFER_CURRENCIES = ["USD", "INR", "CAD", "GBP", "AUD"] as const;
export const OFFER_EMPLOYMENT_TYPES = [
  "Full-time",
  "Part-time",
  "Contract",
  "Contract-to-hire",
] as const;
/** How the hire is engaged; mirrors OfferTaxTerm on the server. */
export const OFFER_TAX_TERMS = ["W-2", "1099", "C2C", "India Payroll", "India Contract"] as const;

export interface OfferInput {
  application_id: string;
  pay_type: string;
  base_salary?: number | null;
  hourly_rate?: number | null;
  currency: string;
  employment_type?: string | null;
  tax_term?: string | null;
  contract_duration?: string | null;
  bonus?: number | null;
  equity?: string | null;
  joining_date?: string | null;
}

/** An offer's pay as it reads on screen: "₹25,00,000 / yr" or "$85.00 / hr". */
export function formatOfferPay(offer: {
  pay_type: string;
  base_salary: number | null;
  hourly_rate: number | null;
  currency: string;
}): string {
  const hourly = offer.pay_type === "Hourly";
  const amount = hourly ? offer.hourly_rate : offer.base_salary;
  if (amount == null) return "—";
  const formatted = new Intl.NumberFormat(offer.currency === "INR" ? "en-IN" : "en-US", {
    style: "currency",
    currency: offer.currency || "USD",
    maximumFractionDigits: hourly ? 2 : 0,
  }).format(amount);
  return `${formatted} / ${hourly ? "hr" : "yr"}`;
}

export function createOffer(input: OfferInput) {
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
