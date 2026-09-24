"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell, StageBadge, ScorePill } from "@/components/layout/AppShell";
import {
  useCandidate,
  useCandidateNotes,
  useAddCandidateNote,
  useCandidateMessages,
  useSendCandidateMessage,
  useCandidateDocuments,
} from "@/lib/hooks/use-candidates";
import { downloadCandidateDocument } from "@/lib/api/candidates";
import type { CandidateDocument } from "@/lib/api/types";
import { useTemplates } from "@/lib/hooks/use-templates";
import { useEmailStatus } from "@/lib/hooks/use-settings";
import { useAuth } from "@/lib/auth/auth-context";
import { ApiError } from "@/lib/api/client";
import type { Application, Job } from "@/lib/api/types";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Mail,
  Phone,
  MapPin,
  Linkedin,
  Clock,
  Sparkles,
  FileText,
  Download,
  Loader2,
} from "lucide-react";
import { initialsOf, relativeTime } from "@/lib/utils";

/** Fill the merge tokens we can resolve from the current context. Anything we
 *  can't resolve is left visible so the recruiter notices before sending. */
function applyTokens(
  text: string,
  ctx: { candidateName: string; jobTitle: string | null; recruiterName: string },
): string {
  return text
    .replace(/\{\{candidate_first_name\}\}/g, ctx.candidateName.split(" ")[0] ?? "")
    .replace(/\{\{candidate_full_name\}\}/g, ctx.candidateName)
    .replace(/\{\{recruiter_name\}\}/g, ctx.recruiterName)
    .replace(/\{\{job_title\}\}/g, ctx.jobTitle ?? "{{job_title}}");
}

function MessagesTab({
  candidateId,
  candidateName,
  candidateEmail,
  applications,
  jobById,
}: {
  candidateId: string;
  candidateName: string;
  candidateEmail: string;
  applications: Application[];
  jobById: Map<string, Job>;
}) {
  const { user } = useAuth();
  const { data: emailStatus } = useEmailStatus();
  const { data: messages, isLoading } = useCandidateMessages(candidateId);
  const { data: templates } = useTemplates();
  const sendMessage = useSendCandidateMessage(candidateId);

  const [applicationId, setApplicationId] = useState<string>("none");
  const [templateId, setTemplateId] = useState<string>("none");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  const linkedJobTitle =
    applicationId === "none"
      ? null
      : (jobById.get(applications.find((a) => a.id === applicationId)?.job_id ?? "")?.title ??
        null);

  function handleTemplateChange(nextId: string) {
    setTemplateId(nextId);
    const template = (templates ?? []).find((t) => t.id === nextId);
    if (!template) return;
    const ctx = {
      candidateName,
      jobTitle: linkedJobTitle,
      recruiterName: user?.full_name ?? "",
    };
    setSubject(applyTokens(template.subject, ctx));
    setBody(applyTokens(template.body, ctx));
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await sendMessage.mutateAsync({
        subject,
        body,
        application_id: applicationId === "none" ? null : applicationId,
        template_id: templateId === "none" ? null : templateId,
      });
      setSubject("");
      setBody("");
      setTemplateId("none");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to log the message.");
    }
  }

  const unresolvedTokens = /\{\{[a-z_]+\}\}/.test(subject + body);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Compose message</CardTitle>
          <p className="text-xs text-muted-foreground">
            {emailStatus?.enabled
              ? `Sends to ${candidateEmail} and is recorded against the candidate.`
              : `Email delivery isn't configured, so this is recorded as an outreach log rather than delivered to ${candidateEmail}.`}
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSend} className="space-y-3">
            {error && <div className="text-sm text-destructive">{error}</div>}
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-xs">Template</Label>
                <Select value={templateId} onValueChange={handleTemplateChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="Start from scratch" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Start from scratch</SelectItem>
                    {(templates ?? []).map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Link to application</Label>
                <Select value={applicationId} onValueChange={setApplicationId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Not linked" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Not linked</SelectItem>
                    {applications.map((a) => (
                      <SelectItem key={a.id} value={a.id}>
                        {jobById.get(a.job_id)?.title ?? "Role"}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Subject</Label>
              <Input value={subject} onChange={(e) => setSubject(e.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Message</Label>
              <Textarea
                rows={8}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                required
                className="font-mono text-sm"
              />
            </div>
            {unresolvedTokens && (
              <p className="text-xs text-[color:var(--color-warning-foreground)]">
                This message still contains unfilled <code>{"{{tokens}}"}</code> — link an
                application or edit them by hand before sending.
              </p>
            )}
            <Button
              type="submit"
              size="sm"
              disabled={sendMessage.isPending || !subject.trim() || !body.trim()}
            >
              {sendMessage.isPending ? "Logging…" : "Log message"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Outreach history</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            <div className="text-sm text-muted-foreground">Loading…</div>
          ) : (messages ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No messages logged for this candidate yet.
            </p>
          ) : (
            [...(messages ?? [])]
              .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
              .map((m) => (
                <div key={m.id} className="rounded-md border p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="text-sm font-medium">{m.subject}</div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant="secondary" className="text-[10px] capitalize">
                        {m.status}
                      </Badge>
                      <span className="text-[11px] text-muted-foreground">
                        {relativeTime(m.created_at)}
                      </span>
                    </div>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">{m.body}</p>
                </div>
              ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

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
              <TabsTrigger value="documents">Documents</TabsTrigger>
              <TabsTrigger value="messages">Messages</TabsTrigger>
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

            <TabsContent value="documents" className="mt-4">
              <DocumentsTab candidateId={candidateId} />
            </TabsContent>

            <TabsContent value="messages" className="mt-4">
              <MessagesTab
                candidateId={candidateId}
                candidateName={candidate.full_name}
                candidateEmail={candidate.email}
                applications={applications ?? []}
                jobById={jobById}
              />
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
            <CardContent className="space-y-3">
              {(applications ?? []).length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No applications yet — AI scoring runs automatically once this candidate applies.
                </p>
              )}
              {(applications ?? []).map((app) => {
                const job = (jobs ?? []).find((j) => j.id === app.job_id);
                const score = typeof app.ai_score === "number" ? Math.round(app.ai_score) : null;
                return (
                  <div key={app.id} className="rounded-md border p-3 space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium truncate">{job?.title ?? "Role"}</span>
                      {score !== null ? (
                        <ScorePill score={score} />
                      ) : (
                        <span className="text-[11px] text-muted-foreground">Pending</span>
                      )}
                    </div>
                    {app.ai_recommendation && (
                      <div className="text-xs text-muted-foreground capitalize">
                        {app.ai_recommendation.replace(/_/g, " ")}
                      </div>
                    )}
                    <Link
                      href={`/ai-review?applicationId=${app.id}`}
                      className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                    >
                      View full AI breakdown
                    </Link>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </aside>
      </div>
    </AppShell>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function DocumentsTab({ candidateId }: { candidateId: string }) {
  const { data: documents, isLoading } = useCandidateDocuments(candidateId);
  // Tracked per document so two downloads at once each show their own spinner.
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleDownload(doc: CandidateDocument) {
    setError(null);
    setDownloadingId(doc.id);
    try {
      await downloadCandidateDocument(candidateId, doc);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not download that file.");
    } finally {
      setDownloadingId(null);
    }
  }

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Loading documents…</div>;
  }

  if (!documents || documents.length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-sm text-muted-foreground">
          No documents yet. Résumés uploaded for this candidate will appear here.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}
      <Card>
        <CardContent className="p-0 divide-y">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center gap-3 p-4">
              <div className="h-9 w-9 rounded-md bg-muted grid place-items-center shrink-0">
                <FileText className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{doc.file_name}</div>
                <div className="text-xs text-muted-foreground">
                  <span className="capitalize">{doc.document_type.replace(/_/g, " ")}</span>
                  {" · "}
                  {formatFileSize(doc.size_bytes)}
                  {" · "}
                  {relativeTime(doc.created_at)}
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDownload(doc)}
                disabled={downloadingId === doc.id}
              >
                {downloadingId === doc.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-1" />
                    Download
                  </>
                )}
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
