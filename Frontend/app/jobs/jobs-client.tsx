"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AppShell, StatCard, StatusDot } from "@/components/layout/AppShell";
import { useJobs } from "@/lib/hooks/use-jobs";
import { useAuth } from "@/lib/auth/auth-context";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Search } from "lucide-react";

export function JobsClient() {
  const [status, setStatus] = useState<string>("all");
  const [search, setSearch] = useState("");
  const { user } = useAuth();
  const { data: jobs, isLoading } = useJobs(status !== "all" ? { status } : {});

  const filtered = useMemo(() => {
    if (!jobs) return [];
    const query = search.trim().toLowerCase();
    if (!query) return jobs;
    return jobs.filter(
      (j) => j.title.toLowerCase().includes(query) || j.req_id.toLowerCase().includes(query),
    );
  }, [jobs, search]);

  const active = jobs?.filter((j) => j.status === "Active").length ?? 0;
  const draft = jobs?.filter((j) => j.status === "Draft").length ?? 0;
  const closed = jobs?.filter((j) => j.status === "Closed").length ?? 0;

  function recruiterLabel(recruiterId: string | null) {
    if (!recruiterId) return "Unassigned";
    if (recruiterId === user?.id) return user.full_name;
    return recruiterId.slice(0, 8);
  }

  return (
    <AppShell
      title="Jobs"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Jobs" }]}
      actions={
        <Button size="sm" asChild>
          <Link href="/jobs/new">
            <Plus className="h-4 w-4 mr-1" />
            New Job
          </Link>
        </Button>
      }
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Total requisitions" value={jobs?.length ?? 0} />
        <StatCard label="Active" value={active} tone="success" />
        <StatCard label="Draft" value={draft} />
        <StatCard label="Closed / paused" value={closed} />
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="flex flex-wrap items-center gap-2 p-4 border-b">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search jobs, req IDs…"
                className="pl-9 h-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="h-9 w-[140px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="Active">Active</SelectItem>
                <SelectItem value="Draft">Draft</SelectItem>
                <SelectItem value="On Hold">On Hold</SelectItem>
                <SelectItem value="Closed">Closed</SelectItem>
                <SelectItem value="Cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="text-left p-3 font-medium">Job title</th>
                  <th className="text-left p-3 font-medium">Req ID</th>
                  <th className="text-left p-3 font-medium">Dept · Location</th>
                  <th className="text-left p-3 font-medium">Recruiter</th>
                  <th className="text-left p-3 font-medium">Status</th>
                  <th className="text-left p-3 font-medium">Priority</th>
                  <th className="text-right p-3 font-medium">Apps</th>
                  <th className="text-right p-3 font-medium">Shortlisted</th>
                  <th className="text-right p-3 font-medium">Hires</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {isLoading && (
                  <tr>
                    <td colSpan={9} className="p-6 text-center text-sm text-muted-foreground">
                      Loading jobs…
                    </td>
                  </tr>
                )}
                {!isLoading && filtered.length === 0 && (
                  <tr>
                    <td colSpan={9} className="p-6 text-center text-sm text-muted-foreground">
                      No jobs yet.{" "}
                      <Link href="/jobs/new" className="text-primary hover:underline">
                        Create the first one
                      </Link>
                      .
                    </td>
                  </tr>
                )}
                {filtered.map((j) => (
                  <tr key={j.id} className="hover:bg-muted/30">
                    <td className="p-3">
                      <Link href={`/jobs/${j.id}`} className="font-medium hover:underline">
                        {j.title}
                      </Link>
                      <div className="text-xs text-muted-foreground">
                        {j.workplace} · {j.employment_type}
                      </div>
                    </td>
                    <td className="p-3 text-xs text-muted-foreground font-mono">{j.req_id}</td>
                    <td className="p-3 text-xs">
                      <div>{j.department ?? "—"}</div>
                      <div className="text-muted-foreground">{j.location ?? "—"}</div>
                    </td>
                    <td className="p-3 text-xs">{recruiterLabel(j.recruiter_id)}</td>
                    <td className="p-3">
                      <StatusDot status={j.status} />
                    </td>
                    <td className="p-3">
                      <Badge
                        variant={j.priority === "Urgent" ? "destructive" : "secondary"}
                        className="text-[10px]"
                      >
                        {j.priority}
                      </Badge>
                    </td>
                    <td className="p-3 text-right font-medium">{j.applications_count}</td>
                    <td className="p-3 text-right">{j.shortlisted_count}</td>
                    <td className="p-3 text-right">{j.hires_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </AppShell>
  );
}
