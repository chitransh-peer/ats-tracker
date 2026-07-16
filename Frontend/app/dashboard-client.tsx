"use client";

import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { hiringTrend, scoreDistribution } from "@/lib/mock-data";
import { useAuth } from "@/lib/auth/auth-context";
import {
  useFunnel,
  useSourceEffectiveness,
  useAgingJobs,
  useRecruiterDashboard,
  useAuditLogs,
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
          <p className="text-xs text-muted-foreground">
            Leadership metrics below are illustrative placeholders pending further reporting work.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Open positions" value={48} />
            <StatCard label="Time to fill" value="32d" change="-4d" tone="success" />
            <StatCard label="Offer acceptance" value="87%" change="+3%" tone="success" />
            <StatCard label="Recruiter productivity" value="1.4/wk" />
          </div>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Hiring trend</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={hiringTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="month" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="offers" stroke="#4f46e5" strokeWidth={2} />
                  <Line type="monotone" dataKey="hires" stroke="#10b981" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="executive" className="space-y-6">
          <p className="text-xs text-muted-foreground">
            AI match score distribution below is an illustrative placeholder — real scoring lands in
            a later phase.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Hires YTD" value={188} tone="success" change="+22%" />
            <StatCard label="Hiring velocity" value="6.4/wk" />
            <StatCard label="Cost per hire" value="$3,240" change="-8%" tone="success" />
            <StatCard label="Diversity hires" value="41%" hint="placeholder metric" />
          </div>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">AI match score distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={scoreDistribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="bucket" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]} fill="#4f46e5" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
