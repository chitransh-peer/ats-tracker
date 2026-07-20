import { useQuery } from "@tanstack/react-query";
import * as auditApi from "@/lib/api/audit";

export function useAuditLogs(filters: auditApi.AuditLogFilters = {}) {
  return useQuery({
    queryKey: ["audit-logs", filters],
    queryFn: () => auditApi.listAuditLogs(filters),
  });
}
