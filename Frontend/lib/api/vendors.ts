import { apiClient } from "./client";
import type {
  Vendor,
  VendorAccount,
  VendorAccountInput,
  VendorBankAccount,
  VendorBankAccountInput,
  VendorContactInput,
  VendorCreateInput,
  VendorDocument,
  VendorMeeting,
  VendorMeetingInput,
  VendorNote,
  VendorNoteInput,
  VendorUpdateInput,
} from "./types";

export function listVendors() {
  return apiClient.get<Vendor[]>("/vendors");
}

export function getVendor(vendorId: string) {
  return apiClient.get<Vendor>(`/vendors/${vendorId}`);
}

export function createVendor(input: VendorCreateInput) {
  return apiClient.post<Vendor>("/vendors", input);
}

export function updateVendor(vendorId: string, input: VendorUpdateInput) {
  return apiClient.patch<Vendor>(`/vendors/${vendorId}`, input);
}

export function addVendorContact(vendorId: string, input: VendorContactInput) {
  return apiClient.post<Vendor>(`/vendors/${vendorId}/contacts`, input);
}

export function addVendorAccount(vendorId: string, input: VendorAccountInput) {
  return apiClient.post<VendorAccount>(`/vendors/${vendorId}/accounts`, input);
}

export function addVendorBankAccount(vendorId: string, input: VendorBankAccountInput) {
  return apiClient.post<VendorBankAccount>(`/vendors/${vendorId}/bank-accounts`, input);
}

export function listVendorNotes(vendorId: string) {
  return apiClient.get<VendorNote[]>(`/vendors/${vendorId}/notes`);
}

export function addVendorNote(vendorId: string, input: VendorNoteInput) {
  return apiClient.post<VendorNote>(`/vendors/${vendorId}/notes`, input);
}

export function listVendorMeetings(vendorId: string) {
  return apiClient.get<VendorMeeting[]>(`/vendors/${vendorId}/meetings`);
}

export function addVendorMeeting(vendorId: string, input: VendorMeetingInput) {
  return apiClient.post<VendorMeeting>(`/vendors/${vendorId}/meetings`, input);
}

export function listVendorDocuments(vendorId: string) {
  return apiClient.get<VendorDocument[]>(`/vendors/${vendorId}/documents`);
}

export const VENDOR_STATUSES = ["Active", "On Hold"] as const;

export const VENDOR_VISIBILITIES = ["Organization Level", "Business Unit"] as const;

export const VENDOR_TYPES = [
  "Staffing Agency",
  "Implementation Partner",
  "Prime Vendor",
  "Sub Vendor",
  "Independent Contractor",
  "MSP / VMS",
] as const;

export const VENDOR_CLASSIFICATIONS = [
  "Preferred",
  "Approved",
  "Tier 1",
  "Tier 2",
  "Probationary",
  "Do Not Use",
] as const;

export const VENDOR_PAYMENT_TERMS = [
  "Net 15",
  "Net 30",
  "Net 45",
  "Net 60",
  "Due on receipt",
] as const;

export const VENDOR_NOTE_ACTIONS = [
  "Call",
  "Email",
  "Meeting",
  "Contract",
  "Escalation",
  "General",
] as const;

export const VENDOR_CONTACT_STATUSES = ["Active", "Inactive"] as const;

export const VMS_STATUSES = ["Not Initiated", "In Progress", "Approved", "Rejected"] as const;

export const BANK_ACCOUNT_TYPES = ["Checking", "Savings", "Business"] as const;

export const VENDOR_SUBMISSION_FORMAT_OPTIONS = [
  "Candidate name",
  "Contact details",
  "Current location",
  "Work authorization",
  "Availability",
  "Bill rate",
  "Pay rate",
  "Skill matrix",
  "Resume attachment",
  "Right to represent",
] as const;

export const TECHNOLOGY_OPTIONS = [
  "Java",
  "Python",
  ".NET",
  "JavaScript / TypeScript",
  "Cloud / DevOps",
  "Data & Analytics",
  "Salesforce",
  "SAP",
  "QA / Automation",
  "Cybersecurity",
  "Mobile",
  "ERP",
] as const;
