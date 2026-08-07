"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useAddJobNote,
  useJob,
  useJobDocuments,
  useJobNotes,
  useJobSubmissions,
  useSaveJobSearchCriteria,
  useSetJobCustomField,
} from "@/lib/hooks/use-jobs";
import {
  DEGREE_OPTIONS,
  JOB_NOTE_ACTIONS,
  JOB_NOTE_TYPES,
  RADIUS_OPTIONS,
  WORK_AUTHORIZATIONS,
} from "@/lib/api/jobs";
import { COUNTRIES } from "@/lib/api/clients";
import type { JobSearchCriteriaInput } from "@/lib/api/types";
import { Briefcase, MapPin, Plus, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleString(undefined, {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function statusTone(status: string) {
  if (status === "Active") return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (status === "Draft") return "bg-slate-50 text-slate-700 border-slate-200";
  if (status === "On Hold") return "bg-amber-50 text-amber-700 border-amber-200";
  return "bg-rose-50 text-rose-700 border-rose-200";
}

function rate(
  min: string | number | null,
  max: string | number | null,
  currency: string,
  unit: string,
  type: string | null,
) {
  if (min == null && max == null) return "N/A";
  const amount =
    min != null && max != null && String(min) !== String(max) ? `${min} - ${max}` : `${min ?? max}`;
  return [`${currency} ${amount}`, unit, type].filter(Boolean).join("/");
}

/** A labelled cell in the header info strip. */
function HeaderStat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="px-4 py-2 min-w-0">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-sm font-medium truncate">{value || "N/A"}</div>
    </div>
  );
}

/** The horizontal stage tracker under each submission row. */
function StageProgress({
  stages,
  currentIndex,
  submittedAt,
}: {
  stages: string[];
  currentIndex: number;
  submittedAt: string | null;
}) {
  return (
    <div className="mt-3">
      <div className="relative flex items-center justify-between">
        <div className="absolute left-0 right-0 top-1.5 h-0.5 bg-border" />
        <div
          className="absolute left-0 top-1.5 h-0.5 bg-emerald-500 transition-all"
          style={{
            width: stages.length > 1 ? `${(currentIndex / (stages.length - 1)) * 100}%` : "0%",
          }}
        />
        {stages.map((stage, i) => (
          <div key={stage} className="relative z-10 flex flex-col items-center gap-1 flex-1">
            <span
              className={cn(
                "h-3 w-3 rounded-full border-2 bg-background",
                i <= currentIndex ? "border-emerald-500 bg-emerald-500" : "border-border",
              )}
            />
            <span className="text-[10px] text-muted-foreground text-center leading-tight">
              {stage}
            </span>
            {i === currentIndex && submittedAt && (
              <span className="text-[9px] text-muted-foreground">
                {formatDateTime(submittedAt)}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyRow({ colSpan, label = "No data available" }: { colSpan: number; label?: string }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-4 py-4 text-muted-foreground text-sm">
        {label}
      </td>
    </tr>
  );
}

export function JobDetailClient() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;

  const { data: job, isLoading } = useJob(jobId);
  const { data: submissions } = useJobSubmissions(jobId);
  const { data: notes } = useJobNotes(jobId);
  const { data: documents } = useJobDocuments(jobId);
  const addNote = useAddJobNote(jobId);
  const saveCriteria = useSaveJobSearchCriteria(jobId);
  const setCustomField = useSetJobCustomField(jobId);

  const [noteBody, setNoteBody] = useState("");
  const [noteType, setNoteType] = useState<string>("Job Posting");
  const [noteAction, setNoteAction] = useState<string>("General");
  const [noteFilter, setNoteFilter] = useState<string>("Job Posting");
  const [stageFilter, setStageFilter] = useState<string>("All");
  const [customField, setCustomFieldDraft] = useState({ field_name: "", field_value: "" });
  const [criteria, setCriteria] = useState<JobSearchCriteriaInput | null>(null);

  // Seed the search-criteria panel once the job loads, defaulting to the job's own location.
  useEffect(() => {
    if (!job || criteria) return;
    setCriteria(
      job.search_criteria
        ? { ...job.search_criteria }
        : {
            boolean_string: null,
            job_title: job.title,
            recent_job_title_only: false,
            search_mode: "radius",
            country: job.country,
            state: job.states[0] ?? null,
            city: job.city,
            postal_code: job.postal_code,
            radius_miles: null,
            search_radius_within_state: false,
            include_applicants_without_country: false,
            experience_min_years: job.experience_min_years,
            experience_max_years: job.experience_max_years,
            education: [],
            work_authorizations: job.work_authorizations,
            employer: null,
            most_recent_employer_only: false,
            willing_to_relocate: null,
            clearance: job.clearance_required ? true : null,
          },
    );
  }, [job, criteria]);

  if (isLoading) {
    return (
      <AppShell title="Job">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </AppShell>
    );
  }

  if (!job) {
    return (
      <AppShell title="Job not found">
        <div className="text-sm text-muted-foreground">
          This job doesn&apos;t exist or you don&apos;t have access.{" "}
          <Link href="/jobs" className="text-primary hover:underline">
            Back to jobs
          </Link>
        </div>
      </AppShell>
    );
  }

  const stages = submissions?.stages ?? [];
  const allRows = submissions?.submissions ?? [];
  const rows =
    stageFilter === "All" ? allRows : allRows.filter((r) => r.current_stage_name === stageFilter);
  const visibleNotes = (notes ?? []).filter((n) => n.note_type === noteFilter);
  const location = [job.location, job.city, job.states.join(", "), job.country]
    .filter(Boolean)
    .join(", ");

  function setCriteriaField<K extends keyof JobSearchCriteriaInput>(
    key: K,
    value: JobSearchCriteriaInput[K],
  ) {
    setCriteria((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!noteBody.trim()) return;
    await addNote.mutateAsync({
      body: noteBody.trim(),
      note_type: noteType,
      action: noteAction,
    });
    setNoteBody("");
  }

  return (
    <AppShell
      title={job.title}
      breadcrumbs={[
        { label: "Home", to: "/" },
        { label: "Jobs", to: "/jobs" },
        { label: job.req_id },
      ]}
      actions={
        <Button size="sm" variant="outline" asChild>
          <Link href={`/jobs/${job.id}/edit`}>Edit Job</Link>
        </Button>
      }
    >
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-6 items-start">
        {/* ---------- Main column ---------- */}
        <div className="space-y-6 min-w-0">
          <Card>
            <CardContent className="p-5 space-y-4">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Briefcase className="h-4 w-4 text-primary shrink-0" />
                    <h2 className="text-lg font-semibold">
                      <span className="font-mono text-muted-foreground">{job.req_id}</span> —{" "}
                      {job.title}
                    </h2>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-muted-foreground">
                    <span>{job.client_name ?? "N/A"}</span>
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {location || "N/A"}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    Assigned To —{" "}
                    {job.assigned_to_names.length ? job.assigned_to_names.join(", ") : "N/A"}
                  </div>
                  <div className="flex flex-wrap gap-2 mt-4">
                    <Button size="sm" variant="outline" asChild>
                      <Link href={`/jobs/${job.id}/edit`}>Edit Job</Link>
                    </Button>
                    <Button size="sm" variant="outline" className="gap-1" asChild>
                      <Link href={`/candidates?job=${job.id}`}>
                        <Sparkles className="h-4 w-4" />
                        Recommended Matches
                      </Link>
                    </Button>
                    <Badge variant="secondary" className="self-center text-[11px]">
                      Matching applicants {job.applications_count}
                    </Badge>
                  </div>
                </div>
                <span
                  className={cn(
                    "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium",
                    statusTone(job.status),
                  )}
                >
                  {job.status}
                </span>
              </div>

              <div className="grid sm:grid-cols-2 lg:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x border rounded-md">
                <HeaderStat label="Recruitment Manager" value={job.recruitment_manager_name} />
                <HeaderStat
                  label="Client Bill Rate / Salary"
                  value={rate(
                    job.client_bill_rate_min,
                    job.client_bill_rate_max,
                    job.client_bill_rate_currency,
                    job.client_bill_rate_unit,
                    job.client_bill_rate_type,
                  )}
                />
                <HeaderStat
                  label="Pay Rate / Salary"
                  value={rate(
                    job.pay_min,
                    job.pay_max,
                    job.pay_rate_currency,
                    job.pay_rate_unit,
                    job.pay_rate_type,
                  )}
                />
                <HeaderStat
                  label="Created By & On"
                  value={
                    <span>
                      {job.created_by_name ?? "N/A"}
                      <br />
                      <span className="text-xs text-muted-foreground">
                        {formatDateTime(job.created_at)}
                      </span>
                    </span>
                  }
                />
                <HeaderStat label="Business Unit" value={job.business_unit} />
              </div>
            </CardContent>
          </Card>

          {/* Tabbed sections */}
          <Tabs defaultValue="snapshot">
            <TabsList>
              <TabsTrigger value="snapshot">Snapshot</TabsTrigger>
              <TabsTrigger value="details">Job Details</TabsTrigger>
              <TabsTrigger value="additional">Additional Details</TabsTrigger>
            </TabsList>

            {/* --- Snapshot: description, submissions, notes, documents --- */}
            <TabsContent value="snapshot" className="space-y-6 mt-4">
              <Card>
                <CardHeader className="py-4">
                  <CardTitle className="text-base">Job Description</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  {job.summary && <p className="text-muted-foreground">{job.summary}</p>}
                  {job.description ? (
                    <p className="whitespace-pre-wrap">{job.description}</p>
                  ) : (
                    <p className="text-muted-foreground">No description added.</p>
                  )}
                  {job.responsibilities.length > 0 && (
                    <ul className="list-disc pl-5 space-y-1">
                      {job.responsibilities.map((r) => (
                        <li key={r}>{r}</li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="py-4 space-y-3">
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <CardTitle className="text-base">Submissions</CardTitle>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <Button
                      size="sm"
                      variant={stageFilter === "All" ? "default" : "outline"}
                      className="h-7 text-[11px] gap-1"
                      onClick={() => setStageFilter("All")}
                    >
                      All
                      <Badge variant="secondary" className="text-[10px] px-1">
                        {allRows.length}
                      </Badge>
                    </Button>
                    {stages.map((stage) => (
                      <Button
                        key={stage}
                        size="sm"
                        variant={stageFilter === stage ? "default" : "outline"}
                        className="h-7 text-[11px] gap-1"
                        onClick={() => setStageFilter(stage)}
                      >
                        {stage}
                        <Badge variant="secondary" className="text-[10px] px-1">
                          {submissions?.counts[stage] ?? 0}
                        </Badge>
                      </Button>
                    ))}
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="text-[11px] uppercase tracking-wide text-muted-foreground">
                        <tr className="border-b">
                          <th className="px-4 py-2.5 text-left font-medium">Name</th>
                          <th className="px-4 py-2.5 text-left font-medium">Submitted by / on</th>
                          <th className="px-4 py-2.5 text-left font-medium">Contact / Location</th>
                          <th className="px-4 py-2.5 text-left font-medium">
                            Pay rate / Work auth
                          </th>
                          <th className="px-4 py-2.5 text-left font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.length === 0 ? (
                          <EmptyRow colSpan={5} />
                        ) : (
                          rows.map((s) => (
                            <tr key={s.application_id} className="border-b last:border-0">
                              <td colSpan={5} className="px-4 py-3">
                                <div className="grid md:grid-cols-5 gap-3">
                                  <Link
                                    href={`/candidates/${s.candidate_id}`}
                                    className="text-primary hover:underline font-medium"
                                  >
                                    {s.candidate_name}
                                  </Link>
                                  <div>
                                    <div>{s.submitted_by_name ?? "—"}</div>
                                    <div className="text-xs text-muted-foreground">
                                      {formatDateTime(s.submitted_at)}
                                    </div>
                                  </div>
                                  <div>
                                    <div>{s.candidate_phone ?? "—"}</div>
                                    <div className="text-xs text-muted-foreground">
                                      {s.candidate_location ?? "—"}
                                    </div>
                                  </div>
                                  <div>
                                    <div>{s.pay_expectation ? `${s.pay_expectation}` : "—"}</div>
                                    <div className="text-xs text-muted-foreground">
                                      {s.work_auth ?? "—"}
                                    </div>
                                  </div>
                                  <div>
                                    <Badge variant="outline" className="text-[11px]">
                                      {s.current_stage_name ?? s.status}
                                    </Badge>
                                  </div>
                                </div>
                                <StageProgress
                                  stages={stages}
                                  currentIndex={s.stage_index}
                                  submittedAt={s.submitted_at}
                                />
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                    <div className="px-4 py-2 text-xs text-muted-foreground">
                      Showing {rows.length === 0 ? 0 : 1} to {rows.length} of {rows.length} entries
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between gap-3 py-4">
                  <CardTitle className="text-base">Notes</CardTitle>
                  <div className="flex items-center gap-1">
                    {JOB_NOTE_TYPES.map((t) => (
                      <Button
                        key={t}
                        size="sm"
                        variant={noteFilter === t ? "default" : "outline"}
                        className="h-7 text-[11px] gap-1"
                        onClick={() => setNoteFilter(t)}
                      >
                        {t}
                        <Badge variant="secondary" className="text-[10px] px-1">
                          {(notes ?? []).filter((n) => n.note_type === t).length}
                        </Badge>
                      </Button>
                    ))}
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <form onSubmit={handleAddNote} className="p-4 border-b space-y-2">
                    <Textarea
                      rows={2}
                      placeholder="Add a note…"
                      value={noteBody}
                      onChange={(e) => setNoteBody(e.target.value)}
                    />
                    <div className="flex flex-wrap items-center gap-2">
                      <Select value={noteType} onValueChange={setNoteType}>
                        <SelectTrigger className="h-8 w-[180px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {JOB_NOTE_TYPES.map((t) => (
                            <SelectItem key={t} value={t}>
                              {t}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select value={noteAction} onValueChange={setNoteAction}>
                        <SelectTrigger className="h-8 w-[150px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {JOB_NOTE_ACTIONS.map((a) => (
                            <SelectItem key={a} value={a}>
                              {a}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        type="submit"
                        size="sm"
                        disabled={addNote.isPending || !noteBody.trim()}
                      >
                        Add note
                      </Button>
                    </div>
                  </form>
                  <table className="w-full text-sm">
                    <thead className="text-[11px] uppercase tracking-wide text-muted-foreground">
                      <tr className="border-b">
                        <th className="px-4 py-2.5 text-left font-medium">Added by / on</th>
                        <th className="px-4 py-2.5 text-left font-medium">Notes / Description</th>
                        <th className="px-4 py-2.5 text-left font-medium">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleNotes.length === 0 ? (
                        <EmptyRow colSpan={3} />
                      ) : (
                        visibleNotes.map((n) => (
                          <tr key={n.id} className="border-b last:border-0">
                            <td className="px-4 py-2.5 align-top">
                              <div className="font-medium">{n.author_name ?? "—"}</div>
                              <div className="text-xs text-muted-foreground">
                                {formatDateTime(n.created_at)}
                              </div>
                            </td>
                            <td className="px-4 py-2.5 align-top whitespace-pre-wrap">{n.body}</td>
                            <td className="px-4 py-2.5 align-top">
                              <Badge variant="outline" className="text-[11px]">
                                {n.action ?? "—"}
                              </Badge>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="py-4">
                  <CardTitle className="text-base">Documents</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <table className="w-full text-sm">
                    <thead className="text-[11px] uppercase tracking-wide text-muted-foreground">
                      <tr className="border-b">
                        <th className="px-4 py-2.5 text-left font-medium">File name</th>
                        <th className="px-4 py-2.5 text-left font-medium">Type</th>
                        <th className="px-4 py-2.5 text-left font-medium">Size</th>
                        <th className="px-4 py-2.5 text-left font-medium">Uploaded on</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(documents ?? []).length === 0 ? (
                        <EmptyRow colSpan={4} />
                      ) : (
                        (documents ?? []).map((d) => (
                          <tr key={d.id} className="border-b last:border-0">
                            <td className="px-4 py-2.5">{d.file_name}</td>
                            <td className="px-4 py-2.5 text-muted-foreground">{d.content_type}</td>
                            <td className="px-4 py-2.5 text-muted-foreground">
                              {Math.round(d.size_bytes / 1024)} KB
                            </td>
                            <td className="px-4 py-2.5 text-muted-foreground">
                              {formatDateTime(d.created_at)}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </TabsContent>

            {/* --- Job Details --- */}
            <TabsContent value="details" className="mt-4">
              <Card>
                <CardContent className="p-5 grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                  {(
                    [
                      ["Job Code", job.req_id],
                      ["Facility", job.facility],
                      ["Client", job.client_name],
                      ["End Client", job.end_client],
                      ["Job Type", job.employment_type],
                      ["Remote Job", job.workplace],
                      ["Job Status", job.status],
                      ["Priority", job.priority],
                      ["Duration", job.duration],
                      ["Required Hours/Week", job.required_hours_per_week],
                      ["Respond By", job.respond_by],
                      [
                        "Turnaround Time",
                        job.turnaround_time_value
                          ? `${job.turnaround_time_value} ${job.turnaround_time_unit ?? ""}`
                          : null,
                      ],
                      ["Interview Mode", job.interview_mode],
                      ["Clearance", job.clearance_required ? "Yes" : "No"],
                      ["Employment Level", job.employment_level],
                      ["Employment Test Template", job.employment_test_template],
                      ["Work Authorization", job.work_authorizations.join(", ")],
                      ["Required Documents", job.required_documents.join(", ")],
                      ["Degree", job.education],
                      [
                        "Experience",
                        job.experience_min_years != null || job.experience_max_years != null
                          ? `${job.experience_min_years ?? 0} – ${job.experience_max_years ?? "+"} years`
                          : null,
                      ],
                      ["Primary Skills", job.required_skills.join(", ")],
                      ["Secondary Skills", job.nice_to_have.join(", ")],
                      ["Address", job.address],
                      ["States", job.states.join(", ")],
                      ["Country", job.country],
                    ] as [string, React.ReactNode][]
                  ).map(([label, value]) => (
                    <div key={label} className="space-y-0.5">
                      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                        {label}
                      </div>
                      <div className="font-medium break-words">{value || "N/A"}</div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>

            {/* --- Additional Details: organizational info + user-defined fields --- */}
            <TabsContent value="additional" className="space-y-6 mt-4">
              <Card>
                <CardHeader className="py-4">
                  <CardTitle className="text-base">Organizational Information</CardTitle>
                </CardHeader>
                <CardContent className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                  {(
                    [
                      ["Number of Positions", job.openings],
                      ["Maximum Allowed Submissions", job.max_allowed_submissions],
                      ["Tax Terms", job.tax_terms.join(", ")],
                      ["Sales Manager", job.sales_manager_name],
                      ["Recruitment Manager", job.recruitment_manager_name],
                      ["Account Manager", job.account_manager_name],
                      ["Primary Recruiter", job.primary_recruiter_name],
                      ["Assigned To", job.assigned_to_names.join(", ")],
                      ["Comments", job.comments],
                      [
                        "Modified By & On",
                        `${job.updated_by_name ?? "N/A"} · ${formatDateTime(job.updated_at)}`,
                      ],
                    ] as [string, React.ReactNode][]
                  ).map(([label, value]) => (
                    <div key={label} className="space-y-0.5">
                      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                        {label}
                      </div>
                      <div className="font-medium break-words">{value || "N/A"}</div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="py-4">
                  <CardTitle className="text-base">User Defined Fields</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid md:grid-cols-[1fr_1fr_auto] gap-2">
                    <Input
                      placeholder="Field name"
                      value={customField.field_name}
                      onChange={(e) =>
                        setCustomFieldDraft({ ...customField, field_name: e.target.value })
                      }
                    />
                    <Input
                      placeholder="Value"
                      value={customField.field_value}
                      onChange={(e) =>
                        setCustomFieldDraft({ ...customField, field_value: e.target.value })
                      }
                    />
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="gap-1"
                      disabled={!customField.field_name.trim() || setCustomField.isPending}
                      onClick={async () => {
                        await setCustomField.mutateAsync(customField);
                        setCustomFieldDraft({ field_name: "", field_value: "" });
                      }}
                    >
                      <Plus className="h-4 w-4" />
                      Save field
                    </Button>
                  </div>
                  {job.custom_fields.length > 0 ? (
                    <div className="rounded-md border divide-y">
                      {job.custom_fields.map((f) => (
                        <div key={f.id} className="flex gap-3 px-3 py-2 text-sm">
                          <span className="font-medium min-w-[180px]">{f.field_name}</span>
                          <span className="text-muted-foreground">{f.field_value ?? "—"}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No user-defined fields yet.</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* ---------- Search Criteria rail ---------- */}
        <Card className="xl:sticky xl:top-4">
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <CardTitle className="text-base">Search Criteria</CardTitle>
            <Button
              size="sm"
              disabled={!criteria || saveCriteria.isPending}
              onClick={() => criteria && saveCriteria.mutateAsync(criteria)}
            >
              Save
            </Button>
          </CardHeader>
          <CardContent className="space-y-4 max-h-[75vh] overflow-y-auto">
            {criteria && (
              <>
                <div className="space-y-1.5">
                  <Label className="text-xs">Boolean string</Label>
                  <Textarea
                    rows={5}
                    className="font-mono text-xs"
                    value={criteria.boolean_string ?? ""}
                    onChange={(e) => setCriteriaField("boolean_string", e.target.value || null)}
                    placeholder='("PROJECT MANAGEMENT") AND ("AGILE") AND ("AZURE DEVOPS")'
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Job title</Label>
                  <Input
                    value={criteria.job_title ?? ""}
                    onChange={(e) => setCriteriaField("job_title", e.target.value || null)}
                  />
                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Checkbox
                      checked={criteria.recent_job_title_only}
                      onCheckedChange={(v) => setCriteriaField("recent_job_title_only", Boolean(v))}
                    />
                    Recent job title only
                  </label>
                </div>

                <div className="space-y-2 border-t pt-3">
                  <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    Location details
                  </div>
                  <div className="flex gap-3 text-xs">
                    {[
                      { value: "radius", label: "Search within radius" },
                      { value: "locations", label: "Selected locations" },
                    ].map((mode) => (
                      <label key={mode.value} className="flex items-center gap-1.5">
                        <input
                          type="radio"
                          checked={criteria.search_mode === mode.value}
                          onChange={() => setCriteriaField("search_mode", mode.value)}
                        />
                        {mode.label}
                      </label>
                    ))}
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs">Country</Label>
                    <Select
                      value={criteria.country ?? "United States"}
                      onValueChange={(v) => setCriteriaField("country", v)}
                    >
                      <SelectTrigger className="h-9">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {COUNTRIES.map((c) => (
                          <SelectItem key={c} value={c}>
                            {c}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {criteria.search_mode === "radius" ? (
                    <div className="grid grid-cols-2 gap-2">
                      <div className="space-y-1.5">
                        <Label className="text-xs">City / Zip code</Label>
                        <Input
                          value={criteria.postal_code ?? ""}
                          onChange={(e) => setCriteriaField("postal_code", e.target.value || null)}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-xs">Radius</Label>
                        <Select
                          value={criteria.radius_miles ? String(criteria.radius_miles) : "any"}
                          onValueChange={(v) =>
                            setCriteriaField("radius_miles", v === "any" ? null : Number(v))
                          }
                        >
                          <SelectTrigger className="h-9">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="any">Select radius</SelectItem>
                            {RADIUS_OPTIONS.map((r) => (
                              <SelectItem key={r} value={String(r)}>
                                {r} miles
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <label className="col-span-2 flex items-center gap-2 text-xs text-muted-foreground">
                        <Checkbox
                          checked={criteria.search_radius_within_state}
                          onCheckedChange={(v) =>
                            setCriteriaField("search_radius_within_state", Boolean(v))
                          }
                        />
                        Search radius within the state
                      </label>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-2">
                      <div className="space-y-1.5">
                        <Label className="text-xs">State</Label>
                        <Input
                          value={criteria.state ?? ""}
                          onChange={(e) => setCriteriaField("state", e.target.value || null)}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-xs">City</Label>
                        <Input
                          value={criteria.city ?? ""}
                          onChange={(e) => setCriteriaField("city", e.target.value || null)}
                        />
                      </div>
                    </div>
                  )}

                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Checkbox
                      checked={criteria.include_applicants_without_country}
                      onCheckedChange={(v) =>
                        setCriteriaField("include_applicants_without_country", Boolean(v))
                      }
                    />
                    Include applicants without country
                  </label>
                </div>

                <div className="space-y-2 border-t pt-3">
                  <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    Filters
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs">Years experience</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        min={0}
                        className="h-9"
                        value={criteria.experience_min_years ?? ""}
                        onChange={(e) =>
                          setCriteriaField(
                            "experience_min_years",
                            e.target.value ? Number(e.target.value) : null,
                          )
                        }
                      />
                      <span className="text-xs text-muted-foreground">to</span>
                      <Input
                        type="number"
                        min={0}
                        className="h-9"
                        value={criteria.experience_max_years ?? ""}
                        onChange={(e) =>
                          setCriteriaField(
                            "experience_max_years",
                            e.target.value ? Number(e.target.value) : null,
                          )
                        }
                      />
                      <span className="text-xs text-muted-foreground">years</span>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs">Educational details</Label>
                    <div className="flex flex-wrap gap-1.5">
                      {DEGREE_OPTIONS.map((d) => {
                        const isOn = criteria.education.includes(d);
                        return (
                          <button
                            key={d}
                            type="button"
                            onClick={() =>
                              setCriteriaField(
                                "education",
                                isOn
                                  ? criteria.education.filter((x) => x !== d)
                                  : [...criteria.education, d],
                              )
                            }
                            className={cn(
                              "rounded-full border px-2.5 py-1 text-[11px]",
                              isOn
                                ? "bg-primary/10 border-primary/30 text-primary font-medium"
                                : "text-muted-foreground hover:bg-muted/60",
                            )}
                          >
                            {d}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs">Work authorization</Label>
                    <div className="flex flex-wrap gap-1.5">
                      {WORK_AUTHORIZATIONS.map((w) => {
                        const isOn = criteria.work_authorizations.includes(w);
                        return (
                          <button
                            key={w}
                            type="button"
                            onClick={() =>
                              setCriteriaField(
                                "work_authorizations",
                                isOn
                                  ? criteria.work_authorizations.filter((x) => x !== w)
                                  : [...criteria.work_authorizations, w],
                              )
                            }
                            className={cn(
                              "rounded-full border px-2.5 py-1 text-[11px]",
                              isOn
                                ? "bg-primary/10 border-primary/30 text-primary font-medium"
                                : "text-muted-foreground hover:bg-muted/60",
                            )}
                          >
                            {w}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs">Employer</Label>
                    <Input
                      value={criteria.employer ?? ""}
                      onChange={(e) => setCriteriaField("employer", e.target.value || null)}
                    />
                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Checkbox
                        checked={criteria.most_recent_employer_only}
                        onCheckedChange={(v) =>
                          setCriteriaField("most_recent_employer_only", Boolean(v))
                        }
                      />
                      Most recent employer
                    </label>
                  </div>

                  {(
                    [
                      ["Willing to relocate", "willing_to_relocate"],
                      ["Clearance", "clearance"],
                    ] as [string, "willing_to_relocate" | "clearance"][]
                  ).map(([label, key]) => (
                    <div key={key} className="flex items-center justify-between gap-2">
                      <Label className="text-xs">{label}</Label>
                      <div className="flex gap-3 text-xs">
                        {[
                          { label: "Yes", value: true },
                          { label: "No", value: false },
                        ].map((opt) => (
                          <label key={opt.label} className="flex items-center gap-1.5">
                            <Checkbox
                              checked={criteria[key] === opt.value}
                              onCheckedChange={(checked) =>
                                setCriteriaField(key, checked ? opt.value : null)
                              }
                            />
                            {opt.label}
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
