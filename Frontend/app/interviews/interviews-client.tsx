"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { useInterviews, useCreateInterview } from "@/lib/hooks/use-interviews";
import { useApplications } from "@/lib/hooks/use-applications";
import { useCandidates } from "@/lib/hooks/use-candidates";
import { useJobs } from "@/lib/hooks/use-jobs";
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

const modeIcon = { Video, Phone, Onsite: MapPin } as const;

function ScheduleInterviewDialog() {
  const [open, setOpen] = useState(false);
  const [applicationId, setApplicationId] = useState("");
  const [roundName, setRoundName] = useState("Recruiter Screen");
  const [mode, setMode] = useState("Video");
  const [scheduledAt, setScheduledAt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { data: applications } = useApplications({ status: "Active" });
  const { data: candidates } = useCandidates();
  const { data: jobs } = useJobs();
  const createInterview = useCreateInterview();

  const candidateById = new Map((candidates ?? []).map((c) => [c.id, c]));
  const jobById = new Map((jobs ?? []).map((j) => [j.id, j]));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createInterview.mutateAsync({
        application_id: applicationId,
        round_name: roundName,
        mode,
        scheduled_at: new Date(scheduledAt).toISOString(),
      });
      setOpen(false);
      setApplicationId("");
      setScheduledAt("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to schedule interview.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">Schedule interview</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Schedule interview</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="space-y-1.5">
            <Label className="text-xs">Application</Label>
            <Select value={applicationId} onValueChange={setApplicationId} required>
              <SelectTrigger>
                <SelectValue placeholder="Select candidate · job" />
              </SelectTrigger>
              <SelectContent>
                {(applications ?? []).map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {candidateById.get(a.candidate_id)?.full_name ?? "Unknown"} ·{" "}
                    {jobById.get(a.job_id)?.title ?? "Unknown"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
                  <SelectItem value="Video">Video</SelectItem>
                  <SelectItem value="Phone">Phone</SelectItem>
                  <SelectItem value="Onsite">Onsite</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">When</Label>
              <Input
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
                required
              />
            </div>
          </div>
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

export function InterviewsClient() {
  const { data: interviews, isLoading } = useInterviews();
  const { data: applications } = useApplications();
  const { data: candidates } = useCandidates();
  const { data: jobs } = useJobs();

  const applicationById = new Map((applications ?? []).map((a) => [a.id, a]));
  const candidateById = new Map((candidates ?? []).map((c) => [c.id, c]));
  const jobById = new Map((jobs ?? []).map((j) => [j.id, j]));

  return (
    <AppShell
      title="Interviews"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Interviews" }]}
      actions={<ScheduleInterviewDialog />}
    >
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <StatCard
          label="Scheduled"
          value={interviews?.filter((i) => i.status === "Scheduled").length ?? 0}
        />
        <StatCard
          label="Completed"
          value={interviews?.filter((i) => i.status === "Completed").length ?? 0}
        />
        <StatCard
          label="Awaiting feedback"
          value={
            interviews?.filter((i) => i.status === "Completed" && i.feedback_entries.length === 0)
              .length ?? 0
          }
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
                <th className="p-3 text-left">Mode</th>
                <th className="p-3 text-left">Status</th>
                <th className="p-3 text-left">Feedback</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {isLoading && (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-sm text-muted-foreground">
                    Loading…
                  </td>
                </tr>
              )}
              {!isLoading && (interviews?.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-sm text-muted-foreground">
                    No interviews scheduled yet.
                  </td>
                </tr>
              )}
              {interviews?.map((iv) => {
                const application = applicationById.get(iv.application_id);
                const candidate = application
                  ? candidateById.get(application.candidate_id)
                  : undefined;
                const job = application ? jobById.get(application.job_id) : undefined;
                const Icon = modeIcon[iv.mode as keyof typeof modeIcon] ?? Video;
                return (
                  <tr key={iv.id} className="hover:bg-muted/30">
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
                          "Unknown"
                        )}
                      </div>
                    </td>
                    <td className="p-3 text-xs">{job?.title ?? "—"}</td>
                    <td className="p-3">
                      <Badge variant="secondary" className="text-[10px]">
                        {iv.round_name}
                      </Badge>
                    </td>
                    <td className="p-3 text-xs">{new Date(iv.scheduled_at).toLocaleString()}</td>
                    <td className="p-3 text-xs">
                      <span className="inline-flex items-center gap-1">
                        <Icon className="h-3 w-3" />
                        {iv.mode}
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
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </AppShell>
  );
}
