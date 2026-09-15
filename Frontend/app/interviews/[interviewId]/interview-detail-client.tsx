"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
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
  useInterview,
  useConsolidatedFeedback,
  useSubmitInterviewFeedback,
  useUpdateInterview,
} from "@/lib/hooks/use-interviews";
import { useApplication } from "@/lib/hooks/use-applications";
import { useCandidate } from "@/lib/hooks/use-candidates";
import { useJob } from "@/lib/hooks/use-jobs";
import { useUsers } from "@/lib/hooks/use-users";
import { useAuth } from "@/lib/auth/auth-context";
import { ApiError } from "@/lib/api/client";
import { formatDateTime, initialsOf, relativeTime } from "@/lib/utils";
import { Video, MapPin, Phone, Star } from "lucide-react";

const RECOMMENDATIONS = ["Strong Yes", "Yes", "No", "Strong No"] as const;
const STATUSES = ["Scheduled", "Completed", "Cancelled", "Rescheduled"] as const;

const modeIcon: Record<string, typeof Video> = {
  Video,
  Onsite: MapPin,
  Phone,
};

function FeedbackForm({
  interviewId,
  alreadySubmitted,
}: {
  interviewId: string;
  alreadySubmitted: boolean;
}) {
  const [rating, setRating] = useState(3);
  const [recommendation, setRecommendation] = useState<string>("Yes");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const submitFeedback = useSubmitInterviewFeedback(interviewId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await submitFeedback.mutateAsync({ rating, recommendation, notes: notes || undefined });
      setDone(true);
      setNotes("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit feedback.");
    }
  }

  if (done) {
    return (
      <p className="text-sm text-[color:var(--color-success)]">
        Feedback submitted. Thanks — it&apos;s now part of the consolidated view.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && <div className="text-sm text-destructive">{error}</div>}
      {alreadySubmitted && (
        <p className="text-xs text-muted-foreground">
          You&apos;ve already left feedback on this round. Submitting again adds another entry.
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label className="text-xs">Rating</Label>
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setRating(n)}
                aria-label={`${n} star${n === 1 ? "" : "s"}`}
                className="p-0.5"
              >
                <Star
                  className={
                    n <= rating
                      ? "h-5 w-5 fill-amber-400 text-amber-400"
                      : "h-5 w-5 text-muted-foreground"
                  }
                />
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Recommendation</Label>
          <Select value={recommendation} onValueChange={setRecommendation}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {RECOMMENDATIONS.map((r) => (
                <SelectItem key={r} value={r}>
                  {r}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="space-y-1.5">
        <Label className="text-xs">Notes</Label>
        <Textarea
          rows={5}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="What did you probe, and what did you conclude?"
        />
      </div>
      <Button type="submit" size="sm" disabled={submitFeedback.isPending}>
        {submitFeedback.isPending ? "Submitting…" : "Submit feedback"}
      </Button>
    </form>
  );
}

export function InterviewDetailClient() {
  const params = useParams<{ interviewId: string }>();
  const interviewId = params.interviewId;
  const { user } = useAuth();

  const { data: interview, isLoading } = useInterview(interviewId);
  const { data: consolidated } = useConsolidatedFeedback(interviewId);
  const { data: application } = useApplication(interview?.application_id);
  const { data: candidate } = useCandidate(application?.candidate_id);
  const { data: job } = useJob(application?.job_id);
  const { data: users } = useUsers();
  const updateInterview = useUpdateInterview(interviewId);

  const [rescheduleAt, setRescheduleAt] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  if (isLoading) {
    return (
      <AppShell title="Interview">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </AppShell>
    );
  }

  if (!interview) {
    return (
      <AppShell title="Interview not found">
        <div className="text-sm text-muted-foreground">
          This interview doesn&apos;t exist or you don&apos;t have access.{" "}
          <Link href="/interviews" className="text-primary hover:underline">
            Back to interviews
          </Link>
        </div>
      </AppShell>
    );
  }

  const userById = new Map((users ?? []).map((u) => [u.id, u]));
  const ModeIcon = modeIcon[interview.mode] ?? Video;
  const myFeedback = interview.feedback_entries.some((f) => f.submitted_by === user?.id);

  async function handleStatusChange(status: string) {
    setActionError(null);
    try {
      await updateInterview.mutateAsync({ status });
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to update the interview.");
    }
  }

  async function handleReschedule() {
    if (!rescheduleAt) return;
    setActionError(null);
    try {
      await updateInterview.mutateAsync({
        scheduled_at: new Date(rescheduleAt).toISOString(),
        status: "Rescheduled",
      });
      setRescheduleAt("");
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to reschedule.");
    }
  }

  return (
    <AppShell
      title={`${interview.round_name} — ${candidate?.full_name ?? "Candidate"}`}
      breadcrumbs={[
        { label: "Home", to: "/" },
        { label: "Interviews", to: "/interviews" },
        { label: interview.round_name },
      ]}
      actions={
        <Select value={interview.status} onValueChange={handleStatusChange}>
          <SelectTrigger className="h-9 w-[160px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      }
    >
      {actionError && <div className="mb-4 text-sm text-destructive">{actionError}</div>}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-6">
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Round details</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-md border p-3">
                <div className="text-xs text-muted-foreground">Scheduled for</div>
                <div className="mt-0.5 text-sm font-medium">
                  {formatDateTime(interview.scheduled_at)}
                </div>
              </div>
              <div className="rounded-md border p-3">
                <div className="text-xs text-muted-foreground">Mode</div>
                <div className="mt-0.5 flex items-center gap-1.5 text-sm font-medium">
                  <ModeIcon className="h-4 w-4" />
                  {interview.mode}
                </div>
              </div>
              <div className="rounded-md border p-3">
                <div className="text-xs text-muted-foreground">Status</div>
                <div className="mt-0.5">
                  <Badge variant="secondary" className="text-[10px]">
                    {interview.status}
                  </Badge>
                </div>
              </div>
              <div className="rounded-md border p-3">
                <div className="text-xs text-muted-foreground">Feedback received</div>
                <div className="mt-0.5 text-sm font-medium">
                  {interview.feedback_entries.length} of {interview.panel_members.length || "—"}{" "}
                  panelists
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Leave your feedback</CardTitle>
            </CardHeader>
            <CardContent>
              <FeedbackForm interviewId={interviewId} alreadySubmitted={myFeedback} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Panel feedback</CardTitle>
              {consolidated && consolidated.average_rating != null && (
                <p className="text-xs text-muted-foreground">
                  Average rating {consolidated.average_rating.toFixed(1)} / 5 ·{" "}
                  {Object.entries(consolidated.recommendation_counts)
                    .map(([rec, count]) => `${count}× ${rec}`)
                    .join(", ")}
                </p>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              {interview.feedback_entries.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No feedback submitted yet for this round.
                </p>
              ) : (
                interview.feedback_entries.map((f) => (
                  <div key={f.id} className="rounded-md border p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Avatar className="h-7 w-7">
                          <AvatarFallback className="text-[10px]">
                            {initialsOf(
                              f.submitted_by
                                ? (userById.get(f.submitted_by)?.full_name ?? "?")
                                : "?",
                            )}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="text-sm font-medium">
                            {f.submitted_by
                              ? (userById.get(f.submitted_by)?.full_name ?? "Unknown")
                              : "Unknown"}
                          </div>
                          <div className="text-[11px] text-muted-foreground">
                            {relativeTime(f.created_at)}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="inline-flex items-center gap-0.5">
                          {[1, 2, 3, 4, 5].map((n) => (
                            <Star
                              key={n}
                              className={
                                n <= f.rating
                                  ? "h-3.5 w-3.5 fill-amber-400 text-amber-400"
                                  : "h-3.5 w-3.5 text-muted-foreground"
                              }
                            />
                          ))}
                        </span>
                        <Badge variant="secondary" className="text-[10px]">
                          {f.recommendation}
                        </Badge>
                      </div>
                    </div>
                    {f.notes && (
                      <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">
                        {f.notes}
                      </p>
                    )}
                  </div>
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
                  {application && (
                    <Link
                      href={`/applications/${application.id}`}
                      className="mt-3 inline-block text-xs text-primary hover:underline"
                    >
                      View application
                    </Link>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Loading…</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Panel</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {interview.panel_members.length === 0 ? (
                <p className="text-sm text-muted-foreground">No panel assigned.</p>
              ) : (
                interview.panel_members.map((m) => {
                  const panelist = userById.get(m.user_id);
                  const submitted = interview.feedback_entries.some(
                    (f) => f.submitted_by === m.user_id,
                  );
                  return (
                    <div key={m.user_id} className="flex items-center justify-between gap-2">
                      <div className="min-w-0 text-sm">
                        <span className="truncate">{panelist?.full_name ?? "Unknown"}</span>
                        {m.is_primary && (
                          <Badge variant="outline" className="ml-1.5 text-[10px]">
                            Lead
                          </Badge>
                        )}
                      </div>
                      <Badge
                        variant={submitted ? "secondary" : "outline"}
                        className="text-[10px] shrink-0"
                      >
                        {submitted ? "Submitted" : "Pending"}
                      </Badge>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Reschedule</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Input
                type="datetime-local"
                value={rescheduleAt}
                onChange={(e) => setRescheduleAt(e.target.value)}
              />
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                disabled={!rescheduleAt || updateInterview.isPending}
                onClick={handleReschedule}
              >
                {updateInterview.isPending ? "Saving…" : "Move interview"}
              </Button>
            </CardContent>
          </Card>
        </aside>
      </div>
    </AppShell>
  );
}
