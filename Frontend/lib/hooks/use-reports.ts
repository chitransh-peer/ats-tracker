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

export function useExecutiveDashboard() {
  return useQuery({
    queryKey: ["reports", "executive-dashboard"],
    queryFn: reportsApi.getExecutiveDashboard,
  });
}

export function useHiringTrend() {
  return useQuery({ queryKey: ["reports", "hiring-trend"], queryFn: reportsApi.getHiringTrend });
}

export function useScoreDistribution() {
  return useQuery({
    queryKey: ["reports", "score-distribution"],
    queryFn: reportsApi.getScoreDistribution,
  });
}

export function useOfferMetrics() {
  return useQuery({ queryKey: ["reports", "offer-metrics"], queryFn: reportsApi.getOfferMetrics });
}

export function useTimeToFill() {
  return useQuery({ queryKey: ["reports", "time-to-fill"], queryFn: reportsApi.getTimeToFill });
}

export function useRecruiterPerformance() {
  return useQuery({
    queryKey: ["reports", "recruiter-performance"],
    queryFn: reportsApi.getRecruiterPerformance,
  });
}

export function useAuditLogs(enabled = true) {
  return useQuery({ queryKey: ["audit-logs"], queryFn: reportsApi.getAuditLogs, enabled });
}
