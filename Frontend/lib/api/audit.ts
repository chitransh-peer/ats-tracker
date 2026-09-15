import { apiClient } from "./client";
import type { AuditLogEntry, AuditUserSummary } from "./types";

export interface AuditLogFilters {
  action?: string;
  resource_type?: string;
  actor_user_id?: string;
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

export function listAuditLogs(filters: AuditLogFilters = {}) {
  return apiClient.get<AuditLogEntry[]>(`/audit-logs${buildQuery(filters)}`);
}

export function listAuditLogsPage(filters: AuditLogFilters = {}) {
  return apiClient.getPage<AuditLogEntry>(
    `/audit-logs${buildQuery({
      ...filters,
      limit: filters.limit?.toString(),
      offset: filters.offset?.toString(),
    })}`,
  );
}

export function listAuditSummaryByUser() {
  return apiClient.get<AuditUserSummary[]>("/audit-logs/by-user");
}
