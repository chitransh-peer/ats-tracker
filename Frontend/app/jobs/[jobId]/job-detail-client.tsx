"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell, StageBadge, StatCard, StatusDot } from "@/components/layout/AppShell";
import { useJob, useJobAction } from "@/lib/hooks/use-jobs";
import { useApplications } from "@/lib/hooks/use-applications";
import { useCandidates } from "@/lib/hooks/use-candidates";
import { useStages } from "@/lib/hooks/use-pipeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { initialsOf } from "@/lib/utils";
import { MapPin, Briefcase, DollarSign, Sparkles } from "lucide-react";

export function JobDetailClient() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;

  const { data: job, isLoading } = useJob(jobId);
  const { data: applications } = useApplications({ job_id: jobId });
  const { data: candidates } = useCandidates();
  const { data: stageTemplate } = useStages();
  const actions = useJobAction(jobId);

  if (isLoading) {
    return (
      <AppShell title="Job">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </AppShell>
    );
  }

  if (!job) {
    return (
      <AppShell title="Job not found">
        <div className="text-sm text-muted-foreground">
          This job doesn&apos;t exist or you don&apos;t have access to it.{" "}
          <Link href="/jobs" className="text-primary hover:underline">
            Back to jobs
          </Link>
        </div>
      </AppShell>
    );
  }

  const candidateById = new Map((candidates ?? []).map((c) => [c.id, c]));
  const stageById = new Map((stageTemplate?.stages ?? []).map((s) => [s.id, s.name]));
  const rows = (applications ?? []).map((app) => ({
    application: app,
    candidate: candidateById.get(app.candidate_id),
    stageName: app.current_stage_id ? (stageById.get(app.current_stage_id) ?? "—") : "—",
  }));

  const canTransition = job.status !== "Closed" && job.status !== "Cancelled";

  return (
    <AppShell
      title={job.title}
      breadcrumbs={[
        { label: "Home", to: "/" },
        { label: "Jobs", to: "/jobs" },
        { label: job.title },
      ]}
      actions={
        <>
          {job.status === "Draft" && (
            <Button
              size="sm"
              onClick={() => actions.publish.mutate()}
              disabled={actions.publish.isPending}
            >
              Publish
            </Button>
          )}
          {job.status === "Active" && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => actions.hold.mutate()}
                disabled={actions.hold.isPending}
              >
                Put on hold
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => actions.close.mutate()}
                disabled={actions.close.isPending}
              >
                Close
              </Button>
            </>
          )}
          {job.status === "On Hold" && (
            <Button
              size="sm"
              onClick={() => actions.publish.mutate()}
              disabled={actions.publish.isPending}
            >
              Resume
            </Button>
          )}
          {canTransition && job.status !== "Draft" && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => actions.cancel.mutate()}
              disabled={actions.cancel.isPending}
            >
              Cancel
            </Button>
          )}
        </>
      }
    >
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-6">
        <div className="space-y-6">
          <Card>
            <CardContent className="p-5">
              <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                <span className="font-mono">{job.req_id}</span>
                <span>·</span>
                <StatusDot status={job.status} />
                <span>·</span>
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {job.location ?? "—"} · {job.workplace}
                </span>
                <span>·</span>
                <span className="inline-flex items-center gap-1">
                  <Briefcase className="h-3 w-3" />
                  {job.employment_type}
                </span>
                {(job.pay_min || job.pay_max) && (
                  <>
                    <span>·</span>
                    <span className="inline-flex items-center gap-1">
                      <DollarSign className="h-3 w-3" />
                      {job.pay_min ? `$${job.pay_min / 1000}k` : "—"} –{" "}
                      {job.pay_max ? `$${job.pay_max / 1000}k` : "—"}
                    </span>
                  </>
                )}
              </div>
              {job.summary && <p className="mt-4 text-sm">{job.summary}</p>}
            </CardContent>
          </Card>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatCard label="Applications" value={job.applications_count} />
            <StatCard label="Shortlisted" value={job.shortlisted_count} />
            <StatCard label="Interviews" value={job.interviews_count} />
            <StatCard label="Offers" value={job.offers_count} tone="warning" />
            <StatCard label="Hires" value={job.hires_count} tone="success" />
          </div>

          <Tabs defaultValue="pipeline">
            <TabsList>
              <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
              <TabsTrigger value="description">Description</TabsTrigger>
            </TabsList>
            <TabsContent value="pipeline" className="mt-4">
              <Card>
                <CardHeader className="pb-2 flex-row items-center justify-between">
                  <CardTitle className="text-base">Candidates on this job</CardTitle>
                  <Button size="sm" variant="outline" asChild>
                    <Link href="/pipeline">Open pipeline</Link>
                  </Button>
                </CardHeader>
                <CardContent className="p-0">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="p-3 text-left font-medium">Candidate</th>
                        <th className="p-3 text-left font-medium">Stage</th>
                        <th className="p-3 text-left font-medium">Status</th>
                        <th className="p-3 text-left font-medium">Applied</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {rows.length === 0 && (
                        <tr>
                          <td colSpan={4} className="p-6 text-center text-sm text-muted-foreground">
                            No candidates have applied yet.
                          </td>
                        </tr>
                      )}
                      {rows.map(({ application, candidate, stageName }) => (
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
                                  className="font-medium hover:underline"
                                >
                                  {candidate.full_name}
                                </Link>
                              ) : (
                                <span className="text-muted-foreground">Unknown candidate</span>
                              )}
                            </div>
                          </td>
                          <td className="p-3">
                            <StageBadge stage={stageName} />
                          </td>
                          <td className="p-3 text-xs">{application.status}</td>
                          <td className="p-3 text-xs text-muted-foreground">
                            {new Date(application.applied_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="description" className="mt-4 space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">About the role</CardTitle>
                </CardHeader>
                <CardContent className="text-sm leading-relaxed text-muted-foreground">
                  {job.description || "No description provided."}
                </CardContent>
              </Card>
              {job.responsibilities.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Responsibilities</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc pl-5 text-sm space-y-1">
                      {job.responsibilities.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
              <div className="grid md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Required</CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-wrap gap-1.5">
                    {job.required_skills.length === 0 && (
                      <span className="text-sm text-muted-foreground">None specified</span>
                    )}
                    {job.required_skills.map((s) => (
                      <Badge key={s} variant="secondary">
                        {s}
                      </Badge>
                    ))}
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Nice to have</CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-wrap gap-1.5">
                    {job.nice_to_have.length === 0 && (
                      <span className="text-sm text-muted-foreground">None specified</span>
                    )}
                    {job.nice_to_have.map((s) => (
                      <Badge key={s} variant="outline">
                        {s}
                      </Badge>
                    ))}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>

        <aside className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-primary" />
                AI insights
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              AI-assisted resume scoring and matching is coming in a later phase.
            </CardContent>
          </Card>
        </aside>
      </div>
    </AppShell>
  );
}
