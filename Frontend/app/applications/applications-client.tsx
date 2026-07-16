"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AppShell, StageBadge, StatCard } from "@/components/layout/AppShell";
import { useApplications } from "@/lib/hooks/use-applications";
import { useCandidates } from "@/lib/hooks/use-candidates";
import { useJobs } from "@/lib/hooks/use-jobs";
import { useStages } from "@/lib/hooks/use-pipeline";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Search } from "lucide-react";
import { initialsOf } from "@/lib/utils";

export function ApplicationsClient() {
  const [search, setSearch] = useState("");
  const { data: applications, isLoading } = useApplications();
  const { data: candidates } = useCandidates();
  const { data: jobs } = useJobs();
  const { data: stageTemplate } = useStages();

  const candidateById = useMemo(
    () => new Map((candidates ?? []).map((c) => [c.id, c])),
    [candidates],
  );
  const jobById = useMemo(() => new Map((jobs ?? []).map((j) => [j.id, j])), [jobs]);
  const stageById = useMemo(
    () => new Map((stageTemplate?.stages ?? []).map((s) => [s.id, s.name])),
    [stageTemplate],
  );

  const rows = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (applications ?? [])
      .map((a) => ({
        application: a,
        candidate: candidateById.get(a.candidate_id),
        job: jobById.get(a.job_id),
      }))
      .filter(({ candidate, job }) => {
        if (!query) return true;
        return (
          candidate?.full_name.toLowerCase().includes(query) ||
          job?.title.toLowerCase().includes(query)
        );
      });
  }, [applications, search, candidateById, jobById]);

  const newThisWeek = (applications ?? []).filter((a) => {
    const days = (Date.now() - new Date(a.applied_at).getTime()) / (1000 * 60 * 60 * 24);
    return days <= 7;
  }).length;

  return (
    <AppShell
      title="Applications"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Applications" }]}
    >
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <StatCard label="Total applications" value={applications?.length ?? 0} />
        <StatCard label="New this week" value={newThisWeek} tone="success" />
        <StatCard
          label="Active"
          value={applications?.filter((a) => a.status === "Active").length ?? 0}
        />
      </div>
      <Card>
        <CardContent className="p-0">
          <div className="p-4 border-b flex gap-2">
            <div className="relative flex-1">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by candidate or job…"
                className="pl-9 h-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-xs uppercase text-muted-foreground tracking-wider">
              <tr>
                <th className="p-3 text-left">Candidate</th>
                <th className="p-3 text-left">Job</th>
                <th className="p-3 text-left">Stage</th>
                <th className="p-3 text-left">Status</th>
                <th className="p-3 text-left">Applied</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {isLoading && (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-sm text-muted-foreground">
                    Loading…
                  </td>
                </tr>
              )}
              {!isLoading && rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-sm text-muted-foreground">
                    No applications found.
                  </td>
                </tr>
              )}
              {rows.map(({ application, candidate, job }) => (
                <tr key={application.id} className="hover:bg-muted/30">
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <Avatar className="h-7 w-7">
                        <AvatarFallback className="text-[10px]">
                          {candidate ? initialsOf(candidate.full_name) : "?"}
                        </AvatarFallback>
                      </Avatar>
                      {candidate ? (
                        <Link
                          href={`/candidates/${candidate.id}`}
                          className="hover:underline font-medium"
                        >
                          {candidate.full_name}
                        </Link>
                      ) : (
                        <span className="text-muted-foreground">Unknown</span>
                      )}
                    </div>
                  </td>
                  <td className="p-3">
                    {job ? (
                      <Link href={`/jobs/${job.id}`} className="hover:underline">
                        {job.title}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="p-3">
                    <StageBadge
                      stage={
                        application.current_stage_id
                          ? (stageById.get(application.current_stage_id) ?? "—")
                          : "—"
                      }
                    />
                  </td>
                  <td className="p-3">
                    <Badge variant="secondary" className="text-[10px]">
                      {application.status}
                    </Badge>
                  </td>
                  <td className="p-3 text-xs text-muted-foreground">
                    {new Date(application.applied_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </AppShell>
  );
}
