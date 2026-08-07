import { apiClient } from "./client";
import type {
  Client,
  ClientAccount,
  ClientAccountInput,
  ClientAssignment,
  ClientAssignmentInput,
  ClientContactInput,
  ClientCreateInput,
  ClientDocument,
  ClientNote,
  ClientNoteInput,
  ClientUpdateInput,
} from "./types";

export function listClients() {
  return apiClient.get<Client[]>("/clients");
}

export function getClient(clientId: string) {
  return apiClient.get<Client>(`/clients/${clientId}`);
}

export function createClient(input: ClientCreateInput) {
  return apiClient.post<Client>("/clients", input);
}

export function updateClient(clientId: string, input: ClientUpdateInput) {
  return apiClient.patch<Client>(`/clients/${clientId}`, input);
}

export function addClientContact(clientId: string, input: ClientContactInput) {
  return apiClient.post<Client>(`/clients/${clientId}/contacts`, input);
}

export function addClientAccount(clientId: string, input: ClientAccountInput) {
  return apiClient.post<ClientAccount>(`/clients/${clientId}/accounts`, input);
}

export function addClientAssignment(clientId: string, input: ClientAssignmentInput) {
  return apiClient.post<ClientAssignment>(`/clients/${clientId}/assignments`, input);
}

export function listClientNotes(clientId: string) {
  return apiClient.get<ClientNote[]>(`/clients/${clientId}/notes`);
}

export function addClientNote(clientId: string, input: ClientNoteInput) {
  return apiClient.post<ClientNote>(`/clients/${clientId}/notes`, input);
}

export function listClientDocuments(clientId: string) {
  return apiClient.get<ClientDocument[]>(`/clients/${clientId}/documents`);
}

export const CLIENT_STATUSES = ["Active", "Prospect", "Paused"] as const;

export const CLIENT_CATEGORIES = [
  "Direct",
  "Implementation Partner",
  "Staffing Partner",
  "System Integrator",
  "Internal",
] as const;

export const CLIENT_VISIBILITIES = ["Organization Level", "Business Unit"] as const;

export const CLIENT_NOTE_TYPES = ["Client", "Lead", "Applicant Reference"] as const;

export const PAYMENT_TERMS = ["Net 15", "Net 30", "Net 45", "Net 60", "Due on receipt"] as const;

export const REQUIRED_DOCUMENT_OPTIONS = [
  "Resume",
  "Right to Represent",
  "Work Authorization",
  "Photo ID",
  "Background Check",
  "Drug Test",
  "I-9",
  "W-4",
  "NDA",
  "MSA",
  "Reference Check",
  "Offer Letter",
] as const;

export const SUBMISSION_FORMAT_OPTIONS = [
  "Candidate name",
  "Contact details",
  "Current location",
  "Work authorization",
  "Availability",
  "Bill rate",
  "Pay rate",
  "Skill matrix",
  "Resume attachment",
  "Recruiter notes",
] as const;

export const INDUSTRIES = [
  "Aerospace & Defense",
  "Automotive",
  "Banking & Financial Services",
  "Biotech & Pharma",
  "Construction",
  "Consulting",
  "Consumer Goods",
  "Education",
  "Energy & Utilities",
  "Government",
  "Healthcare",
  "Insurance",
  "Manufacturing",
  "Media & Entertainment",
  "Non-profit",
  "Retail & E-commerce",
  "Technology",
  "Telecommunications",
  "Transportation & Logistics",
] as const;

export const PRACTICES = [
  "Information Technology",
  "Engineering",
  "Healthcare",
  "Finance & Accounting",
  "Professional Services",
  "Light Industrial",
] as const;

export const COUNTRIES = [
  "United States",
  "Canada",
  "India",
  "United Kingdom",
  "Australia",
] as const;

export const CLIENT_FACILITY_OPTIONS = [
  "Onsite",
  "Remote",
  "Hybrid",
  "Cafeteria",
  "Parking",
  "Badge access required",
] as const;

export const ASSIGNMENT_ROLES = [
  "Account Manager",
  "Recruiter",
  "Delivery Lead",
  "Sourcer",
  "Coordinator",
] as const;
