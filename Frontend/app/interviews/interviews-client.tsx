"use client";

import { interviewModeLabel } from "@/lib/api/interviews";
import { useCallback, useState } from "react";
import { useQuickCreate } from "@/lib/hooks/use-quick-create";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import {
  useCreateInterview,
  useInterviewSummary,
  useInterviewsPage,
} from "@/lib/hooks/use-interviews";
import { EntityPicker } from "@/components/entity-picker";
import { Pager } from "@/components/ui/pager";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Video, MapPin, Phone } from "lucide-react";
import { initialsOf } from "@/lib/utils";
import { ApiError } from "@/lib/api/client";
import { InterviewerPicker } from "@/components/interviewer-picker";
import {
  INTERVIEW_TIMEZONES,
  defaultTimezone,
  formatForViewer,
  formatInZone,
  zonedToUtcIso,
} from "@/lib/timezones";

const modeIcon = { Video, Phone, Onsite: MapPin } as const;

function ScheduleInterviewDialog() {
  const [open, setOpen] = useState(false);
  useQuickCreate(useCallback(() => setOpen(true), []));
  const [applicationId, setApplicationId] = useState("");
  const [roundName, setRoundName] = useState("Recruiter Screen");
  const [mode, setMode] = useState("Video");
  const [scheduledAt, setScheduledAt] = useState("");
  const [timezone, setTimezone] = useState(defaultTimezone);
  const [duration, setDuration] = useState("60");
  const [interviewers, setInterviewers] = useState<string[]>([]);
  const [meetingLink, setMeetingLink] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const createInterview = useCreateInterview();

  // The slot as the other side of the US–India split will read it.
  const preview = scheduledAt ? zonedToUtcIso(scheduledAt, timezone) : null;
  const otherZone = timezone === "Asia/Kolkata" ? "America/New_York" : "Asia/Kolkata";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (interviewers.length === 0) {
      setError("Add at least one interviewer.");
      return;
    }
    try {
      await createInterview.mutateAsync({
        application_id: applicationId,
        round_name: roundName,
        mode,
        scheduled_at: zonedToUtcIso(scheduledAt, timezone),
        timezone,
        duration_minutes: Number(duration),
        panel_user_ids: interviewers,
        primary_interviewer_id: interviewers[0],
        meeting_link: mode === "Onsite" ? null : meetingLink.trim() || null,
        location: mode === "Onsite" ? location.trim() || null : null,
      });
      setOpen(false);
      setApplicationId("");
      setScheduledAt("");
      setInterviewers([]);
      setMeetingLink("");
      setLocation("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to schedule interview.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">Schedule interview</Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Schedule interview</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="space-y-1.5">
            <Label className="text-xs">Application</Label>
            {/* Searched on the server: listing every active application, with
                every candidate and job to name them, froze the dialog. */}
            <EntityPicker
              kind="applications"
              status="Active"
              value={applicationId || null}
              onChange={(id) => setApplicationId(id ?? "")}
              placeholder="Search candidate or job"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Round name</Label>
            <Input value={roundName} onChange={(e) => setRoundName(e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Mode</Label>
              <Select value={mode} onValueChange={setMode}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Video">Visual Round</SelectItem>
                  <SelectItem value="Phone">Phone</SelectItem>
                  <SelectItem value="Onsite">Onsite</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Duration</Label>
              <Select value={duration} onValueChange={setDuration}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[15, 30, 45, 60, 90, 120].map((m) => (
                    <SelectItem key={m} value={String(m)}>
                      {m < 60 ? `${m} min` : `${m / 60} hr${m > 60 ? "s" : ""}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Date &amp; time</Label>
              <Input
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Time zone</Label>
              <Select value={timezone} onValueChange={setTimezone}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {INTERVIEW_TIMEZONES.map((z) => (
                    <SelectItem key={z.value} value={z.value}>
                      {z.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          {preview && (
            <p className="text-xs text-muted-foreground">
              {formatInZone(preview, timezone)} · {formatInZone(preview, otherZone)}
            </p>
          )}
          <div className="space-y-1.5">
            <Label className="text-xs">Interviewers</Label>
            <InterviewerPicker value={interviewers} onChange={setInterviewers} />
          </div>
          {mode === "Onsite" ? (
            <div className="space-y-1.5">
              <Label className="text-xs">Location</Label>
              <Input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Office address, floor, room"
                maxLength={500}
                required
              />
            </div>
          ) : (
            <div className="space-y-1.5">
              <Label className="text-xs">
                {mode === "Phone" ? "Dial-in / bridge link (optional)" : "Meeting link"}
              </Label>
              <Input
                type="url"
                value={meetingLink}
                onChange={(e) => setMeetingLink(e.target.value)}
                placeholder="https://teams.microsoft.com/…"
                maxLength={1000}
                required={mode === "Video"}
              />
            </div>
          )}
          <DialogFooter>
            <Button type="submit" disabled={createInterview.isPending || !applicationId}>
              {createInterview.isPending ? "Scheduling…" : "Schedule"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

const PAGE_SIZE = 50;

export function InterviewsClient() {
  const [offset, setOffset] = useState(0);
  // Paged, with each interview's candidate and job named by the server and
  // the stat cards counted there, instead of loading every interview,
  // application, candidate and job to join them here.
  const { data, isLoading } = useInterviewsPage({ limit: PAGE_SIZE, offset });
  const { data: summary } = useInterviewSummary();
  const interviews = data?.data;

  return (
    <AppShell
      title="Interviews"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Interviews" }]}
      actions={<ScheduleInterviewDialog />}
    >
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <StatCard label="Scheduled" value={summary?.scheduled ?? 0} />
        <StatCard label="Completed" value={summary?.completed ?? 0} />
        <StatCard
          label="Awaiting feedback"
          value={summary?.awaiting_feedback ?? 0}
          tone="warning"
        />
      </div>

      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="p-3 text-left">Candidate</th>
                <th className="p-3 text-left">Job</th>
                <th className="p-3 text-left">Round</th>
                <th className="p-3 text-left">When</th>
                <th className="p-3 text-left">Interviewers</th>
                <th className="p-3 text-left">Mode</th>
                <th className="p-3 text-left">Status</th>
                <th className="p-3 text-left">Feedback</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {isLoading && (
                <tr>
                  <td colSpan={8} className="p-6 text-center text-sm text-muted-foreground">
                    Loading…
                  </td>
                </tr>
              )}
              {!isLoading && (interviews?.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={8} className="p-6 text-center text-sm text-muted-foreground">
                    No interviews scheduled yet.
                  </td>
                </tr>
              )}
              {interviews?.map((iv) => {
                const Icon = modeIcon[iv.mode as keyof typeof modeIcon] ?? Video;
                return (
                  <tr key={iv.id} className="hover:bg-muted/30">
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <Avatar className="h-7 w-7">
                          <AvatarFallback className="text-[10px]">
                            {iv.candidate_name ? initialsOf(iv.candidate_name) : "?"}
                          </AvatarFallback>
                        </Avatar>
                        {iv.candidate_id && iv.candidate_name ? (
                          <Link
                            href={`/candidates/${iv.candidate_id}`}
                            className="hover:underline font-medium"
                          >
                            {iv.candidate_name}
                          </Link>
                        ) : (
                          "Unknown"
                        )}
                      </div>
                    </td>
                    <td className="p-3 text-xs">{iv.job_title ?? "—"}</td>
                    <td className="p-3">
                      <Link href={`/interviews/${iv.id}`} className="hover:underline">
                        <Badge variant="secondary" className="text-[10px]">
                          {iv.round_name}
                        </Badge>
                      </Link>
                    </td>
                    <td className="p-3 text-xs">
                      {iv.timezone ? (
                        <>
                          <div>{formatInZone(iv.scheduled_at, iv.timezone)}</div>
                          {formatForViewer(iv.scheduled_at, iv.timezone) && (
                            <div className="text-muted-foreground">
                              {formatForViewer(iv.scheduled_at, iv.timezone)} (yours)
                            </div>
                          )}
                        </>
                      ) : (
                        new Date(iv.scheduled_at).toLocaleString()
                      )}
                    </td>
                    <td className="p-3 text-xs">
                      {iv.panel_members.length
                        ? iv.panel_members.map((m) => m.full_name ?? "Unknown").join(", ")
                        : "—"}
                    </td>
                    <td className="p-3 text-xs">
                      <span className="inline-flex items-center gap-1">
                        <Icon className="h-3 w-3" />
                        {interviewModeLabel(iv.mode)}
                      </span>
                    </td>
                    <td className="p-3">
                      <Badge
                        variant={iv.status === "Completed" ? "secondary" : "outline"}
                        className="text-[10px]"
                      >
                        {iv.status}
                      </Badge>
                    </td>
                    <td className="p-3">
                      {iv.feedback_entries.length > 0 ? (
                        <Badge className="text-[10px]" variant="secondary">
                          {iv.feedback_entries[0].recommendation}
                        </Badge>
                      ) : (
                        <Link
                          href={`/interviews/${iv.id}`}
                          className="text-xs text-primary hover:underline"
                        >
                          Add feedback
                        </Link>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
        <Pager
          offset={offset}
          limit={PAGE_SIZE}
          total={data?.total ?? 0}
          onOffsetChange={setOffset}
        />
      </Card>
    </AppShell>
  );
}
