"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell, StageBadge } from "@/components/layout/AppShell";
import { useCandidate, useCandidateNotes, useAddCandidateNote } from "@/lib/hooks/use-candidates";
import { useApplications } from "@/lib/hooks/use-applications";
import { useInterviews } from "@/lib/hooks/use-interviews";
import { useJobs } from "@/lib/hooks/use-jobs";
import { useStages } from "@/lib/hooks/use-pipeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Textarea } from "@/components/ui/textarea";
import { Mail, Phone, MapPin, Linkedin, Clock, Sparkles } from "lucide-react";
import { initialsOf, relativeTime } from "@/lib/utils";

export function CandidateDetailClient() {
  const params = useParams<{ candidateId: string }>();
  const candidateId = params.candidateId;

  const { data: candidate, isLoading } = useCandidate(candidateId);
  const { data: notes } = useCandidateNotes(candidateId);
  const { data: applications } = useApplications({ candidate_id: candidateId });
  const { data: interviews } = useInterviews();
  const { data: jobs } = useJobs();
  const { data: stageTemplate } = useStages();
  const addNote = useAddCandidateNote(candidateId);
  const [noteBody, setNoteBody] = useState("");

  if (isLoading) {
    return (
      <AppShell title="Candidate">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </AppShell>
    );
  }

  if (!candidate) {
    return (
      <AppShell title="Candidate not found">
        <div className="text-sm text-muted-foreground">
          This candidate doesn&apos;t exist or you don&apos;t have access.{" "}
          <Link href="/candidates" className="text-primary hover:underline">
            Back to candidates
          </Link>
        </div>
      </AppShell>
    );
  }

  const jobById = new Map((jobs ?? []).map((j) => [j.id, j]));
  const stageById = new Map((stageTemplate?.stages ?? []).map((s) => [s.id, s.name]));
  const applicationIds = new Set((applications ?? []).map((a) => a.id));
  const candidateInterviews = (interviews ?? []).filter((iv) =>
    applicationIds.has(iv.application_id),
  );

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!noteBody.trim()) return;
    await addNote.mutateAsync(noteBody.trim());
    setNoteBody("");
  }

  return (
    <AppShell
      title={candidate.full_name}
      breadcrumbs={[
        { label: "Home", to: "/" },
        { label: "Candidates", to: "/candidates" },
        { label: candidate.full_name },
      ]}
    >
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-6">
        <div className="space-y-6">
          <Card>
            <CardContent className="p-5">
              <div className="flex items-start gap-4">
                <Avatar className="h-16 w-16">
                  <AvatarFallback className="text-lg">
                    {initialsOf(candidate.full_name)}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-semibold">{candidate.full_name}</h2>
                    <Badge variant="secondary" className="text-[10px]">
                      {candidate.status}
                    </Badge>
                    {candidate.tags.map((t) => (
                      <Badge key={t} variant="outline" className="text-[10px]">
                        {t}
                      </Badge>
                    ))}
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    {candidate.current_title ?? "—"} · {candidate.current_company ?? "—"}
                    {candidate.total_experience_years
                      ? ` · ${candidate.total_experience_years} yrs`
                      : ""}
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {candidate.email}
                    </span>
                    {candidate.phone && (
                      <span className="flex items-center gap-1">
                        <Phone className="h-3 w-3" />
                        {candidate.phone}
                      </span>
                    )}
                    {candidate.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {candidate.location}
                      </span>
                    )}
                    {candidate.linkedin_url && (
                      <a
                        href={candidate.linkedin_url}
                        className="flex items-center gap-1 hover:text-foreground"
                      >
                        <Linkedin className="h-3 w-3" />
                        LinkedIn
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="profile">
            <TabsList>
              <TabsTrigger value="profile">Profile</TabsTrigger>
              <TabsTrigger value="applications">Applications</TabsTrigger>
              <TabsTrigger value="interviews">Interviews</TabsTrigger>
              <TabsTrigger value="notes">Notes</TabsTrigger>
            </TabsList>

            <TabsContent value="profile" className="mt-4 space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Skills</CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-wrap gap-1.5">
                    {candidate.skills.length === 0 && (
                      <span className="text-sm text-muted-foreground">None listed</span>
                    )}
                    {candidate.skills.map((s) => (
                      <Badge key={s} variant="secondary">
                        {s}
                      </Badge>
                    ))}
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Compensation</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Current CTC</span>
                      <span className="font-medium">
                        {candidate.current_ctc ? `$${candidate.current_ctc.toLocaleString()}` : "—"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Expected CTC</span>
                      <span className="font-medium">
                        {candidate.expected_ctc
                          ? `$${candidate.expected_ctc.toLocaleString()}`
                          : "—"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Notice period</span>
                      <span className="font-medium">{candidate.notice_period ?? "—"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Work auth</span>
                      <span className="font-medium">{candidate.work_auth ?? "—"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Relocation</span>
                      <span className="font-medium">
                        {candidate.relocation_ok ? "Open" : "Not open"}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </div>
              {candidate.education.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Education</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm space-y-2">
                    {candidate.education.map((e, i) => (
                      <div key={i}>
                        <div className="font-medium">{e.degree}</div>
                        <div className="text-muted-foreground text-xs">
                          {e.school} {e.year ? `· ${e.year}` : ""}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="applications" className="mt-4">
              <Card>
                <CardContent className="p-0">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="p-3 text-left">Job</th>
                        <th className="p-3 text-left">Stage</th>
                        <th className="p-3 text-left">Status</th>
                        <th className="p-3 text-left">Applied</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {(applications ?? []).length === 0 && (
                        <tr>
                          <td colSpan={4} className="p-6 text-center text-sm text-muted-foreground">
                            No applications yet.
                          </td>
                        </tr>
                      )}
                      {(applications ?? []).map((a) => {
                        const job = jobById.get(a.job_id);
                        return (
                          <tr key={a.id}>
                            <td className="p-3">
                              {job ? (
                                <Link
                                  href={`/jobs/${job.id}`}
                                  className="font-medium hover:underline"
                                >
                                  {job.title}
                                </Link>
                              ) : (
                                "—"
                              )}
                            </td>
                            <td className="p-3">
                              <StageBadge
                                stage={
                                  a.current_stage_id
                                    ? (stageById.get(a.current_stage_id) ?? "—")
                                    : "—"
                                }
                              />
                            </td>
                            <td className="p-3 text-xs">{a.status}</td>
                            <td className="p-3 text-xs text-muted-foreground">
                              {new Date(a.applied_at).toLocaleDateString()}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="interviews" className="mt-4 space-y-3">
              {candidateInterviews.length === 0 && (
                <Card>
                  <CardContent className="p-8 text-center text-sm text-muted-foreground">
                    No interviews scheduled yet.
                  </CardContent>
                </Card>
              )}
              {candidateInterviews.map((iv) => (
                <Card key={iv.id}>
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="grid place-items-center h-10 w-10 rounded-md bg-primary/10 text-primary">
                      <Clock className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-sm">{iv.round_name}</div>
                      <div className="text-xs text-muted-foreground">
                        {iv.mode} · {new Date(iv.scheduled_at).toLocaleString()}
                      </div>
                    </div>
                    <Badge variant="outline">{iv.status}</Badge>
                    {iv.feedback_entries.length > 0 && (
                      <Badge variant="secondary" className="text-[10px]">
                        {iv.feedback_entries[0].recommendation}
                      </Badge>
                    )}
                  </CardContent>
                </Card>
              ))}
            </TabsContent>

            <TabsContent value="notes" className="mt-4 space-y-4">
              <form onSubmit={handleAddNote} className="flex gap-2">
                <Textarea
                  rows={2}
                  placeholder="Add a note about this candidate…"
                  value={noteBody}
                  onChange={(e) => setNoteBody(e.target.value)}
                  className="flex-1"
                />
                <Button type="submit" disabled={addNote.isPending || !noteBody.trim()}>
                  Add
                </Button>
              </form>
              <Card>
                <CardContent className="p-5 space-y-3 text-sm">
                  {(notes ?? []).length === 0 && (
                    <div className="text-muted-foreground">No notes yet.</div>
                  )}
                  {(notes ?? []).map((n) => (
                    <div key={n.id} className="p-3 rounded-md border bg-muted/20">
                      <div className="text-xs text-muted-foreground mb-1">
                        {relativeTime(n.created_at)}
                      </div>
                      {n.body}
                    </div>
                  ))}
                </CardContent>
              </Card>
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
