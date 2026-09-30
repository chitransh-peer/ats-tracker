"use client";

import { useState } from "react";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import {
  useOnboardingActions,
  useOnboardingCasesPage,
  useOnboardingSummary,
} from "@/lib/hooks/use-onboarding";
import { Pager } from "@/components/ui/pager";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError } from "@/lib/api/client";
import type { OnboardingCase } from "@/lib/api/types";

const caseTone: Record<string, string> = {
  "In Progress": "bg-blue-100 text-blue-800",
  Completed: "bg-emerald-100 text-emerald-800",
  Cancelled: "bg-slate-200 text-slate-600",
};

const categoryTone: Record<string, string> = {
  Documentation: "bg-slate-100 text-slate-700",
  Compliance: "bg-amber-100 text-amber-800",
  Equipment: "bg-violet-100 text-violet-800",
  Provisioning: "bg-blue-100 text-blue-800",
  Orientation: "bg-teal-100 text-teal-800",
};

const TASK_CATEGORIES = ["Documentation", "Compliance", "Equipment", "Provisioning", "Orientation"];

function CaseCard({
  onboardingCase,
  candidateName,
  jobTitle,
}: {
  onboardingCase: OnboardingCase;
  candidateName: string;
  jobTitle: string;
}) {
  const actions = useOnboardingActions();
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskCategory, setNewTaskCategory] = useState("Documentation");
  const [error, setError] = useState<string | null>(null);

  const editable = onboardingCase.status === "In Progress";
  const done = onboardingCase.tasks.filter((t) => t.status === "Completed").length;
  const total = onboardingCase.tasks.length;
  const pct = total ? Math.round((done / total) * 100) : 0;
  const allDone = total > 0 && done === total;

  async function toggleTask(taskId: string, completed: boolean) {
    setError(null);
    try {
      await actions.updateTask.mutateAsync({
        taskId,
        status: completed ? "Completed" : "Pending",
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update task.");
    }
  }

  async function handleAddTask(e: React.FormEvent) {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    setError(null);
    try {
      await actions.addTask.mutateAsync({
        caseId: onboardingCase.id,
        title: newTaskTitle.trim(),
        category: newTaskCategory,
      });
      setNewTaskTitle("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add task.");
    }
  }

  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <div className="font-medium">{candidateName}</div>
            <div className="text-xs text-muted-foreground">{jobTitle}</div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={`text-[10px] ${caseTone[onboardingCase.status] ?? ""}`}>
              {onboardingCase.status}
            </Badge>
            {onboardingCase.start_date && (
              <span className="text-xs text-muted-foreground">
                Starts {onboardingCase.start_date}
              </span>
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
            <span>
              {done} / {total} tasks complete
            </span>
            <span>{pct}%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {error && <div className="text-sm text-destructive">{error}</div>}

        <ul className="divide-y rounded-md border">
          {onboardingCase.tasks.map((task) => {
            const completed = task.status === "Completed";
            return (
              <li key={task.id} className="flex items-center gap-3 p-2.5">
                <Checkbox
                  checked={completed}
                  disabled={!editable}
                  onCheckedChange={(v) => toggleTask(task.id, Boolean(v))}
                />
                <span
                  className={`flex-1 text-sm ${completed ? "line-through text-muted-foreground" : ""}`}
                >
                  {task.title}
                </span>
                {task.due_date && (
                  <span className="text-[11px] text-muted-foreground">{task.due_date}</span>
                )}
                <Badge className={`text-[10px] ${categoryTone[task.category] ?? ""}`}>
                  {task.category}
                </Badge>
              </li>
            );
          })}
        </ul>

        {editable && (
          <form onSubmit={handleAddTask} className="flex items-center gap-2">
            <Input
              value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)}
              placeholder="Add a task…"
              className="h-8 text-sm"
            />
            <Select value={newTaskCategory} onValueChange={setNewTaskCategory}>
              <SelectTrigger className="h-8 w-40 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TASK_CATEGORIES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              type="submit"
              size="sm"
              variant="secondary"
              className="h-8"
              disabled={!newTaskTitle.trim()}
            >
              Add
            </Button>
          </form>
        )}

        {editable && (
          <div className="flex items-center justify-end gap-2 pt-1">
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs"
              onClick={() => actions.cancel.mutate(onboardingCase.id)}
            >
              Cancel case
            </Button>
            <Button
              size="sm"
              className="h-7 text-xs"
              disabled={!allDone || actions.complete.isPending}
              onClick={() => actions.complete.mutate(onboardingCase.id)}
            >
              Mark hired
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

const PAGE_SIZE = 20;

export function OnboardingClient() {
  const [offset, setOffset] = useState(0);
  // Paged, named and counted by the server; see the interviews page.
  const { data, isLoading } = useOnboardingCasesPage({ limit: PAGE_SIZE, offset });
  const { data: summary } = useOnboardingSummary();
  const cases = data?.data;

  return (
    <AppShell
      title="Onboarding"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Onboarding" }]}
    >
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <StatCard label="In progress" value={summary?.in_progress ?? 0} />
        <StatCard label="Completed" value={summary?.completed ?? 0} tone="success" />
        <StatCard label="Cancelled" value={summary?.cancelled ?? 0} />
      </div>

      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {!isLoading && (cases?.length ?? 0) === 0 && (
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">
            No onboarding cases yet. A case opens automatically when an offer is accepted.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {cases?.map((c) => (
          <CaseCard
            key={c.id}
            onboardingCase={c}
            candidateName={c.candidate_name ?? "Unknown candidate"}
            jobTitle={c.job_title ?? "—"}
          />
        ))}
      </div>
      <Pager
        offset={offset}
        limit={PAGE_SIZE}
        total={data?.total ?? 0}
        onOffsetChange={setOffset}
      />
    </AppShell>
  );
}
