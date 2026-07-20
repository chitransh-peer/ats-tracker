"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell, StatCard, ScorePill } from "@/components/layout/AppShell";
import { useApplications } from "@/lib/hooks/use-applications";
import { useCandidates } from "@/lib/hooks/use-candidates";
import { useJobs } from "@/lib/hooks/use-jobs";
import {
  useAiReview,
  useEvaluateApplication,
  useEvaluation,
  useJdResumeComparison,
  useOverrideEvaluation,
} from "@/lib/hooks/use-ai";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Sparkles, CheckCircle2, AlertTriangle, XCircle, Loader2 } from "lucide-react";

const RECOMMENDATION_LABELS: Record<string, string> = {
  strong_fit: "Strong fit — proceed to interview",
  fit: "Fit — proceed to interview",
  partial_fit: "Partial fit — proceed with caution",
  not_a_fit: "Not a fit",
};

function statusChip(status: string) {
  return status === "Matched"
    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : status === "Partial"
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-red-50 text-red-700 border-red-200";
}

export function AIReviewClient() {
  const { data: applications } = useApplications();
  const { data: candidates } = useCandidates();
  const { data: jobs } = useJobs();

  const options = useMemo(() => {
    if (!applications || !candidates || !jobs) return [];
    const candidateById = new Map(candidates.map((c) => [c.id, c]));
    const jobById = new Map(jobs.map((j) => [j.id, j]));
    return applications
      .map((app) => {
        const candidate = candidateById.get(app.candidate_id);
        const job = jobById.get(app.job_id);
        if (!candidate || !job) return null;
        return {
          applicationId: app.id,
          label: `${candidate.full_name} — ${job.title}`,
        };
      })
      .filter((o): o is { applicationId: string; label: string } => o !== null);
  }, [applications, candidates, jobs]);

  const searchParams = useSearchParams();
  const applicationIdParam = searchParams.get("applicationId") ?? undefined;

  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  useEffect(() => {
    if (selectedId) return;
    if (applicationIdParam && options.some((o) => o.applicationId === applicationIdParam)) {
      setSelectedId(applicationIdParam);
    } else if (options.length > 0) {
      setSelectedId(options[0].applicationId);
    }
  }, [options, selectedId, applicationIdParam]);

  const { data: latestReview, isLoading: reviewLoading } = useAiReview(selectedId);
  const [trackedEvaluationId, setTrackedEvaluationId] = useState<string | undefined>(undefined);
  const { data: polledEvaluation } = useEvaluation(trackedEvaluationId);
  const { data: comparison } = useJdResumeComparison(selectedId);
  const evaluateMutation = useEvaluateApplication();
  const overrideMutation = useOverrideEvaluation();

  useEffect(() => {
    setTrackedEvaluationId(undefined);
  }, [selectedId]);

  const evaluation = polledEvaluation ?? latestReview ?? null;
  const isPending = evaluation?.status === "pending" || evaluation?.status === "processing";
  const isRunning = evaluateMutation.isPending || isPending;

  function handleRunAnalysis() {
    if (!selectedId) return;
    evaluateMutation.mutate(selectedId, {
      onSuccess: (created) => setTrackedEvaluationId(created.id),
    });
  }

  const overallScore = evaluation?.overall_score ?? 0;
  const matchedCount = evaluation?.matched_skills.length ?? 0;
  const missingCount = evaluation?.missing_skills.length ?? 0;
  const totalSkills = matchedCount + missingCount;
  const donut = [
    { name: "Matched", value: matchedCount },
    { name: "Missing", value: missingCount },
  ].filter((d) => d.value > 0);
  const colors = ["#10b981", "#ef4444"];

  return (
    <AppShell
      title="AI Resume Review"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "AI Review" }]}
      actions={
        <>
          <Select value={selectedId} onValueChange={setSelectedId}>
            <SelectTrigger className="h-9 w-[280px]">
              <SelectValue placeholder="Select an application" />
            </SelectTrigger>
            <SelectContent>
              {options.map((o) => (
                <SelectItem key={o.applicationId} value={o.applicationId}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button size="sm" onClick={handleRunAnalysis} disabled={!selectedId || isRunning}>
            {isRunning ? (
              <>
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                Analyzing…
              </>
            ) : evaluation ? (
              "Re-run analysis"
            ) : (
              "Run analysis"
            )}
          </Button>
        </>
      }
    >
      {!selectedId || reviewLoading ? (
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">
            {options.length === 0
              ? "No applications available yet. Create a job application first."
              : "Loading…"}
          </CardContent>
        </Card>
      ) : !evaluation ? (
        <Card>
          <CardContent className="p-8 text-center space-y-3">
            <Sparkles className="h-6 w-6 mx-auto text-primary" />
            <p className="text-sm text-muted-foreground">
              No AI evaluation has been run for this application yet.
            </p>
            <Button size="sm" onClick={handleRunAnalysis} disabled={isRunning}>
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Analyzing…
                </>
              ) : (
                "Run analysis"
              )}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
            <StatCard label="Overall match" value={`${Math.round(overallScore)}%`} tone="success" />
            <StatCard label="Matched skills" value={`${matchedCount}/${totalSkills || matchedCount}`} tone="success" />
            <StatCard label="Missing skills" value={missingCount} tone={missingCount > 0 ? "warning" : "default"} />
            <StatCard
              label="Recommendation"
              value={evaluation.recommendation_label ? evaluation.recommendation_label.replace(/_/g, " ") : "—"}
            />
            <StatCard label="Confidence" value={evaluation.confidence != null ? `${Math.round(evaluation.confidence)}%` : "—"} />
          </div>

          {evaluation.error_message && (
            <div className="mb-6 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              AI provider unavailable — showing rule-based score only. ({evaluation.error_message})
            </div>
          )}

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-6">
            <Card className="xl:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4 text-primary" />
                  AI recommendation
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="text-4xl font-semibold">
                    {Math.round(overallScore)}
                    <span className="text-sm text-muted-foreground">/100</span>
                  </div>
                  <div className="flex-1">
                    <Progress value={overallScore} className="h-2" />
                    <div className="text-xs text-muted-foreground mt-1">
                      Recommendation:{" "}
                      <span className="font-semibold text-[color:var(--color-success)]">
                        {evaluation.recommendation_label
                          ? RECOMMENDATION_LABELS[evaluation.recommendation_label] ?? evaluation.recommendation_label
                          : "Pending"}
                      </span>
                    </div>
                  </div>
                  <ScorePill score={overallScore} />
                </div>
                {evaluation.explanation_text && (
                  <p className="text-sm text-muted-foreground">{evaluation.explanation_text}</p>
                )}
                <div className="grid md:grid-cols-3 gap-3">
                  <div className="p-3 rounded-md border">
                    <div className="text-xs font-semibold text-[color:var(--color-success)] mb-1 flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Top strengths
                    </div>
                    <ul className="text-xs list-disc pl-4 space-y-0.5">
                      {evaluation.strengths.length > 0 ? (
                        evaluation.strengths.map((s) => <li key={s}>{s}</li>)
                      ) : (
                        <li className="text-muted-foreground list-none">—</li>
                      )}
                    </ul>
                  </div>
                  <div className="p-3 rounded-md border">
                    <div className="text-xs font-semibold text-amber-700 mb-1 flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      Gaps
                    </div>
                    <ul className="text-xs list-disc pl-4 space-y-0.5">
                      {evaluation.gaps.length > 0 ? (
                        evaluation.gaps.map((g) => <li key={g}>{g}</li>)
                      ) : (
                        <li className="text-muted-foreground list-none">—</li>
                      )}
                    </ul>
                  </div>
                  <div className="p-3 rounded-md border">
                    <div className="text-xs font-semibold text-destructive mb-1 flex items-center gap-1">
                      <XCircle className="h-3 w-3" />
                      Risks
                    </div>
                    <ul className="text-xs list-disc pl-4 space-y-0.5">
                      {evaluation.risk_flags.length > 0 ? (
                        evaluation.risk_flags.map((r) => <li key={r}>{r}</li>)
                      ) : (
                        <li className="text-muted-foreground list-none">—</li>
                      )}
                    </ul>
                  </div>
                </div>
                {evaluation.suggested_interview_questions.length > 0 && (
                  <div className="p-3 rounded-md bg-muted/50">
                    <div className="text-xs font-semibold mb-1">Suggested interview questions</div>
                    <ul className="text-xs list-disc pl-4 space-y-0.5">
                      {evaluation.suggested_interview_questions.map((q) => (
                        <li key={q}>{q}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="flex gap-2 pt-1">
                  {(["strong_fit", "fit", "partial_fit", "not_a_fit"] as const)
                    .filter((label) => label !== evaluation.recommendation_label)
                    .map((label) => (
                      <Button
                        key={label}
                        size="sm"
                        variant="outline"
                        className="text-xs h-7"
                        disabled={overrideMutation.isPending || evaluation.status !== "completed"}
                        onClick={() =>
                          overrideMutation.mutate({ evaluationId: evaluation.id, recommendationLabel: label })
                        }
                      >
                        Mark as {label.replace(/_/g, " ")}
                      </Button>
                    ))}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Match visualization</CardTitle>
              </CardHeader>
              <CardContent>
                {donut.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={donut} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80}>
                        {donut.map((_, i) => (
                          <Cell key={i} fill={colors[i]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[200px] grid place-items-center text-sm text-muted-foreground">
                    No skill data yet
                  </div>
                )}
                <div className="flex justify-around text-xs mt-2">
                  {donut.map((d, i) => (
                    <div key={d.name} className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full" style={{ background: colors[i] }} />
                      {d.name}: {d.value}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="comparison">
            <TabsList>
              <TabsTrigger value="comparison">JD vs Resume</TabsTrigger>
              <TabsTrigger value="capabilities">AI capabilities</TabsTrigger>
            </TabsList>

            <TabsContent value="comparison" className="mt-4 space-y-4">
              {comparison ? (
                <>
                  <div className="grid md:grid-cols-2 gap-4">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base">
                          Job requirements — {comparison.job_requirements.title}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="text-sm space-y-2">
                        <div>
                          <span className="text-muted-foreground text-xs">Must-have skills</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {comparison.job_requirements.required_skills.map((s) => (
                              <Badge key={s} variant="secondary">
                                {s}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground text-xs">Experience</span>
                          <div className="font-medium">{comparison.job_requirements.experience ?? "—"}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground text-xs">Education</span>
                          <div className="font-medium">{comparison.job_requirements.education ?? "—"}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground text-xs">Location</span>
                          <div className="font-medium">{comparison.job_requirements.location ?? "—"}</div>
                        </div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base">
                          Candidate data — {comparison.candidate_profile.full_name}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="text-sm space-y-2">
                        <div>
                          <span className="text-muted-foreground text-xs">Skills</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {comparison.candidate_profile.skills.map((s) => (
                              <Badge key={s} variant="outline">
                                {s}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground text-xs">Experience</span>
                          <div className="font-medium">
                            {comparison.candidate_profile.total_experience_years ?? "—"} years
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground text-xs">Location</span>
                          <div className="font-medium">{comparison.candidate_profile.location ?? "—"}</div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Weighted comparison</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <table className="w-full text-sm">
                        <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
                          <tr>
                            <th className="p-3 text-left">Type</th>
                            <th className="p-3 text-left">Requirement</th>
                            <th className="p-3 text-right">Weight</th>
                            <th className="p-3 text-left">Candidate</th>
                            <th className="p-3 text-left">Status</th>
                            <th className="p-3 text-right">Score</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {comparison.criteria.map((c, i) => (
                            <tr key={i} className="hover:bg-muted/30">
                              <td className="p-3 text-xs">
                                <Badge variant="outline" className="text-[10px]">
                                  {c.type}
                                </Badge>
                              </td>
                              <td className="p-3">{c.requirement}</td>
                              <td className="p-3 text-right text-xs">{c.weight}</td>
                              <td className="p-3 text-xs text-muted-foreground">{c.candidate_value}</td>
                              <td className="p-3">
                                <span
                                  className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${statusChip(c.status)}`}
                                >
                                  {c.status}
                                </span>
                              </td>
                              <td className="p-3 text-right font-medium">{c.score}</td>
                            </tr>
                          ))}
                          <tr className="bg-muted/30 font-semibold">
                            <td className="p-3" colSpan={5}>
                              Total match score
                            </td>
                            <td className="p-3 text-right">{comparison.total_score}</td>
                          </tr>
                        </tbody>
                      </table>
                    </CardContent>
                  </Card>
                </>
              ) : (
                <Card>
                  <CardContent className="p-8 text-center text-sm text-muted-foreground">Loading…</CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="capabilities" className="mt-4 grid md:grid-cols-3 gap-3">
              {[
                ["Resume parsing", "Extract structured data from PDF/DOCX resumes."],
                ["Resume scoring", "Score candidates against a job with weighted criteria."],
                ["JD vs Resume", "Side-by-side matching with match/partial/missing chips."],
                ["Interview assistant", "Suggest questions and probe areas based on gaps."],
                ["Recruiter override", "Override the AI recommendation with a full audit trail."],
              ].map(([t, d]) => (
                <Card key={t}>
                  <CardHeader className="pb-1">
                    <CardTitle className="text-sm flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 text-primary" />
                      {t}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-xs text-muted-foreground">{d}</CardContent>
                </Card>
              ))}
            </TabsContent>
          </Tabs>
        </>
      )}
    </AppShell>
  );
}
