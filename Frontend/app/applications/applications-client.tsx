"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { AppShell, StageBadge, StatCard, ScorePill } from "@/components/layout/AppShell";
import {
  useApplicationsPage,
  useBulkRejectApplications,
  useBulkHoldApplications,
} from "@/lib/hooks/use-applications";
import { useCandidates } from "@/lib/hooks/use-candidates";
import { useJobs } from "@/lib/hooks/use-jobs";
import { useStages } from "@/lib/hooks/use-pipeline";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Search, XCircle, PauseCircle } from "lucide-react";
import { initialsOf } from "@/lib/utils";
import { Pager } from "@/components/ui/pager";
import type { BulkActionResult } from "@/lib/api/applications";

const PAGE_SIZE = 50;

/** Surfaces a partial-failure bulk result as toasts, since some rows can
 * succeed while others fail (e.g. one was already rejected). */
function reportBulkResult(result: BulkActionResult, verb: string) {
  if (result.succeeded.length > 0) {
    toast.success(
      `${verb} ${result.succeeded.length} application${result.succeeded.length === 1 ? "" : "s"}.`,
    );
  }
  if (result.failed.length > 0) {
    toast.error(
      `${result.failed.length} application${result.failed.length === 1 ? "" : "s"} couldn't be ${verb.toLowerCase()}d.`,
      { description: result.failed.map((f) => f.reason).join("; ") },
    );
  }
}

export function ApplicationsClient() {
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmAction, setConfirmAction] = useState<"reject" | "hold" | null>(null);

  const { data, isLoading } = useApplicationsPage({ page_size: PAGE_SIZE, offset });
  const applications = data?.data;
  const total = data?.total ?? 0;
  const { data: candidates } = useCandidates();
  const { data: jobs } = useJobs();
  const { data: stageTemplate } = useStages();
  const bulkReject = useBulkRejectApplications();
  const bulkHold = useBulkHoldApplications();

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

  // Only "Active" applications are eligible for reject/hold — a bulk action
  // silently skipping half a selection because it included stale rows would
  // be confusing, so ineligible rows just aren't selectable to begin with.
  const eligibleIds = useMemo(
    () =>
      new Set(rows.filter((r) => r.application.status === "Active").map((r) => r.application.id)),
    [rows],
  );
  const selectedEligible = [...selected].filter((id) => eligibleIds.has(id));
  const allEligibleSelected = eligibleIds.size > 0 && selectedEligible.length === eligibleIds.size;

  function toggleRow(id: string, checked: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  function toggleAll(checked: boolean) {
    setSelected(checked ? new Set(eligibleIds) : new Set());
  }

  function updateSearch(value: string) {
    setSearch(value);
    setOffset(0);
  }

  async function runBulkAction() {
    const ids = selectedEligible;
    const action = confirmAction;
    setConfirmAction(null);
    if (!action || ids.length === 0) return;

    const mutation = action === "reject" ? bulkReject : bulkHold;
    const verb = action === "reject" ? "Rejected" : "Held";
    try {
      const result = await mutation.mutateAsync({ applicationIds: ids });
      reportBulkResult(result, verb);
      setSelected(new Set());
    } catch {
      toast.error(`Couldn't ${action} the selected applications. Try again.`);
    }
  }

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
        <StatCard label="Total applications" value={total} />
        <StatCard label="New this week (this page)" value={newThisWeek} tone="success" />
        <StatCard
          label="Active (this page)"
          value={applications?.filter((a) => a.status === "Active").length ?? 0}
        />
      </div>
      <Card>
        <CardContent className="p-0">
          <div className="p-4 border-b flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by candidate or job…"
                className="pl-9 h-9"
                value={search}
                onChange={(e) => updateSearch(e.target.value)}
              />
            </div>
            {selectedEligible.length > 0 && (
              <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-1.5">
                <span className="text-xs font-medium">{selectedEligible.length} selected</span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 gap-1 text-xs"
                  onClick={() => setConfirmAction("hold")}
                >
                  <PauseCircle className="h-3.5 w-3.5" />
                  Hold
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 gap-1 text-xs text-destructive"
                  onClick={() => setConfirmAction("reject")}
                >
                  <XCircle className="h-3.5 w-3.5" />
                  Reject
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 text-xs"
                  onClick={() => setSelected(new Set())}
                >
                  Clear
                </Button>
              </div>
            )}
          </div>
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-xs uppercase text-muted-foreground tracking-wider">
              <tr>
                <th className="p-3 w-10">
                  <Checkbox
                    checked={allEligibleSelected}
                    onCheckedChange={(checked) => toggleAll(checked === true)}
                    disabled={eligibleIds.size === 0}
                    aria-label="Select all eligible applications"
                  />
                </th>
                <th className="p-3 text-left">Candidate</th>
                <th className="p-3 text-left">Job</th>
                <th className="p-3 text-left">AI Score</th>
                <th className="p-3 text-left">Stage</th>
                <th className="p-3 text-left">Status</th>
                <th className="p-3 text-left">Applied</th>
                <th className="p-3 text-right sr-only">Actions</th>
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
              {!isLoading && rows.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-6 text-center text-sm text-muted-foreground">
                    No applications found.
                  </td>
                </tr>
              )}
              {rows.map(({ application, candidate, job }) => (
                <tr key={application.id} className="hover:bg-muted/30">
                  <td className="p-3">
                    <Checkbox
                      checked={selected.has(application.id)}
                      onCheckedChange={(checked) => toggleRow(application.id, checked === true)}
                      disabled={application.status !== "Active"}
                      aria-label={`Select application for ${candidate?.full_name ?? "candidate"}`}
                    />
                  </td>
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
                    {typeof application.ai_score === "number" ? (
                      <ScorePill score={Math.round(application.ai_score)} />
                    ) : (
                      <span className="text-xs text-muted-foreground">Pending</span>
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
                  <td className="p-3 text-right">
                    <Link
                      href={`/applications/${application.id}`}
                      className="text-xs text-primary hover:underline"
                    >
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pager offset={offset} limit={PAGE_SIZE} total={total} onOffsetChange={setOffset} />
        </CardContent>
      </Card>

      <AlertDialog
        open={confirmAction !== null}
        onOpenChange={(open) => !open && setConfirmAction(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmAction === "reject" ? "Reject" : "Hold"} {selectedEligible.length} application
              {selectedEligible.length === 1 ? "" : "s"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction === "reject"
                ? "This moves every selected application to Rejected. It can be restored individually afterward."
                : "This moves every selected application to On Hold."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={runBulkAction}
              className={
                confirmAction === "reject"
                  ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  : undefined
              }
            >
              {confirmAction === "reject" ? "Reject" : "Hold"} {selectedEligible.length}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
