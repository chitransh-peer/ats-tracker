"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  useAgingJobs,
  useExecutiveDashboard,
  useFunnel,
  useHiringTrend,
  useOfferMetrics,
  useRecruiterPerformance,
  useScoreDistribution,
  useSourceEffectiveness,
  useTimeToFill,
} from "@/lib/hooks/use-reports";
import { downloadCsv } from "@/lib/csv";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const colors = ["#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#a855f7"];

/** Charts render an axis frame even with no rows, which reads as "zero" rather than "no data yet". */
function ChartFrame({
  isLoading,
  isEmpty,
  emptyLabel,
  children,
}: {
  isLoading: boolean;
  isEmpty: boolean;
  emptyLabel: string;
  children: React.ReactNode;
}) {
  if (isLoading) return <Skeleton className="h-[340px] w-full" />;
  if (isEmpty) {
    return (
      <div className="grid h-[340px] place-items-center text-center">
        <div>
          <p className="text-sm text-muted-foreground">{emptyLabel}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            This chart fills in as data flows through the pipeline.
          </p>
        </div>
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={340}>
      {children as never}
    </ResponsiveContainer>
  );
}

export function ReportsClient() {
  const [tab, setTab] = useState("funnel");

  const funnel = useFunnel();
  const trend = useHiringTrend();
  const source = useSourceEffectiveness();
  const scores = useScoreDistribution();
  const recruiters = useRecruiterPerformance();
  const aging = useAgingJobs();
  const timeToFill = useTimeToFill();
  const offers = useOfferMetrics();
  const executive = useExecutiveDashboard();

  const agingOver60 = (aging.data ?? []).filter((j) => (j.age_days ?? 0) >= 60).length;
  const avgDays = timeToFill.data?.average_days;
  const acceptance = offers.data?.acceptance_rate;

  function handleExport() {
    switch (tab) {
      case "funnel":
        return downloadCsv("funnel.csv", ["stage", "value"], funnel.data ?? []);
      case "trend":
        return downloadCsv("hiring-trend.csv", ["month", "offers", "hires"], trend.data ?? []);
      case "source":
        return downloadCsv("source-effectiveness.csv", ["source", "value"], source.data ?? []);
      case "ai":
        return downloadCsv("score-distribution.csv", ["bucket", "count"], scores.data ?? []);
      case "recruiter":
        return downloadCsv(
          "recruiter-performance.csv",
          ["recruiter_name", "open_jobs", "applications", "hires"],
          recruiters.data ?? [],
        );
      case "aging":
        return downloadCsv(
          "aging-jobs.csv",
          ["title", "status", "posted_at", "age_days"],
          aging.data ?? [],
        );
    }
  }

  return (
    <AppShell
      title="Reports & Analytics"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Reports" }]}
      actions={
        <Button variant="outline" size="sm" onClick={handleExport}>
          Export CSV
        </Button>
      }
    >
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <StatCard label="Open positions" value={executive.data?.total_open_jobs ?? 0} />
        <StatCard
          label="Avg. time to fill"
          value={avgDays != null ? `${Math.round(avgDays)}d` : "—"}
          hint={
            timeToFill.data?.filled_jobs_count
              ? `across ${timeToFill.data.filled_jobs_count} hire${timeToFill.data.filled_jobs_count === 1 ? "" : "s"}`
              : "no hires yet"
          }
        />
        <StatCard
          label="Offer acceptance"
          value={acceptance != null ? `${acceptance}%` : "—"}
          tone={acceptance != null && acceptance >= 70 ? "success" : "default"}
          hint={
            offers.data
              ? `${offers.data.accepted} accepted · ${offers.data.declined} declined`
              : undefined
          }
        />
        <StatCard label="Total hires" value={executive.data?.total_hires ?? 0} tone="success" />
        <StatCard
          label="Aging jobs (60d+)"
          value={agingOver60}
          tone={agingOver60 > 0 ? "warning" : "default"}
        />
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="funnel">Funnel</TabsTrigger>
          <TabsTrigger value="trend">Trend</TabsTrigger>
          <TabsTrigger value="source">Source</TabsTrigger>
          <TabsTrigger value="ai">AI scores</TabsTrigger>
          <TabsTrigger value="recruiter">Recruiter</TabsTrigger>
          <TabsTrigger value="aging">Aging jobs</TabsTrigger>
        </TabsList>

        <TabsContent value="funnel" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Hiring funnel</CardTitle>
              <p className="text-xs text-muted-foreground">
                Applications that have reached each stage, including those since moved on.
              </p>
            </CardHeader>
            <CardContent>
              <ChartFrame
                isLoading={funnel.isLoading}
                isEmpty={(funnel.data ?? []).length === 0}
                emptyLabel="No applications in the pipeline yet."
              >
                <BarChart data={funnel.data ?? []} layout="vertical" margin={{ left: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} className="text-xs" />
                  <YAxis type="category" dataKey="stage" className="text-xs" width={90} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} fill="#4f46e5" />
                </BarChart>
              </ChartFrame>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trend" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Hiring trend — offers vs hires</CardTitle>
              <p className="text-xs text-muted-foreground">Last 12 months.</p>
            </CardHeader>
            <CardContent>
              <ChartFrame
                isLoading={trend.isLoading}
                isEmpty={(trend.data ?? []).every((p) => p.offers === 0 && p.hires === 0)}
                emptyLabel="No offers or hires recorded yet."
              >
                <LineChart data={trend.data ?? []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" className="text-xs" />
                  <YAxis allowDecimals={false} className="text-xs" />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="offers" stroke="#4f46e5" strokeWidth={2} />
                  <Line type="monotone" dataKey="hires" stroke="#10b981" strokeWidth={2} />
                </LineChart>
              </ChartFrame>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="source" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Source effectiveness</CardTitle>
              <p className="text-xs text-muted-foreground">
                Applications by the channel they came in through.
              </p>
            </CardHeader>
            <CardContent>
              <ChartFrame
                isLoading={source.isLoading}
                isEmpty={(source.data ?? []).length === 0}
                emptyLabel="No applications yet."
              >
                <PieChart>
                  <Pie
                    data={source.data ?? []}
                    dataKey="value"
                    nameKey="source"
                    innerRadius={80}
                    outerRadius={130}
                  >
                    {(source.data ?? []).map((_, i) => (
                      <Cell key={i} fill={colors[i % colors.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ChartFrame>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ai" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">AI match score distribution</CardTitle>
              <p className="text-xs text-muted-foreground">
                Latest completed evaluation per application.
              </p>
            </CardHeader>
            <CardContent>
              <ChartFrame
                isLoading={scores.isLoading}
                isEmpty={(scores.data ?? []).every((b) => b.count === 0)}
                emptyLabel="No AI evaluations have completed yet."
              >
                <BarChart data={scores.data ?? []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="bucket" className="text-xs" />
                  <YAxis allowDecimals={false} className="text-xs" />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]} fill="#a855f7" />
                </BarChart>
              </ChartFrame>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recruiter" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recruiter productivity</CardTitle>
              <p className="text-xs text-muted-foreground">
                Counted across every job the recruiter owns.
              </p>
            </CardHeader>
            <CardContent className="p-0">
              {recruiters.isLoading ? (
                <div className="space-y-2 p-6">
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-5 w-full" />
                </div>
              ) : (recruiters.data ?? []).length === 0 ? (
                <p className="p-6 text-center text-sm text-muted-foreground">
                  No recruiters own an active job yet.
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="p-3 text-left">Recruiter</th>
                      <th className="p-3 text-right">Open jobs</th>
                      <th className="p-3 text-right">Applications</th>
                      <th className="p-3 text-right">Hires</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {(recruiters.data ?? []).map((r) => (
                      <tr key={r.recruiter_id} className="hover:bg-muted/30">
                        <td className="p-3">{r.recruiter_name}</td>
                        <td className="p-3 text-right">{r.open_jobs}</td>
                        <td className="p-3 text-right">{r.applications}</td>
                        <td className="p-3 text-right">{r.hires}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="aging" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Aging jobs</CardTitle>
              <p className="text-xs text-muted-foreground">
                Active requisitions, oldest posting first.
              </p>
            </CardHeader>
            <CardContent className="p-0">
              {aging.isLoading ? (
                <div className="space-y-2 p-6">
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-5 w-full" />
                </div>
              ) : (aging.data ?? []).length === 0 ? (
                <p className="p-6 text-center text-sm text-muted-foreground">
                  No active jobs right now.
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="p-3 text-left">Job</th>
                      <th className="p-3 text-left">Status</th>
                      <th className="p-3 text-right">Age</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {(aging.data ?? []).map((j) => (
                      <tr key={j.job_id} className="hover:bg-muted/30">
                        <td className="p-3">
                          <Link href={`/jobs/${j.job_id}`} className="hover:underline">
                            {j.title}
                          </Link>
                        </td>
                        <td className="p-3">
                          <Badge variant="secondary" className="text-[10px]">
                            {j.status}
                          </Badge>
                        </td>
                        <td className="p-3 text-right">
                          {j.age_days != null ? (
                            <span className={j.age_days >= 60 ? "text-destructive" : undefined}>
                              {j.age_days}d
                            </span>
                          ) : (
                            "not posted"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
