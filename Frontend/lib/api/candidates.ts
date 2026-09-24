import { apiClient, downloadFile } from "./client";
import type {
  CandidateDocument,
  Candidate,
  CandidateCreateInput,
  CandidateNote,
  OutboundMessage,
  SendMessageInput,
} from "./types";

export interface CandidateFilters {
  status?: string;
  pool?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}

function buildQuery(params: Record<string, string | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) query.set(key, value);
  }
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export function listCandidatesPage(filters: CandidateFilters = {}) {
  return apiClient.getPage<Candidate>(
    `/candidates${buildQuery({
      status: filters.status,
      pool: filters.pool ? "true" : undefined,
      search: filters.search,
      limit: filters.limit?.toString(),
      offset: filters.offset?.toString(),
    })}`,
  );
}

export function listCandidates(filters: CandidateFilters = {}) {
  return apiClient.get<Candidate[]>(
    `/candidates${buildQuery({
      status: filters.status,
      pool: filters.pool ? "true" : undefined,
      search: filters.search,
    })}`,
  );
}

export function getCandidate(candidateId: string) {
  return apiClient.get<Candidate>(`/candidates/${candidateId}`);
}

export function createCandidate(input: CandidateCreateInput) {
  return apiClient.post<Candidate>("/candidates", input);
}

export function updateCandidate(
  candidateId: string,
  input: Partial<CandidateCreateInput> & { status?: string; rating?: number },
) {
  return apiClient.patch<Candidate>(`/candidates/${candidateId}`, input);
}

export function addCandidateNote(candidateId: string, body: string) {
  return apiClient.post<CandidateNote>(`/candidates/${candidateId}/notes`, { body });
}

export function listCandidateNotes(candidateId: string) {
  return apiClient.get<CandidateNote[]>(`/candidates/${candidateId}/notes`);
}

export function setCandidateTags(candidateId: string, tags: string[]) {
  return apiClient.post<Candidate>(`/candidates/${candidateId}/tags`, { tags });
}

export function uploadCandidateDocument(candidateId: string, file: File, documentType = "resume") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_type", documentType);
  return apiClient.postForm(`/candidates/${candidateId}/documents`, formData);
}

export function listCandidateMessages(candidateId: string) {
  return apiClient.get<OutboundMessage[]>(`/candidates/${candidateId}/messages`);
}

export function sendCandidateMessage(candidateId: string, input: SendMessageInput) {
  return apiClient.post<OutboundMessage>(`/candidates/${candidateId}/messages`, input);
}

export function listCandidateDocuments(candidateId: string) {
  return apiClient.get<CandidateDocument[]>(`/candidates/${candidateId}/documents`);
}

export function downloadCandidateDocument(candidateId: string, document: CandidateDocument) {
  return downloadFile(
    `/candidates/${candidateId}/documents/${document.id}/download`,
    document.file_name,
  );
}
