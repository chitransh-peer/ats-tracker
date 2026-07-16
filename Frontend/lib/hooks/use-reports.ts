import { useQuery } from "@tanstack/react-query";
import * as reportsApi from "@/lib/api/reports";

export function useFunnel() {
  return useQuery({ queryKey: ["reports", "funnel"], queryFn: reportsApi.getFunnel });
}

export function useSourceEffectiveness() {
  return useQuery({
    queryKey: ["reports", "source-effectiveness"],
    queryFn: reportsApi.getSourceEffectiveness,
  });
}

export function useAgingJobs() {
  return useQuery({ queryKey: ["reports", "aging-jobs"], queryFn: reportsApi.getAgingJobs });
}

export function useRecruiterDashboard() {
  return useQuery({
    queryKey: ["reports", "recruiter-dashboard"],
    queryFn: reportsApi.getRecruiterDashboard,
  });
}

export function useAuditLogs(enabled = true) {
  return useQuery({ queryKey: ["audit-logs"], queryFn: reportsApi.getAuditLogs, enabled });
}
