"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateJob, useUpdateJob } from "@/lib/hooks/use-jobs";
import { EntityPicker } from "@/components/entity-picker";
import { useUserOptions } from "@/lib/hooks/use-users";
import {
  CURRENCIES,
  DEGREE_OPTIONS,
  EMPLOYMENT_LEVELS,
  INTERVIEW_MODES,
  normalizeInterviewMode,
  JOB_REQUIRED_DOCUMENTS,
  JOB_TYPES,
  RATE_TYPES,
  RATE_UNITS,
  REMOTE_OPTIONS,
  RESPOND_BY_OPTIONS,
  TAX_TERM_OPTIONS,
  TURNAROUND_UNITS,
  WORK_AUTHORIZATIONS,
} from "@/lib/api/jobs";
import { COUNTRIES } from "@/lib/api/clients";
import { ApiError } from "@/lib/api/client";
import { NumberInput } from "@/components/number-input";
import type { Job, JobCreateInput } from "@/lib/api/types";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const NONE = "__none__";

// Openings is null while the field is cleared mid-edit; submit refuses that.
type FormState = Omit<JobCreateInput, "openings"> & { title: string; openings: number | null };

// Mirrors the upper bounds in backend/app/schemas/job.py.
const MAX_RATE = 100_000_000;
const MAX_EXPERIENCE_YEARS = 70;
const MAX_COUNT = 10_000;
const MAX_TURNAROUND = 9_999;

function todayIso(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

/** The number rules the server also enforces, caught before the round trip. */
function checkNumbers(form: FormState, job?: Job): string | null {
  const num = (v: unknown) => (v === null || v === undefined || v === "" ? null : Number(v));
  const pairs: [unknown, unknown, string][] = [
    [form.pay_min, form.pay_max, "Pay rate"],
    [form.client_bill_rate_min, form.client_bill_rate_max, "Client bill rate"],
    [form.experience_min_years, form.experience_max_years, "Experience"],
  ];
  for (const [low, high, label] of pairs) {
    const lo = num(low);
    const hi = num(high);
    if (lo !== null && hi !== null && lo > hi)
      return `${label} minimum cannot be more than the maximum.`;
  }
  if (!form.openings || form.openings < 1) return "Number of positions must be at least 1.";
  if (
    form.respond_by === "Specific Date" &&
    form.respond_by_date &&
    form.respond_by_date < todayIso() &&
    form.respond_by_date !== job?.respond_by_date
  ) {
    return "The respond-by date cannot be in the past.";
  }
  return null;
}

/** 4.5 -> "4:30". */
function toHoursMinutes(value: number | null | undefined): string {
  if (value === null || value === undefined) return "";
  const hours = Math.floor(value);
  const minutes = Math.round((value - hours) * 60);
  return minutes ? `${hours}:${String(minutes).padStart(2, "0")}` : String(hours);
}

/**
 * Turnaround in hours, typed as "4" or "4:30". Stored as fractional hours
 * (4.5), so the value keeps its minutes.
 */
function HoursMinutesInput({
  value,
  onValueChange,
}: {
  value: number | null | undefined;
  onValueChange: (value: number | null) => void;
}) {
  const [text, setText] = useState(() => toHoursMinutes(value));
  const [invalid, setInvalid] = useState(false);

  return (
    <div>
      <Input
        inputMode="numeric"
        placeholder="hh:mm"
        value={text}
        aria-invalid={invalid}
        className={cn(invalid && "border-destructive")}
        onChange={(e) => {
          const next = e.target.value.replace(/[^\d:]/g, "").replace(/:(?=.*:)/g, "");
          setText(next);
          const match = next.match(/^(\d{1,4})(?::(\d{0,2}))?$/);
          if (!next) {
            setInvalid(false);
            onValueChange(null);
          } else if (match && Number(match[2] || 0) < 60) {
            setInvalid(false);
            const minutes = Number(match[2] || 0);
            onValueChange(Math.round((Number(match[1]) + minutes / 60) * 100) / 100);
          } else {
            setInvalid(true);
          }
        }}
      />
      {invalid && <p className="mt-1 text-xs text-destructive">Use hours:minutes, e.g. 4:30.</p>}
    </div>
  );
}

function initialState(job?: Job): FormState {
  return {
    title: job?.title ?? "",
    department: job?.department ?? "",
    client_id: job?.client_id ?? null,
    end_client: job?.end_client ?? "",
    business_unit: job?.business_unit ?? "",
    facility: job?.facility ?? "",
    location: job?.location ?? "",
    workplace: job?.workplace ?? "Onsite",
    employment_type: job?.employment_type ?? "Full-time",
    openings: job?.openings ?? 1,
    priority: job?.priority ?? "Medium",
    duration: job?.duration ?? "",
    required_hours_per_week: job?.required_hours_per_week ?? 40,
    interview_mode: normalizeInterviewMode(job?.interview_mode),
    clearance_required: job?.clearance_required ?? false,
    additional_details: job?.additional_details ?? "",
    employment_test_template: job?.employment_test_template ?? "",
    employment_level: job?.employment_level ?? "",
    required_documents: job?.required_documents ?? ["Resume"],
    work_authorizations: job?.work_authorizations ?? [],

    respond_by: job?.respond_by ?? "Open Until Filled",
    respond_by_date: job?.respond_by_date ?? null,
    turnaround_time_value: job?.turnaround_time_value ?? null,
    turnaround_time_unit: job?.turnaround_time_unit ?? "In Days",

    pay_min: job?.pay_min ?? null,
    pay_max: job?.pay_max ?? null,
    pay_rate_currency: job?.pay_rate_currency ?? "USD",
    pay_rate_unit: job?.pay_rate_unit ?? "Hourly",
    pay_rate_type: job?.pay_rate_type ?? null,
    client_bill_rate_min: job?.client_bill_rate_min ?? null,
    client_bill_rate_max: job?.client_bill_rate_max ?? null,
    client_bill_rate_currency: job?.client_bill_rate_currency ?? "USD",
    client_bill_rate_unit: job?.client_bill_rate_unit ?? "Hourly",
    client_bill_rate_type: job?.client_bill_rate_type ?? null,

    address: job?.address ?? "",
    city: job?.city ?? "",
    states: job?.states ?? [],
    country: job?.country ?? "United States",
    postal_code: job?.postal_code ?? "",

    education: job?.education ?? "",
    experience_min_years: job?.experience_min_years ?? null,
    experience_max_years: job?.experience_max_years ?? null,
    required_skills: job?.required_skills ?? [],
    nice_to_have: job?.nice_to_have ?? [],

    max_allowed_submissions: job?.max_allowed_submissions ?? null,
    tax_terms: job?.tax_terms ?? [],
    sales_manager_id: job?.sales_manager_id ?? null,
    recruitment_manager_id: job?.recruitment_manager_id ?? null,
    account_manager_id: job?.account_manager_id ?? null,
    primary_recruiter_id: job?.primary_recruiter_id ?? null,
    assigned_to_ids: job?.assigned_to_ids ?? [],
    comments: job?.comments ?? "",

    summary: job?.summary ?? "",
    description: job?.description ?? "",
    responsibilities: job?.responsibilities ?? [],
    screening_questions: job?.screening_questions ?? [],
  };
}

function Field({
  label,
  required,
  className,
  children,
}: {
  label: string;
  required?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <Label className="text-xs">
        {label}
        {required && <span className="text-destructive ml-0.5">*</span>}
      </Label>
      {children}
    </div>
  );
}

/** Select that allows an explicit "none" choice, since Radix forbids empty-string values. */
function OptionalSelect({
  value,
  onChange,
  placeholder,
  options,
}: {
  value: string | null | undefined;
  onChange: (value: string | null) => void;
  placeholder: string;
  options: readonly { value: string; label: string }[];
}) {
  return (
    <Select value={value || NONE} onValueChange={(v) => onChange(v === NONE ? null : v)}>
      <SelectTrigger>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={NONE}>{placeholder}</SelectItem>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

/** Multi-select rendered as toggleable chips — used for states, tax terms, and skills. */
function ChipMultiSelect({
  options,
  selected,
  onToggle,
}: {
  options: readonly string[];
  selected: string[];
  onToggle: (option: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((option) => {
        const isOn = selected.includes(option);
        return (
          <button
            key={option}
            type="button"
            onClick={() => onToggle(option)}
            className={cn(
              "rounded-full border px-2.5 py-1 text-[11px] transition-colors",
              isOn
                ? "bg-primary/10 border-primary/30 text-primary font-medium"
                : "text-muted-foreground hover:bg-muted/60",
            )}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}

/** Free-text list editor rendering entries as removable chips. */
function ChipInput({
  value,
  onChange,
  placeholder,
}: {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder: string;
}) {
  const [draft, setDraft] = useState("");

  function commit() {
    const entry = draft.trim();
    if (entry && !value.includes(entry)) onChange([...value, entry]);
    setDraft("");
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          value={draft}
          placeholder={placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commit();
            }
          }}
        />
        <Button type="button" size="sm" variant="outline" onClick={commit} disabled={!draft.trim()}>
          Add
        </Button>
      </div>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map((v) => (
            <Badge key={v} variant="secondary" className="gap-1 text-[11px]">
              {v}
              <button
                type="button"
                onClick={() => onChange(value.filter((x) => x !== v))}
                className="hover:text-destructive"
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

const US_STATES = [
  "Alabama",
  "Alaska",
  "Arizona",
  "Arkansas",
  "California",
  "Colorado",
  "Connecticut",
  "Delaware",
  "Florida",
  "Georgia",
  "Hawaii",
  "Idaho",
  "Illinois",
  "Indiana",
  "Iowa",
  "Kansas",
  "Kentucky",
  "Louisiana",
  "Maine",
  "Maryland",
  "Massachusetts",
  "Michigan",
  "Minnesota",
  "Mississippi",
  "Missouri",
  "Montana",
  "Nebraska",
  "Nevada",
  "New Hampshire",
  "New Jersey",
  "New Mexico",
  "New York",
  "North Carolina",
  "North Dakota",
  "Ohio",
  "Oklahoma",
  "Oregon",
  "Pennsylvania",
  "Rhode Island",
  "South Carolina",
  "South Dakota",
  "Tennessee",
  "Texas",
  "Utah",
  "Vermont",
  "Virginia",
  "Washington",
  "West Virginia",
  "Wisconsin",
  "Wyoming",
] as const;

export function JobForm({ job }: { job?: Job }) {
  const router = useRouter();
  const isEdit = Boolean(job);
  const createJob = useCreateJob();
  const updateJob = useUpdateJob(job?.id ?? "");
  // Names only, so recruiters -- who create and post jobs -- can fill these in.
  const { data: users } = useUserOptions();

  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(() => initialState(job));

  const userOptions = useMemo(
    () => (users ?? []).map((u) => ({ value: u.id, label: u.full_name })),
    [users],
  );

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function toggleIn(
    key: "states" | "tax_terms" | "required_documents" | "work_authorizations",
    option: string,
  ) {
    setForm((prev) => {
      const current = prev[key] ?? [];
      return {
        ...prev,
        [key]: current.includes(option)
          ? current.filter((v) => v !== option)
          : [...current, option],
      };
    });
  }

  const pending = createJob.isPending || updateJob.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!form.title.trim()) {
      setError("Job title is required.");
      return;
    }
    if (!form.client_id) {
      setError("Client is required.");
      return;
    }
    if (!form.required_skills?.length) {
      setError("At least one primary skill is required.");
      return;
    }
    const problem = checkNumbers(form, job);
    if (problem) {
      setError(problem);
      return;
    }

    // Empty strings mean "not provided" — send null so the column stays empty.
    const payload = Object.fromEntries(
      Object.entries(form).map(([k, v]) => [k, v === "" ? null : v]),
    ) as JobCreateInput;
    payload.title = form.title.trim();

    try {
      if (isEdit && job) {
        await updateJob.mutateAsync(payload);
        router.push(`/jobs/${job.id}`);
      } else {
        const created = await createJob.mutateAsync(payload);
        router.push(`/jobs/${created.id}`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save job.");
    }
  }

  return (
    <AppShell
      title={isEdit ? `Edit ${job!.title}` : "New Job"}
      breadcrumbs={[
        { label: "Home", to: "/" },
        { label: "Jobs", to: "/jobs" },
        { label: isEdit ? "Edit" : "New" },
      ]}
      actions={
        <>
          <Button
            variant="outline"
            size="sm"
            type="button"
            onClick={() => router.push(isEdit ? `/jobs/${job!.id}` : "/jobs")}
          >
            Cancel
          </Button>
          <Button size="sm" form="job-form" type="submit" disabled={pending}>
            {pending ? (
              <>
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                Saving…
              </>
            ) : isEdit ? (
              "Save"
            ) : (
              "Save as Draft"
            )}
          </Button>
        </>
      }
    >
      <form id="job-form" onSubmit={handleSubmit} className="space-y-4 max-w-[1400px]">
        {error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        <Card>
          <CardContent className="p-5">
            <Field label="Business Unit" className="max-w-md">
              <Input
                value={form.business_unit ?? ""}
                onChange={(e) => set("business_unit", e.target.value)}
                placeholder="e.g. Peer Consulting Resources Inc."
              />
            </Field>
          </CardContent>
        </Card>

        {/* ---------- Job Details ---------- */}
        <Card>
          <CardContent className="p-5 space-y-4">
            <h2 className="text-base font-semibold">Job Details</h2>

            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Job Code" required>
                <Input
                  readOnly
                  value={job?.req_id ?? "Assigned on save"}
                  className="cursor-default text-muted-foreground font-mono"
                />
              </Field>
              <Field label="Facility">
                <Input
                  value={form.facility ?? ""}
                  onChange={(e) => set("facility", e.target.value)}
                />
              </Field>
              <Field label="Job Title" required>
                <Input
                  value={form.title}
                  onChange={(e) => set("title", e.target.value)}
                  placeholder="Required"
                  required
                />
              </Field>
            </div>

            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Client Bill Rate / Salary">
                <div className="grid grid-cols-2 gap-2">
                  <Select
                    value={form.client_bill_rate_currency ?? "USD"}
                    onValueChange={(v) => set("client_bill_rate_currency", v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CURRENCIES.map((c) => (
                        <SelectItem key={c} value={c}>
                          {c}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <NumberInput
                    decimals={2}
                    max={MAX_RATE}
                    placeholder="Min"
                    value={form.client_bill_rate_min}
                    onValueChange={(v) => set("client_bill_rate_min", v)}
                  />
                  <NumberInput
                    decimals={2}
                    max={MAX_RATE}
                    placeholder="Max"
                    value={form.client_bill_rate_max}
                    onValueChange={(v) => set("client_bill_rate_max", v)}
                  />
                  <Select
                    value={form.client_bill_rate_unit ?? "Hourly"}
                    onValueChange={(v) => set("client_bill_rate_unit", v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {RATE_UNITS.map((u) => (
                        <SelectItem key={u} value={u}>
                          {u}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <div className="col-span-2">
                    <OptionalSelect
                      value={form.client_bill_rate_type}
                      onChange={(v) => set("client_bill_rate_type", v)}
                      placeholder="Rate type"
                      options={RATE_TYPES.map((t) => ({ value: t, label: t }))}
                    />
                  </div>
                </div>
              </Field>

              <Field label="Pay Rate / Salary">
                <div className="grid grid-cols-2 gap-2">
                  <Select
                    value={form.pay_rate_currency ?? "USD"}
                    onValueChange={(v) => set("pay_rate_currency", v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CURRENCIES.map((c) => (
                        <SelectItem key={c} value={c}>
                          {c}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <NumberInput
                    max={MAX_RATE}
                    placeholder="Min"
                    value={form.pay_min}
                    onValueChange={(v) => set("pay_min", v === null ? null : Number(v))}
                  />
                  <NumberInput
                    max={MAX_RATE}
                    placeholder="Max"
                    value={form.pay_max}
                    onValueChange={(v) => set("pay_max", v === null ? null : Number(v))}
                  />
                  <Select
                    value={form.pay_rate_unit ?? "Hourly"}
                    onValueChange={(v) => set("pay_rate_unit", v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {RATE_UNITS.map((u) => (
                        <SelectItem key={u} value={u}>
                          {u}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <div className="col-span-2">
                    <OptionalSelect
                      value={form.pay_rate_type}
                      onChange={(v) => set("pay_rate_type", v)}
                      placeholder="Rate type"
                      options={RATE_TYPES.map((t) => ({ value: t, label: t }))}
                    />
                  </div>
                </div>
              </Field>

              <div className="space-y-4">
                <Field label="Respond By" required>
                  <Select
                    value={form.respond_by ?? "Open Until Filled"}
                    onValueChange={(v) => set("respond_by", v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {RESPOND_BY_OPTIONS.map((o) => (
                        <SelectItem key={o} value={o}>
                          {o}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                {form.respond_by === "Specific Date" && (
                  <Field label="Respond by date">
                    <Input
                      type="date"
                      min={todayIso()}
                      value={form.respond_by_date ?? ""}
                      onChange={(e) => set("respond_by_date", e.target.value || null)}
                    />
                  </Field>
                )}
              </div>
            </div>

            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Remote Job">
                <RadioGroup
                  value={form.workplace ?? "Onsite"}
                  onValueChange={(v) => set("workplace", v)}
                  className="flex gap-4 pt-2"
                >
                  {REMOTE_OPTIONS.map((o) => (
                    <label key={o} className="flex items-center gap-2 text-sm">
                      <RadioGroupItem value={o} />
                      {o === "Onsite" ? "No" : o === "Remote" ? "Yes" : "Hybrid"}
                    </label>
                  ))}
                </RadioGroup>
              </Field>
              <Field label="Country">
                <Select
                  value={form.country ?? "United States"}
                  onValueChange={(v) => set("country", v)}
                >
                  <SelectTrigger>
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
              </Field>
              <Field label="States" required>
                <div className="max-h-32 overflow-y-auto rounded-md border p-2">
                  <ChipMultiSelect
                    options={US_STATES}
                    selected={form.states ?? []}
                    onToggle={(o) => toggleIn("states", o)}
                  />
                </div>
              </Field>
            </div>

            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Location">
                <Input
                  value={form.location ?? ""}
                  onChange={(e) => set("location", e.target.value)}
                  placeholder="Search location with city or zip code"
                />
              </Field>
              <Field label="Job Status" required>
                <Input
                  readOnly
                  value={job?.status ?? "Draft"}
                  className="cursor-default text-muted-foreground"
                />
              </Field>
              <Field label="Job Type">
                <Select
                  value={form.employment_type ?? "Full-time"}
                  onValueChange={(v) => set("employment_type", v)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {JOB_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>

            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Required Hours/Week">
                <NumberInput
                  max={168}
                  value={form.required_hours_per_week}
                  onValueChange={(v) =>
                    set("required_hours_per_week", v === null ? null : Number(v))
                  }
                />
              </Field>
              <Field label="Client" required>
                <EntityPicker
                  kind="clients"
                  value={form.client_id}
                  onChange={(v) => set("client_id", v)}
                  placeholder="Search for a client"
                />
              </Field>
              <Field label="End Client">
                <Input
                  value={form.end_client ?? ""}
                  onChange={(e) => set("end_client", e.target.value)}
                />
              </Field>
            </div>

            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Required Documents">
                <div className="rounded-md border p-2">
                  <ChipMultiSelect
                    options={JOB_REQUIRED_DOCUMENTS}
                    selected={form.required_documents ?? []}
                    onToggle={(o) => toggleIn("required_documents", o)}
                  />
                </div>
              </Field>
              <Field label="Turnaround Time" required>
                <div className="grid grid-cols-2 gap-2">
                  {form.turnaround_time_unit === "In Hours" ? (
                    <HoursMinutesInput
                      value={form.turnaround_time_value}
                      onValueChange={(v) => set("turnaround_time_value", v)}
                    />
                  ) : (
                    <NumberInput
                      max={MAX_TURNAROUND}
                      value={
                        form.turnaround_time_value === null ||
                        form.turnaround_time_value === undefined
                          ? null
                          : Math.round(form.turnaround_time_value)
                      }
                      onValueChange={(v) =>
                        set("turnaround_time_value", v === null ? null : Number(v))
                      }
                    />
                  )}
                  <Select
                    value={form.turnaround_time_unit ?? "In Days"}
                    onValueChange={(v) => {
                      set("turnaround_time_unit", v);
                      // Days and weeks are whole: 4:30 hours must not become 4.5 days.
                      const current = form.turnaround_time_value;
                      if (v !== "In Hours" && current !== null && current !== undefined) {
                        set("turnaround_time_value", Math.round(current));
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TURNAROUND_UNITS.map((u) => (
                        <SelectItem key={u} value={u}>
                          {u}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </Field>
              <Field label="Priority">
                <Select value={form.priority ?? "Medium"} onValueChange={(v) => set("priority", v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {["Low", "Medium", "High", "Urgent"].map((p) => (
                      <SelectItem key={p} value={p}>
                        {p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>

            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Duration" required>
                <Input
                  value={form.duration ?? ""}
                  onChange={(e) => set("duration", e.target.value)}
                  placeholder="e.g. 12 months"
                />
              </Field>
              <Field label="Additional Details">
                <Textarea
                  rows={2}
                  value={form.additional_details ?? ""}
                  onChange={(e) => set("additional_details", e.target.value)}
                />
              </Field>
              <Field label="Work Authorization" required>
                <div className="rounded-md border p-2">
                  <ChipMultiSelect
                    options={WORK_AUTHORIZATIONS}
                    selected={form.work_authorizations ?? []}
                    onToggle={(o) => toggleIn("work_authorizations", o)}
                  />
                </div>
              </Field>
            </div>

            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Interview Mode" required>
                <OptionalSelect
                  value={form.interview_mode}
                  onChange={(v) => set("interview_mode", v)}
                  placeholder="Select"
                  options={INTERVIEW_MODES.map((m) => ({ value: m, label: m }))}
                />
              </Field>
              <Field label="Clearance">
                <RadioGroup
                  value={form.clearance_required ? "Yes" : "No"}
                  onValueChange={(v) => set("clearance_required", v === "Yes")}
                  className="flex gap-4 pt-2"
                >
                  {["Yes", "No"].map((o) => (
                    <label key={o} className="flex items-center gap-2 text-sm">
                      <RadioGroupItem value={o} />
                      {o}
                    </label>
                  ))}
                </RadioGroup>
              </Field>
              <Field label="Address">
                <Textarea
                  rows={2}
                  value={form.address ?? ""}
                  onChange={(e) => set("address", e.target.value)}
                />
              </Field>
            </div>

            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Employment Test Template">
                <Input
                  value={form.employment_test_template ?? ""}
                  onChange={(e) => set("employment_test_template", e.target.value)}
                />
              </Field>
              <Field label="Employment Level">
                <OptionalSelect
                  value={form.employment_level}
                  onChange={(v) => set("employment_level", v)}
                  placeholder="Select"
                  options={EMPLOYMENT_LEVELS.map((l) => ({ value: l, label: l }))}
                />
              </Field>
            </div>
          </CardContent>
        </Card>

        {/* ---------- Skills ---------- */}
        <Card>
          <CardContent className="p-5 space-y-4">
            <h2 className="text-base font-semibold">Skills</h2>
            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Degree">
                <OptionalSelect
                  value={form.education}
                  onChange={(v) => set("education", v)}
                  placeholder="Select"
                  options={DEGREE_OPTIONS.map((d) => ({ value: d, label: d }))}
                />
              </Field>
              <Field label="Experience (years)" required>
                <div className="grid grid-cols-2 gap-2">
                  <NumberInput
                    max={MAX_EXPERIENCE_YEARS}
                    placeholder="Min"
                    value={form.experience_min_years}
                    onValueChange={(v) =>
                      set("experience_min_years", v === null ? null : Number(v))
                    }
                  />
                  <NumberInput
                    max={MAX_EXPERIENCE_YEARS}
                    placeholder="Max"
                    value={form.experience_max_years}
                    onValueChange={(v) =>
                      set("experience_max_years", v === null ? null : Number(v))
                    }
                  />
                </div>
              </Field>
              <Field label="Primary Skills" required>
                <ChipInput
                  value={form.required_skills ?? []}
                  onChange={(v) => set("required_skills", v)}
                  placeholder="Add a skill and press Enter"
                />
              </Field>
            </div>
            <Field label="Secondary skills">
              <ChipInput
                value={form.nice_to_have ?? []}
                onChange={(v) => set("nice_to_have", v)}
                placeholder="Add a nice-to-have skill"
              />
            </Field>
          </CardContent>
        </Card>

        {/* ---------- Organizational Information ---------- */}
        <Card>
          <CardContent className="p-5 space-y-4">
            <h2 className="text-base font-semibold">Organizational Information</h2>
            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Number of Positions" required>
                <NumberInput
                  max={MAX_COUNT}
                  value={form.openings}
                  onValueChange={(v) => set("openings", v === null ? null : Number(v))}
                />
              </Field>
              <Field label="Maximum Allowed Submissions">
                <NumberInput
                  max={MAX_COUNT}
                  value={form.max_allowed_submissions}
                  onValueChange={(v) =>
                    set("max_allowed_submissions", v === null ? null : Number(v))
                  }
                />
              </Field>
              <Field label="Tax Terms">
                <div className="rounded-md border p-2">
                  <ChipMultiSelect
                    options={TAX_TERM_OPTIONS}
                    selected={form.tax_terms ?? []}
                    onToggle={(o) => toggleIn("tax_terms", o)}
                  />
                </div>
              </Field>
            </div>

            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Sales Manager">
                <OptionalSelect
                  value={form.sales_manager_id}
                  onChange={(v) => set("sales_manager_id", v)}
                  placeholder="Select"
                  options={userOptions}
                />
              </Field>
              <Field label="Recruitment Manager" required>
                <OptionalSelect
                  value={form.recruitment_manager_id}
                  onChange={(v) => set("recruitment_manager_id", v)}
                  placeholder="Select"
                  options={userOptions}
                />
              </Field>
              <Field label="Account Manager">
                <OptionalSelect
                  value={form.account_manager_id}
                  onChange={(v) => set("account_manager_id", v)}
                  placeholder="Select"
                  options={userOptions}
                />
              </Field>
            </div>

            <div className="grid lg:grid-cols-3 gap-4">
              <Field label="Assigned To">
                <div className="rounded-md border p-2 max-h-32 overflow-y-auto">
                  <div className="flex flex-wrap gap-1.5">
                    {userOptions.map((u) => {
                      const isOn = (form.assigned_to_ids ?? []).includes(u.value);
                      return (
                        <button
                          key={u.value}
                          type="button"
                          onClick={() =>
                            set(
                              "assigned_to_ids",
                              isOn
                                ? (form.assigned_to_ids ?? []).filter((id) => id !== u.value)
                                : [...(form.assigned_to_ids ?? []), u.value],
                            )
                          }
                          className={cn(
                            "rounded-full border px-2.5 py-1 text-[11px] transition-colors",
                            isOn
                              ? "bg-primary/10 border-primary/30 text-primary font-medium"
                              : "text-muted-foreground hover:bg-muted/60",
                          )}
                        >
                          {u.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </Field>
              <Field label="Primary Recruiter">
                <OptionalSelect
                  value={form.primary_recruiter_id}
                  onChange={(v) => set("primary_recruiter_id", v)}
                  placeholder="Select"
                  options={userOptions}
                />
              </Field>
              <Field label="Comments">
                <Textarea
                  rows={3}
                  value={form.comments ?? ""}
                  onChange={(e) => set("comments", e.target.value)}
                />
              </Field>
            </div>
          </CardContent>
        </Card>

        {/* ---------- Job Description ---------- */}
        <Card>
          <CardContent className="p-5 space-y-4">
            <h2 className="text-base font-semibold">Job Description</h2>
            <Field label="Recruiter summary">
              <Textarea
                rows={3}
                value={form.summary ?? ""}
                onChange={(e) => set("summary", e.target.value)}
              />
            </Field>
            <Field label="Full description">
              <Textarea
                rows={8}
                value={form.description ?? ""}
                onChange={(e) => set("description", e.target.value)}
              />
            </Field>
            <Field label="Responsibilities">
              <ChipInput
                value={form.responsibilities ?? []}
                onChange={(v) => set("responsibilities", v)}
                placeholder="Add a responsibility"
              />
            </Field>
            <Field label="Screening questions">
              <ChipInput
                value={form.screening_questions ?? []}
                onChange={(v) => set("screening_questions", v)}
                placeholder="Add a screening question"
              />
            </Field>
          </CardContent>
        </Card>
      </form>
    </AppShell>
  );
}
