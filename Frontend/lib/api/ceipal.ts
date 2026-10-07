import { apiClient, downloadFile } from "./client";

export type CeipalTableKind =
  | "applicants"
  | "documents"
  | "education"
  | "notes"
  | "submissions"
  | "submission_notes"
  | "users"
  | "degrees";

export interface CeipalImport {
  id: string;
  name: string;
  status: "staging" | "importing" | "documents" | "completed" | "undoing" | "undone";
  applicants_total: number;
  applicants_processed: number;
  created_count: number;
  updated_count: number;
  rejected_count: number;
  documents_expected: number;
  documents_attached: number;
  documents_orphaned: number;
  education_count: number;
  submissions_count: number;
  submissions_linked: number;
  kept_on_undo: number;
  /** Rows staged per table; only while the status is "staging". */
  staged: Partial<Record<CeipalTableKind, number>>;
  created_at: string;
  updated_at: string;
}

export interface CeipalDocumentResult {
  file_name: string;
  outcome: "attached" | "skipped" | "rejected";
  message: string;
}

export interface CeipalResumeRef {
  document_id: string;
  file_name: string;
}

export interface CeipalCandidateRow {
  candidate_id: string;
  full_name: string;
  /** Ceipal header -> value, exactly as Ceipal had it. */
  values: Record<string, string>;
  resume: CeipalResumeRef | null;
}

export interface CeipalCandidatePage {
  columns: string[];
  total: number;
  rows: CeipalCandidateRow[];
}

export interface CeipalSubmission {
  submission_id: string;
  job_id: string;
  job_code: string;
  record_type: string;
  status: string;
  source: string;
  submitted_by: string;
  submitted_on: string;
  pay_rate: string;
  bill_rate: string;
  rating: string;
  resume: string;
  date_available: string;
  notes: { subject: string; note: string; created_by: string; created_at: string }[];
  application_id: string | null;
  job_title: string | null;
}

export interface CeipalProfile {
  candidate_id: string;
  ceipal_id: string;
  columns: string[];
  values: Record<string, string>;
  submissions: CeipalSubmission[];
  resume: CeipalResumeRef | null;
}

export function createCeipalImport(name: string) {
  return apiClient.post<CeipalImport>("/imports/ceipal", { name });
}

export function listCeipalImports() {
  return apiClient.get<CeipalImport[]>("/imports/ceipal?limit=10");
}

export function getCeipalImport(importId: string) {
  return apiClient.get<CeipalImport>(`/imports/ceipal/${importId}`);
}

export function stageCeipalRows(
  importId: string,
  input: {
    kind: CeipalTableKind;
    source: string;
    first_row: number;
    headers: string[];
    rows: Record<string, string>[];
  },
) {
  return apiClient.post<{ kind: string; staged: number }>(
    `/imports/ceipal/${importId}/rows`,
    input,
  );
}

/** Imports the next chunk of applicants; call until the status leaves "importing". */
export function processCeipalImport(importId: string) {
  return apiClient.post<CeipalImport>(`/imports/ceipal/${importId}/process`);
}

export function pendingCeipalDocuments(importId: string, offset: number, limit = 5000) {
  return apiClient.get<{ names: string[]; total_pending: number }>(
    `/imports/ceipal/${importId}/documents/pending?offset=${offset}&limit=${limit}`,
  );
}

export function uploadCeipalDocuments(importId: string, files: { name: string; blob: Blob }[]) {
  const form = new FormData();
  for (const file of files) form.append("files", file.blob, file.name);
  return apiClient.postForm<{ results: CeipalDocumentResult[]; job: CeipalImport }>(
    `/imports/ceipal/${importId}/documents`,
    form,
  );
}

export function finishCeipalImport(importId: string) {
  return apiClient.post<CeipalImport>(`/imports/ceipal/${importId}/finish`);
}

/** Undoes the next batch; call until the status is "undone". */
export function undoCeipalImport(importId: string) {
  return apiClient.post<CeipalImport>(`/imports/ceipal/${importId}/undo`);
}

export function downloadCeipalReport(job: CeipalImport) {
  return downloadFile(`/imports/ceipal/${job.id}/report`, `${job.name}-not-imported.csv`);
}

export function listCeipalCandidates(filters: { search?: string; limit: number; offset: number }) {
  const query = new URLSearchParams({
    limit: String(filters.limit),
    offset: String(filters.offset),
  });
  if (filters.search) query.set("search", filters.search);
  return apiClient.get<CeipalCandidatePage>(`/ceipal/candidates?${query.toString()}`);
}

export function getCeipalProfile(candidateId: string) {
  return apiClient.get<CeipalProfile>(`/ceipal/candidates/${candidateId}`);
}
