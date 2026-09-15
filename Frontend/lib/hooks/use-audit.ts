import { useQuery } from "@tanstack/react-query";
import * as auditApi from "@/lib/api/audit";

export function useAuditLogs(filters: auditApi.AuditLogFilters = {}, enabled = true) {
  return useQuery({
    queryKey: ["audit-logs", filters],
    queryFn: () => auditApi.listAuditLogs(filters),
    enabled,
  });
}

/** Paginated variant for the admin audit panel — returns `{ data, total }`. */
export function useAuditLogsPage(filters: auditApi.AuditLogFilters = {}, enabled = true) {
  return useQuery({
    queryKey: ["audit-logs", "page", filters],
    queryFn: () => auditApi.listAuditLogsPage(filters),
    enabled,
    placeholderData: (previous) => previous,
  });
}

export function useAuditSummaryByUser(enabled = true) {
  return useQuery({
    queryKey: ["audit-summary-by-user"],
    queryFn: () => auditApi.listAuditSummaryByUser(),
    enabled,
  });
}
