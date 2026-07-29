import { useQuery } from "@tanstack/react-query";
import * as auditApi from "@/lib/api/audit";

export function useAuditLogs(filters: auditApi.AuditLogFilters = {}, enabled = true) {
  return useQuery({
    queryKey: ["audit-logs", filters],
    queryFn: () => auditApi.listAuditLogs(filters),
    enabled,
  });
}

export function useAuditSummaryByUser(enabled = true) {
  return useQuery({
    queryKey: ["audit-summary-by-user"],
    queryFn: () => auditApi.listAuditSummaryByUser(),
    enabled,
  });
}
