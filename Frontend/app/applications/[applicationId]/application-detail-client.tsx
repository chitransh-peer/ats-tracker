"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell, StageBadge, ScorePill } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useApplication,
  useApplicationTimeline,
  useMoveApplicationStage,
  useApplicationAction,
} from "@/lib/hooks/use-applications";
import { useCandidate } from "@/lib/hooks/use-candidates";
import { useJob } from "@/lib/hooks/use-jobs";
import { useInterviews } from "@/lib/hooks/use-interviews";
import { useStages } from "@/lib/hooks/use-pipeline";
import { useUsers } from "@/lib/hooks/use-users";
import { useAiReview } from "@/lib/hooks/use-ai";
import { ApiError } from "@/lib/api/client";
import { formatDateTime, initialsOf, relativeTime } from "@/lib/utils";
import { CalendarClock, Sparkles } from "lucide-react";

export function ApplicationDetailClient() {
  const params = useParams<{ applicationId: string }>();
  const applicationId = params.applicationId;

  const { data: application, isLoading } = useApplication(applicationId);
  const { data: timeline } = useApplicationTimeline(applicationId);
  const { data: candidate } = useCandidate(application?.candidate_id);
  const { data: job } = useJob(application?.job_id);
  const { data: interviews } = useInterviews({ application_id: applicationId });
  const { data: stageTemplate } = useStages();
  const { data: users } = useUsers();
  const { data: aiReview } = useAiReview(applicationId);

  const moveStage = useMoveApplicationStage();
  const { hold, reject, restore } = useApplicationAction();

  const [targetStageId, setTargetStageId] = useState<string>("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (isLoading) {
    return (
      <AppShell title="Application">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </AppShell>
    );
  }

  if (!application) {
    return (
      <AppShell title="Application not found">
        <div className="text-sm text-muted-foreground">
          This application doesn&apos;t exist or you don&apos;t have access.{" "}
          <Link href="/applications" className="text-primary hover:underline">
            Back to applications
          </Link>
        </div>
      </AppShell>
    );
  }

  const stages = [...(stageTemplate?.stages ?? [])].sort((a, b) => a.sort_order - b.sort_order);
  const stageById = new Map(stages.map((s) => [s.id, s]));
  const userById = new Map((users ?? []).map((u) => [u.id, u]));
  const currentStage = application.current_stage_id
    ? stageById.get(application.current_stage_id)
    : undefined;
  const isTerminal = ["Rejected", "Hired", "Withdrawn"].includes(application.status);

  async function runAction(action: () => Promise<unknown>, failureMessage: string) {
    setError(null);
    try {
      await action();
      setNote("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : failureMessage);
    }
  }

  return (
    <AppShell
      title={candidate?.full_name ?? "Application"}
      breadcrumbs={[
        { label: "Home", to: "/" },
        { label: "Applications", to: "/applications" },
        { label: candidate?.full_name ?? "Application" },
      ]}
      actions={
        <>
          {application.status === "On Hold" || application.status === "Rejected" ? (
            <Button
              size="sm"
              variant="outline"
              disabled={restore.isPending}
              onClick={() =>
                runAction(
                  () => restore.mutateAsync({ applicationId, note: note || undefined }),
                  "Failed to restore the application.",
                )
              }
            >
              Restore
            </Button>
          ) : (
            <>
              <Button
                size="sm"
                variant="outline"
                disabled={hold.isPending}
                onClick={() =>
                  runAction(
                    () => hold.mutateAsync({ applicationId, note: note || undefined }),
                    "Failed to hold the application.",
                  )
                }
              >
                Hold
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="text-destructive"
                disabled={reject.isPending}
                onClick={() =>
                  runAction(
                    () => reject.mutateAsync({ applicationId, note: note || undefined }),
                    "Failed to reject the application.",
                  )
                }
              >
                Reject
              </Button>
            </>
          )}
        </>
      }
    >
      {error && <div className="mb-4 text-sm text-destructive">{error}</div>}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-6">
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Status</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-md border p-3">
                <div className="text-xs text-muted-foreground">Current stage</div>
                <div className="mt-1">
                  <StageBadge stage={currentStage?.name ?? "—"} />
                </div>
              </div>
              <div className="rounded-md border p-3">
                <div className="text-xs text-muted-foreground">Status</div>
                <div className="mt-1">
                  <Badge variant="secondary" className="text-[10px]">
                    {application.status}
                  </Badge>
                </div>
              </div>
              <div className="rounded-md border p-3">
                <div className="text-xs text-muted-foreground">Applied</div>
                <div className="mt-0.5 text-sm font-medium">
                  {formatDateTime(application.applied_at)}
                </div>
              </div>
              <div className="rounded-md border p-3">
                <div className="text-xs text-muted-foreground">Source</div>
                <div className="mt-0.5 text-sm font-medium">{application.source ?? "—"}</div>
              </div>
            </CardContent>
          </Card>

          {!isTerminal && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Move stage</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
                  <div className="space-y-1.5">
                    <Label className="text-xs">Move to</Label>
                    <Select value={targetStageId} onValueChange={setTargetStageId}>
                      <SelectTrigger>
                        <SelectValue placeholder="Pick a stage" />
                      </SelectTrigger>
                      <SelectContent>
                        {stages
                          .filter((s) => s.id !== application.current_stage_id)
                          .map((s) => (
                            <SelectItem key={s.id} value={s.id}>
                              {s.name}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    size="sm"
                    disabled={!targetStageId || moveStage.isPending}
                    onClick={() =>
                      runAction(async () => {
                        await moveStage.mutateAsync({
                          applicationId,
                          toStageId: targetStageId,
                          note: note || undefined,
                        });
                        setTargetStageId("");
                      }, "Failed to move the application.")
                    }
                  >
                    {moveStage.isPending ? "Moving…" : "Move"}
                  </Button>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">
                    Note{" "}
                    <span className="text-muted-foreground">(applies to any action above)</span>
                  </Label>
                  <Textarea
                    rows={2}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Why is this moving?"
                  />
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              {(timeline ?? []).length === 0 ? (
                <p className="text-sm text-muted-foreground">No stage movements recorded yet.</p>
              ) : (
                <ol className="space-y-3">
                  {[...(timeline ?? [])]
                    .sort(
                      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
                    )
                    .map((entry) => (
                      <li key={entry.id} className="flex gap-3">
                        <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                        <div className="min-w-0 flex-1">
                          <div className="text-sm">
                            {entry.from_stage_id
                              ? `${stageById.get(entry.from_stage_id)?.name ?? "—"} → `
                              : "Entered "}
                            <span className="font-medium">
                              {entry.to_stage_id
                                ? (stageById.get(entry.to_stage_id)?.name ?? "—")
                                : "—"}
                            </span>
                          </div>
                          <div className="text-[11px] text-muted-foreground">
                            {entry.changed_by
                              ? (userById.get(entry.changed_by)?.full_name ?? "Unknown")
                              : "System"}{" "}
                            · {relativeTime(entry.created_at)}
                          </div>
                          {entry.note && (
                            <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">
                              {entry.note}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                </ol>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Interviews</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {(interviews ?? []).length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No interviews scheduled for this application.
                </p>
              ) : (
                (interviews ?? []).map((iv) => (
                  <Link
                    key={iv.id}
                    href={`/interviews/${iv.id}`}
                    className="flex items-center gap-3 rounded-md border p-3 hover:bg-muted/30"
                  >
                    <div className="grid h-9 w-9 place-items-center rounded-md bg-primary/10 text-primary">
                      <CalendarClock className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium">{iv.round_name}</div>
                      <div className="text-xs text-muted-foreground">
                        {formatDateTime(iv.scheduled_at)} · {iv.mode}
                      </div>
                    </div>
                    <Badge variant="secondary" className="text-[10px] shrink-0">
                      {iv.status}
                    </Badge>
                  </Link>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <aside className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Candidate</CardTitle>
            </CardHeader>
            <CardContent>
              {candidate ? (
                <>
                  <div className="flex items-center gap-2">
                    <Avatar className="h-9 w-9">
                      <AvatarFallback className="text-xs">
                        {initialsOf(candidate.full_name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                      <Link
                        href={`/candidates/${candidate.id}`}
                        className="text-sm font-medium hover:underline"
                      >
                        {candidate.full_name}
                      </Link>
                      <div className="text-xs text-muted-foreground truncate">
                        {candidate.current_title ?? "—"}
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 space-y-1 text-xs text-muted-foreground">
                    <div>{candidate.email}</div>
                    {candidate.phone && <div>{candidate.phone}</div>}
                    {candidate.location && <div>{candidate.location}</div>}
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Loading…</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Role</CardTitle>
            </CardHeader>
            <CardContent>
              {job ? (
                <>
                  <Link href={`/jobs/${job.id}`} className="text-sm font-medium hover:underline">
                    {job.title}
                  </Link>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {job.req_id} · {job.location ?? "—"}
                  </div>
                  <Badge variant="secondary" className="mt-2 text-[10px]">
                    {job.status}
                  </Badge>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Loading…</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-primary" />
                AI review
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!aiReview ? (
                <p className="text-sm text-muted-foreground">
                  No AI evaluation has run for this application yet.
                </p>
              ) : (
                <>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-muted-foreground">Match score</span>
                    {aiReview.overall_score != null ? (
                      <ScorePill score={Math.round(aiReview.overall_score)} />
                    ) : (
                      <span className="text-xs text-muted-foreground capitalize">
                        {aiReview.status}
                      </span>
                    )}
                  </div>
                  {aiReview.recommendation_label && (
                    <div className="mt-2 text-sm font-medium capitalize">
                      {aiReview.recommendation_label.replace(/_/g, " ")}
                    </div>
                  )}
                  {aiReview.strengths.length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-medium">Strengths</div>
                      <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
                        {aiReview.strengths.slice(0, 3).map((s) => (
                          <li key={s}>· {s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <Link
                    href={`/ai-review?applicationId=${applicationId}`}
                    className="mt-3 inline-block text-xs text-primary hover:underline"
                  >
                    View full AI breakdown
                  </Link>
                </>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>
    </AppShell>
  );
}
