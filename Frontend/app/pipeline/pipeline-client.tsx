"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { EntityPicker } from "@/components/entity-picker";
import { usePipelineBoard, useStages } from "@/lib/hooks/use-pipeline";
import { useMoveApplicationStage } from "@/lib/hooks/use-applications";
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
import { Info } from "lucide-react";
import { initialsOf, relativeTime } from "@/lib/utils";

export function PipelineClient() {
  const [jobId, setJobId] = useState<string | null>(null);
  const { data: stageTemplate, isLoading: stagesLoading } = useStages();
  // Counts come from the server and are exact; the cards stop at the board's
  // limit (2,000). Before, the page fetched a capped list and counted that,
  // so past 2,000 applications it quietly under-counted and dropped cards.
  const { data: board, isLoading: boardLoading } = usePipelineBoard(jobId);
  const moveStage = useMoveApplicationStage();

  const isLoading = stagesLoading || boardLoading;
  const stages = stageTemplate?.stages ?? [];
  const countByStage = new Map((board?.stage_counts ?? []).map((s) => [s.stage_id, s.count]));
  const cards = board?.cards ?? [];
  const total = board?.total ?? 0;
  const truncated = cards.length < total;

  const byStage = stages.map((stage) => ({
    stage,
    count: countByStage.get(stage.id) ?? 0,
    items: cards.filter((a) => a.current_stage_id === stage.id),
  }));
  const sumWhere = (match: (name: string) => boolean) =>
    byStage.filter(({ stage }) => match(stage.name)).reduce((sum, { count }) => sum + count, 0);
  const atInterview = sumWhere((name) => name.includes("Interview"));
  const atOffer = sumWhere((name) => name.startsWith("Offer"));

  return (
    <AppShell
      title="Hiring pipeline"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Pipeline" }]}
      actions={
        <div className="w-72">
          <EntityPicker kind="jobs" value={jobId} onChange={setJobId} placeholder="All jobs" />
        </div>
      }
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="In pipeline" value={total} />
        <StatCard label="At interview" value={atInterview} />
        <StatCard label="At offer" value={atOffer} />
        <StatCard label="Hired" value={board?.hired ?? 0} tone="success" />
      </div>

      {truncated && (
        <div className="mb-4 flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <Info className="h-4 w-4 mt-0.5 shrink-0" />
          <span>
            Showing the newest {cards.length.toLocaleString()} of {total.toLocaleString()}{" "}
            applications. Column counts include all of them.
            {jobId ? "" : " Pick a job above to see every card for that job."}
          </span>
        </div>
      )}

      {isLoading && <div className="text-sm text-muted-foreground">Loading pipeline…</div>}

      {!isLoading && (
        <div className="overflow-x-auto -mx-4 lg:-mx-8 px-4 lg:px-8">
          <div className="flex gap-3 min-w-max pb-4">
            {byStage.map(({ stage, count, items }) => (
              <div key={stage.id} className="w-72 shrink-0">
                <div className="flex items-center justify-between mb-2 px-1">
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {stage.name}
                  </div>
                  <Badge variant="secondary" className="text-[10px]">
                    {count.toLocaleString()}
                  </Badge>
                </div>
                <div className="space-y-2 min-h-[120px] rounded-lg bg-muted/40 p-2">
                  {items.map((application) => (
                    <Card key={application.id}>
                      <CardContent className="p-3">
                        <div className="flex items-start gap-2">
                          <Avatar className="h-8 w-8">
                            <AvatarFallback className="text-[10px]">
                              {application.candidate_name
                                ? initialsOf(application.candidate_name)
                                : "?"}
                            </AvatarFallback>
                          </Avatar>
                          <div className="min-w-0 flex-1">
                            {application.candidate_name ? (
                              <Link
                                href={`/candidates/${application.candidate_id}`}
                                className="text-sm font-medium hover:underline truncate block"
                              >
                                {application.candidate_name}
                              </Link>
                            ) : (
                              <span className="text-sm text-muted-foreground">Unknown</span>
                            )}
                            <div className="text-[11px] text-muted-foreground truncate">
                              {application.job_title}
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
                  ))}
                  {count === 0 && (
                    <div className="text-center text-[11px] text-muted-foreground py-4">
                      No candidates
                    </div>
                  )}
                  {count > items.length && (
                    <div className="text-center text-[11px] text-muted-foreground py-2">
                      +{(count - items.length).toLocaleString()} more not shown
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
