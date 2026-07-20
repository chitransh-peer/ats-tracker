import { apiClient } from "./client";
import type { Template } from "./types";

export function listTemplates() {
  return apiClient.get<Template[]>("/templates");
}

export function createTemplate(input: { name: string; type: string; subject: string; body: string }) {
  return apiClient.post<Template>("/templates", input);
}

export function updateTemplate(
  templateId: string,
  input: { name?: string; subject?: string; body?: string },
) {
  return apiClient.patch<Template>(`/templates/${templateId}`, input);
}
