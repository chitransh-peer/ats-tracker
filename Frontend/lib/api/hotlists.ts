import { apiClient, downloadFile } from "./client";
import type {
  Hotlist,
  HotlistInput,
  HotlistListItem,
  HotlistRecipient,
  HotlistSend,
  RecipientImportResult,
} from "./types";

export function listHotlists(status?: string) {
  return apiClient.get<HotlistListItem[]>(`/hotlists${status ? `?status=${status}` : ""}`);
}

export function getHotlist(hotlistId: string) {
  return apiClient.get<Hotlist>(`/hotlists/${hotlistId}`);
}

export function createHotlist(input: HotlistInput & { name: string }) {
  return apiClient.post<Hotlist>("/hotlists", input);
}

export function updateHotlist(hotlistId: string, input: HotlistInput) {
  return apiClient.patch<Hotlist>(`/hotlists/${hotlistId}`, input);
}

export function deleteHotlist(hotlistId: string) {
  return apiClient.delete<void>(`/hotlists/${hotlistId}`);
}

export function setHotlistMembers(hotlistId: string, benchProfileIds: string[]) {
  return apiClient.put<Hotlist>(`/hotlists/${hotlistId}/members`, {
    bench_profile_ids: benchProfileIds,
  });
}

export function suggestedMembers() {
  return apiClient.get<string[]>("/hotlists/suggested-members");
}

export function addHotlistRecipients(
  hotlistId: string,
  recipients: {
    first_name?: string | null;
    last_name?: string | null;
    email: string;
    company?: string | null;
  }[],
) {
  return apiClient.post<Hotlist>(`/hotlists/${hotlistId}/recipients`, { recipients });
}

export function addRecipientsFromParties(
  hotlistId: string,
  input: { client_ids?: string[]; vendor_ids?: string[] },
) {
  return apiClient.post<Hotlist>(`/hotlists/${hotlistId}/recipients/from-parties`, input);
}

export function removeHotlistRecipient(hotlistId: string, recipientId: string) {
  return apiClient.delete<void>(`/hotlists/${hotlistId}/recipients/${recipientId}`);
}

export function setRecipientUnsubscribed(
  hotlistId: string,
  recipientId: string,
  unsubscribed: boolean,
) {
  return apiClient.post<HotlistRecipient>(
    `/hotlists/${hotlistId}/recipients/${recipientId}/unsubscribe?unsubscribed=${unsubscribed}`,
  );
}

export function importRecipients(hotlistId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postForm<RecipientImportResult>(
    `/hotlists/${hotlistId}/recipients/import`,
    formData,
  );
}

export function listHotlistSends(hotlistId: string) {
  return apiClient.get<HotlistSend[]>(`/hotlists/${hotlistId}/sends`);
}

export function sendHotlist(hotlistId: string) {
  return apiClient.post<HotlistSend>(`/hotlists/${hotlistId}/send`);
}

export function exportHotlist(hotlistId: string, name: string) {
  return downloadFile(`/hotlists/${hotlistId}/export`, `${name || "hotlist"}.xlsx`);
}

export function downloadRecipientTemplate() {
  return downloadFile("/hotlists/recipient-template", "hotlist-recipients-template.xlsx");
}
