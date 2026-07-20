import { apiClient } from "./client";
import type { Organization } from "./types";

export function getOrganizationSettings() {
  return apiClient.get<Organization>("/settings/organization");
}

export function updateOrganizationSettings(input: {
  default_locale?: string;
  careers_page_enabled?: boolean;
}) {
  return apiClient.patch<Organization>("/settings/organization", input);
}
