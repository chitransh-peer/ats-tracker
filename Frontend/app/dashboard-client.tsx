"use client";

import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useAuth } from "@/lib/auth/auth-context";
import {
  useFunnel,
  useSourceEffectiveness,
  useAgingJobs,
  useRecruiterDashboard,
  useAuditLogs,
  useHiringTrend,
  useScoreDistribution,
  useOfferMetrics,
  useTimeToFill,
  useExecutiveDashboard,
  useRecruiterPerformance,
} from "@/lib/hooks/use-reports";
import { useCandidates } from "@/lib/hooks/use-candidates";
import { useInterviews } from "@/lib/hooks/use-interviews";
import { useApplications } from "@/lib/hooks/use-applications";
import { useStages } from "@/lib/hooks/use-pipeline";
import { initialsOf, relativeTime } from "@/lib/utils";
import { ArrowRight, CalendarClock, Clock } from "lucide-react";
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

const chartColors = ["#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#a855f7"];

function humanizeAction(action: string): string {
  return action.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function DashboardClient() {
  const { user } = useAuth();
  const { data: funnel } = useFunnel();
  const { data: sourceEffectiveness } = useSourceEffectiveness();
  const { data: agingJobs } = useAgingJobs();
  const { data: recruiterStats } = useRecruiterDashboard();
  const { data: hiringTrend } = useHiringTrend();
  const { data: scoreDistribution } = useScoreDistribution();
  const { data: offerMetrics } = useOfferMetrics();
  const { data: timeToFill } = useTimeToFill();
  const { data: executive } = useExecutiveDashboard();
  const { data: recruiterPerformance } = useRecruiterPerformance();
  const { data: candidates } = useCandidates();
  const { data: interviews } = useInterviews({ status: "Scheduled" });
  const { data: applications } = useApplications();
  const { data: stageTemplate } = useStages();
  const canViewAuditLogs = ["super_admin", "admin", "executive"].some((r) =>
    user?.roles.includes(r),
  );
  const { data: auditLogs } = useAuditLogs(canViewAuditLogs);

  const stageById = new Map((stageTemplate?.stages ?? []).map((s) => [s.id, s.name]));
  const applicationById = new Map((applications ?? []).map((a) => [a.id, a]));
  const candidateById = new Map((candidates ?? []).map((c) => [c.id, c]));
  const recentCandidates = [...(candidates ?? [])]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 6);
  const upcomingInterviews = (interviews ?? []).slice(0, 5);
  const recentActivity = (auditLogs ?? []).slice(0, 6);

  return (
    <AppShell
      title={`Good morning, ${user?.full_name.split(" ")[0] ?? ""}`}
      breadcrumbs={[{ label: "Home" }, { label: "Dashboard" }]}
      actions={
        <Button size="sm" asChild>
          <Link href="/jobs/new">New requisition</Link>
        </Button>
      }
    >
      <Tabs defaultValue="recruiter" className="space-y-6">
        <TabsList>
          <TabsTrigger value="recruiter">Recruiter</TabsTrigger>
          <TabsTrigger value="leadership">Leadership</TabsTrigger>
          <TabsTrigger value="executive">Executive</TabsTrigger>
        </TabsList>

        <TabsContent value="recruiter" className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="My open jobs" value={recruiterStats?.open_jobs ?? 0} />
            <StatCard
              label="Applications this week"
              value={recruiterStats?.applications_this_week ?? 0}
              tone="success"
            />
            <StatCard
              label="Interviews scheduled"
              value={recruiterStats?.interviews_scheduled ?? 0}
            />
            <StatCard
              label="Offers pending"
              value={recruiterStats?.offers_pending ?? 0}
              tone="warning"
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <Card className="xl:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div>
                  <CardTitle className="text-base">Hiring funnel</CardTitle>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Applications reaching each stage, org-wide
                  </p>
                </div>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={funnel ?? []} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                    <XAxis type="number" tickLine={false} axisLine={false} className="text-xs" />
                    <YAxis
                      type="category"
                      dataKey="stage"
                      tickLine={false}
                      axisLine={false}
                      width={90}
                      className="text-xs"
                    />
                    <Tooltip cursor={{ fill: "rgba(0,0,0,0.03)" }} />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]} fill="#4f46e5" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Source performance</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={sourceEffectiveness ?? []}
                      dataKey="value"
                      nameKey="source"
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                    >
                      {(sourceEffectiveness ?? []).map((_, i) => (
                        <Cell key={i} fill={chartColors[i % chartColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <Card className="xl:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base">Recently added candidates</CardTitle>
                <Button variant="ghost" size="sm" className="text-xs" asChild>
                  <Link href="/candidates">
                    View all <ArrowRight className="ml-1 h-3 w-3" />
                  </Link>
                </Button>
              </CardHeader>
              <CardContent className="p-0">
                {recentCandidates.length === 0 && (
                  <div className="p-6 text-sm text-muted-foreground text-center">
                    No candidates yet.
                  </div>
                )}
                <ul className="divide-y">
                  {recentCandidates.map((c) => (
                    <li key={c.id} className="flex items-center gap-3 px-6 py-3">
                      <Avatar className="h-9 w-9">
                        <AvatarFallback className="text-xs">
                          {initialsOf(c.full_name)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="min-w-0 flex-1">
                        <Link
                          href={`/candidates/${c.id}`}
                          className="text-sm font-medium hover:underline"
                        >
                          {c.full_name}
                        </Link>
                        <div className="text-xs text-muted-foreground truncate">
                          {c.current_title ?? "—"} · {c.current_company ?? "—"} ·{" "}
                          {c.location ?? "—"}
                        </div>
                      </div>
                      <Badge variant="secondary" className="text-[10px]">
                        {c.status}
                      </Badge>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-base">Upcoming interviews</CardTitle>
                <Button variant="ghost" size="sm" className="text-xs" asChild>
                  <Link href="/interviews">All</Link>
                </Button>
              </CardHeader>
              <CardContent className="space-y-3">
                {upcomingInterviews.length === 0 && (
                  <div className="text-sm text-muted-foreground text-center py-4">
                    No interviews scheduled.
                  </div>
                )}
                {upcomingInterviews.map((iv) => {
                  const application = applicationById.get(iv.application_id);
                  const candidate = application
                    ? candidateById.get(application.candidate_id)
                    : undefined;
                  return (
                    <div key={iv.id} className="flex items-start gap-3 rounded-md border p-3">
                      <div className="grid place-items-center h-9 w-9 rounded-md bg-primary/10 text-primary">
                        <CalendarClock className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium">{iv.round_name}</div>
                        <div className="text-xs text-muted-foreground">
                          {candidate?.full_name ?? "Unknown"} · {iv.mode}
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-1">
                          <Clock className="inline h-3 w-3 mr-1" />
                          {new Date(iv.scheduled_at).toLocaleString()}
                        </div>
                      </div>
                      <Badge variant="secondary" className="text-[10px]">
                        {iv.status}
                      </Badge>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <Card className="xl:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Aging jobs — need attention</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {(agingJobs ?? []).length === 0 && (
                    <div className="text-sm text-muted-foreground text-center py-4">
                      No active jobs.
                    </div>
                  )}
                  {(agingJobs ?? []).slice(0, 4).map((j) => (
                    <div key={j.job_id} className="flex items-center gap-3">
                      <div className="min-w-0 flex-1">
                        <Link
                          href={`/jobs/${j.job_id}`}
                          className="text-sm font-medium hover:underline truncate block"
                        >
                          {j.title}
                        </Link>
                        <div className="text-xs text-muted-foreground">
                          Posted {j.age_days ?? 0} days ago
                        </div>
                      </div>
                      <div className="w-40 hidden md:block">
                        <Progress value={Math.min(100, (j.age_days ?? 0) * 3)} className="h-1.5" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Recent activity</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {recentActivity.length === 0 && (
                  <div className="text-sm text-muted-foreground text-center py-4">
                    No activity yet.
                  </div>
                )}
                {recentActivity.map((a) => (
                  <div key={a.id} className="flex items-start gap-2 text-sm">
                    <div className="h-1.5 w-1.5 rounded-full bg-primary mt-2" />
                    <div className="flex-1">
                      <div>
                        <span className="font-medium">{humanizeAction(a.action)}</span>{" "}
                        <span className="text-muted-foreground">{a.resource_type}</span>
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        {relativeTime(a.created_at)}
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="leadership" className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Open positions" value={executive?.total_open_jobs ?? 0} />
            <StatCard
              label="Avg. time to fill"
              value={
                timeToFill?.average_days != null ? `${Math.round(timeToFill.average_days)}d` : "—"
              }
              hint={
                timeToFill?.filled_jobs_count
                  ? `across ${timeToFill.filled_jobs_count} hire${timeToFill.filled_jobs_count === 1 ? "" : "s"}`
                  : "no hires yet"
              }
            />
            <StatCard
              label="Offer acceptance"
              value={
                offerMetrics?.acceptance_rate != null ? `${offerMetrics.acceptance_rate}%` : "—"
              }
              tone={
                offerMetrics?.acceptance_rate != null && offerMetrics.acceptance_rate >= 70
                  ? "success"
                  : "default"
              }
              hint={offerMetrics ? `${offerMetrics.pending} awaiting approval` : undefined}
            />
            <StatCard
              label="Active recruiters"
              value={(recruiterPerformance ?? []).length}
              hint="owning at least one open job"
            />
          </div>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Hiring trend</CardTitle>
              <p className="text-xs text-muted-foreground">
                Offers created vs. hires made, last 12 months.
              </p>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={hiringTrend ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="month" className="text-xs" />
                  <YAxis allowDecimals={false} className="text-xs" />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="offers" stroke="#4f46e5" strokeWidth={2} />
                  <Line type="monotone" dataKey="hires" stroke="#10b981" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-base">Recruiter productivity</CardTitle>
              <Button variant="ghost" size="sm" className="text-xs" asChild>
                <Link href="/reports">
                  Full report <ArrowRight className="ml-1 h-3 w-3" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {(recruiterPerformance ?? []).length === 0 ? (
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
                    {(recruiterPerformance ?? []).map((r) => (
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

        <TabsContent value="executive" className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Total hires" value={executive?.total_hires ?? 0} tone="success" />
            <StatCard label="Open requisitions" value={executive?.total_open_jobs ?? 0} />
            <StatCard label="Candidates in database" value={executive?.total_candidates ?? 0} />
            <StatCard
              label="Offers out"
              value={offerMetrics?.sent ?? 0}
              hint={offerMetrics ? `${offerMetrics.declined} declined` : undefined}
              tone="warning"
            />
          </div>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Org-wide funnel</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={executive?.funnel ?? []} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} className="text-xs" />
                    <YAxis
                      type="category"
                      dataKey="stage"
                      width={90}
                      tickLine={false}
                      axisLine={false}
                      className="text-xs"
                    />
                    <Tooltip />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]} fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">AI match score distribution</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Latest completed evaluation per application.
                </p>
              </CardHeader>
              <CardContent>
                {(scoreDistribution ?? []).every((b) => b.count === 0) ? (
                  <p className="grid h-[240px] place-items-center text-sm text-muted-foreground">
                    No AI evaluations have completed yet.
                  </p>
                ) : (
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={scoreDistribution ?? []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="bucket" className="text-xs" />
                      <YAxis allowDecimals={false} className="text-xs" />
                      <Tooltip />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]} fill="#4f46e5" />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
