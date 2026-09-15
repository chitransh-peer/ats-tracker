import { apiClient } from "./client";
import type { Template } from "./types";

export interface TemplateInput {
  name: string;
  type: string;
  subject: string;
  body: string;
}

export function listTemplates() {
  return apiClient.get<Template[]>("/templates");
}

export function createTemplate(input: TemplateInput) {
  return apiClient.post<Template>("/templates", input);
}

export function updateTemplate(templateId: string, input: Partial<TemplateInput>) {
  return apiClient.patch<Template>(`/templates/${templateId}`, input);
}

export function deleteTemplate(templateId: string) {
  return apiClient.delete<void>(`/templates/${templateId}`);
}
