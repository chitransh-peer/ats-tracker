"use client";

import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { useStages } from "@/lib/hooks/use-pipeline";
import { useApplications, useMoveApplicationStage } from "@/lib/hooks/use-applications";
import { useCandidates } from "@/lib/hooks/use-candidates";
import { useJobs } from "@/lib/hooks/use-jobs";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { initialsOf, relativeTime } from "@/lib/utils";

export function PipelineClient() {
  const { data: stageTemplate, isLoading: stagesLoading } = useStages();
  const { data: applications, isLoading: appsLoading } = useApplications();
  const { data: candidates } = useCandidates();
  const { data: jobs } = useJobs();
  const moveStage = useMoveApplicationStage();

  const isLoading = stagesLoading || appsLoading;
  const stages = stageTemplate?.stages ?? [];
  const candidateById = new Map((candidates ?? []).map((c) => [c.id, c]));
  const jobById = new Map((jobs ?? []).map((j) => [j.id, j]));

  const visibleApplications = (applications ?? []).filter(
    (a) => a.status === "Active" || a.status === "Hired",
  );

  const byStage = stages.map((stage) => ({
    stage,
    items: visibleApplications.filter((a) => a.current_stage_id === stage.id),
  }));

  const atInterview = visibleApplications.filter((a) => {
    const stageName = stages.find((s) => s.id === a.current_stage_id)?.name ?? "";
    return stageName.includes("Interview");
  }).length;
  const atOffer = visibleApplications.filter((a) => {
    const stageName = stages.find((s) => s.id === a.current_stage_id)?.name ?? "";
    return stageName.startsWith("Offer");
  }).length;
  const hired = visibleApplications.filter((a) => a.status === "Hired").length;

  return (
    <AppShell
      title="Hiring pipeline"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Pipeline" }]}
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="In pipeline" value={visibleApplications.length} />
        <StatCard label="At interview" value={atInterview} />
        <StatCard label="At offer" value={atOffer} />
        <StatCard label="Hired" value={hired} tone="success" />
      </div>

      {isLoading && <div className="text-sm text-muted-foreground">Loading pipeline…</div>}

      {!isLoading && (
        <div className="overflow-x-auto -mx-4 lg:-mx-8 px-4 lg:px-8">
          <div className="flex gap-3 min-w-max pb-4">
            {byStage.map(({ stage, items }) => (
              <div key={stage.id} className="w-72 shrink-0">
                <div className="flex items-center justify-between mb-2 px-1">
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {stage.name}
                  </div>
                  <Badge variant="secondary" className="text-[10px]">
                    {items.length}
                  </Badge>
                </div>
                <div className="space-y-2 min-h-[120px] rounded-lg bg-muted/40 p-2">
                  {items.map((application) => {
                    const candidate = candidateById.get(application.candidate_id);
                    const job = jobById.get(application.job_id);
                    return (
                      <Card key={application.id}>
                        <CardContent className="p-3">
                          <div className="flex items-start gap-2">
                            <Avatar className="h-8 w-8">
                              <AvatarFallback className="text-[10px]">
                                {candidate ? initialsOf(candidate.full_name) : "?"}
                              </AvatarFallback>
                            </Avatar>
                            <div className="min-w-0 flex-1">
                              {candidate ? (
                                <Link
                                  href={`/candidates/${candidate.id}`}
                                  className="text-sm font-medium hover:underline truncate block"
                                >
                                  {candidate.full_name}
                                </Link>
                              ) : (
                                <span className="text-sm text-muted-foreground">Unknown</span>
                              )}
                              <div className="text-[11px] text-muted-foreground truncate">
                                {job?.title}
                              </div>
                              <div className="mt-2">
                                <Select
                                  value={stage.id}
                                  onValueChange={(toStageId) =>
                                    moveStage.mutate({ applicationId: application.id, toStageId })
                                  }
                                >
                                  <SelectTrigger className="h-7 text-[11px]">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {stages.map((s) => (
                                      <SelectItem key={s.id} value={s.id} className="text-xs">
                                        {s.name}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                              <div className="mt-1 text-[10px] text-muted-foreground">
                                Applied {relativeTime(application.applied_at)}
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                  {items.length === 0 && (
                    <div className="text-center text-[11px] text-muted-foreground py-4">
                      No candidates
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </AppShell>
  );
}
