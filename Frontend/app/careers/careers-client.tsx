"use client";

import { useMemo, useState, type ChangeEvent, type ReactNode } from "react";
import Link from "next/link";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  getPublicOrganization,
  listPublicJobs,
  applyToJob,
  type ApplyInput,
  type PublicJob,
} from "@/lib/api/careers-public";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Building2, MapPin, Briefcase, Search, CheckCircle2 } from "lucide-react";

const EMPTY_FORM: ApplyInput = {
  full_name: "",
  email: "",
  phone: "",
  location: "",
  current_title: "",
  current_company: "",
  total_experience_years: "",
  relevant_experience_years: "",
  linkedin_url: "",
  portfolio_url: "",
  github_url: "",
  highest_qualification: "",
  college: "",
  graduation_year: "",
  notice_period: "",
  earliest_joining_date: "",
  current_ctc: "",
  expected_ctc: "",
  work_arrangement_ok: "",
  heard_from: "",
  work_authorized: "",
  needs_sponsorship: "",
};

const FIELD_CLASS =
  "flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="space-y-3 border-t pt-4 first:border-t-0 first:pt-0">
      <legend className="text-sm font-semibold">{title}</legend>
      {children}
    </fieldset>
  );
}

function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">
        {label}
        {required && <span className="text-destructive"> *</span>}
      </Label>
      {children}
      {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

function Choice({
  value,
  onChange,
  options,
  required,
}: {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  required?: boolean;
}) {
  return (
    <select
      className={FIELD_CLASS}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      required={required}
    >
      <option value="">Select…</option>
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}

const YES_NO = ["Yes", "No"];
const NOTICE_PERIODS = [
  "Immediate",
  "15 days",
  "30 days",
  "60 days",
  "90 days",
  "More than 90 days",
];
const HEARD_FROM = [
  "LinkedIn",
  "Company website",
  "Job portal",
  "Employee referral",
  "Social media",
  "Other",
];

function ApplyDialog({ job, onClose }: { job: PublicJob | null; onClose: () => void }) {
  const [form, setForm] = useState<ApplyInput>(EMPTY_FORM);
  const [roleAnswers, setRoleAnswers] = useState<Record<string, string>>({});
  const [resume, setResume] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const set = (key: keyof ApplyInput) => (value: string) =>
    setForm((current) => ({ ...current, [key]: value }));
  const text = (key: keyof ApplyInput) => ({
    value: form[key],
    onChange: (e: ChangeEvent<HTMLInputElement>) => set(key)(e.target.value),
  });

  const mutation = useMutation({
    mutationFn: () => applyToJob(job!.id, form, roleAnswers, resume!),
    onSuccess: () => setDone(true),
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again."),
  });

  function reset() {
    setForm(EMPTY_FORM);
    setRoleAnswers({});
    setResume(null);
    setError(null);
    setDone(false);
  }

  function handleClose() {
    reset();
    onClose();
  }

  const arrangement = job ? [job.workplace, job.location].filter(Boolean).join(" · ") : "";

  return (
    <Dialog open={job !== null} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        {done ? (
          <div className="text-center py-6 space-y-3">
            <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto" />
            <DialogTitle>Application received</DialogTitle>
            <p className="text-sm text-muted-foreground">
              Thanks for applying to {job?.title}. Our team will review your profile and be in
              touch.
            </p>
            <Button onClick={handleClose}>Close</Button>
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Apply — {job?.title}</DialogTitle>
              <p className="text-xs text-muted-foreground">
                Fields marked <span className="text-destructive">*</span> are required.
              </p>
            </DialogHeader>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setError(null);
                if (!resume) {
                  setError("Please upload your résumé.");
                  return;
                }
                mutation.mutate();
              }}
              className="space-y-5"
            >
              <Section title="1. Personal details">
                <Field label="Full name" required>
                  <Input {...text("full_name")} required />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Email address" required>
                    <Input type="email" {...text("email")} required />
                  </Field>
                  <Field label="Phone number" required>
                    <Input type="tel" {...text("phone")} required minLength={5} />
                  </Field>
                </div>
                <Field label="Current city / location" required>
                  <Input {...text("location")} required />
                </Field>
              </Section>

              <Section title="2. Professional profile">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Current job title" required>
                    <Input {...text("current_title")} required />
                  </Field>
                  <Field label="Current company">
                    <Input {...text("current_company")} />
                  </Field>
                  <Field label="Total years of experience" required>
                    <Input
                      type="number"
                      min={0}
                      max={60}
                      step={0.5}
                      {...text("total_experience_years")}
                      required
                    />
                  </Field>
                  <Field label="Relevant years of experience">
                    <Input
                      type="number"
                      min={0}
                      max={60}
                      step={0.5}
                      {...text("relevant_experience_years")}
                    />
                  </Field>
                </div>
              </Section>

              <Section title="3. Résumé & portfolio">
                <Field
                  label="Upload résumé / CV (PDF or DOCX)"
                  required
                  hint="Your résumé lets our team pre-screen your profile faster."
                >
                  <Input
                    type="file"
                    accept=".pdf,.doc,.docx"
                    onChange={(e) => setResume(e.target.files?.[0] ?? null)}
                    required
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="LinkedIn profile">
                    <Input
                      type="url"
                      placeholder="https://linkedin.com/in/…"
                      {...text("linkedin_url")}
                    />
                  </Field>
                  <Field label="Portfolio / personal website">
                    <Input type="url" placeholder="https://" {...text("portfolio_url")} />
                  </Field>
                </div>
                {job?.ask_portfolio_links && (
                  <Field label="GitHub / Behance / Dribbble">
                    <Input type="url" placeholder="https://" {...text("github_url")} />
                  </Field>
                )}
              </Section>

              <Section title="4. Education">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Highest qualification" required>
                    <Input
                      placeholder="e.g. B.Tech, MBA"
                      {...text("highest_qualification")}
                      required
                    />
                  </Field>
                  <Field label="College / university">
                    <Input {...text("college")} />
                  </Field>
                  <Field label="Graduation year">
                    <Input type="number" min={1950} max={2100} {...text("graduation_year")} />
                  </Field>
                </div>
              </Section>

              {job && job.role_questions.length > 0 && (
                <Section title="5. Role-specific questions">
                  {job.role_questions.map((q) => {
                    const value = roleAnswers[q.key] ?? "";
                    const update = (v: string) =>
                      setRoleAnswers((current) => ({ ...current, [q.key]: v }));
                    return (
                      <Field key={q.key} label={q.label} required={q.required}>
                        {q.type === "yesno" ? (
                          <Choice
                            value={value}
                            onChange={update}
                            options={YES_NO}
                            required={q.required}
                          />
                        ) : q.type === "textarea" ? (
                          <textarea
                            className={`${FIELD_CLASS} min-h-[72px]`}
                            value={value}
                            placeholder={q.placeholder ?? undefined}
                            onChange={(e) => update(e.target.value)}
                            required={q.required}
                            maxLength={4000}
                          />
                        ) : (
                          <Input
                            type={q.type === "number" ? "number" : "text"}
                            min={q.type === "number" ? 0 : undefined}
                            step={q.type === "number" ? 0.5 : undefined}
                            value={value}
                            placeholder={q.placeholder ?? undefined}
                            onChange={(e) => update(e.target.value)}
                            required={q.required}
                          />
                        )}
                      </Field>
                    );
                  })}
                </Section>
              )}

              <Section title="6. Availability & compensation">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Notice period" required>
                    <Choice
                      value={form.notice_period}
                      onChange={set("notice_period")}
                      options={NOTICE_PERIODS}
                      required
                    />
                  </Field>
                  <Field label="Earliest joining date">
                    <Input type="date" {...text("earliest_joining_date")} />
                  </Field>
                  <Field label="Current CTC">
                    <Input placeholder="Annual, e.g. 1200000" {...text("current_ctc")} />
                  </Field>
                  <Field label="Expected CTC" required>
                    <Input placeholder="Annual, e.g. 1500000" {...text("expected_ctc")} required />
                  </Field>
                </div>
                <Field
                  label={`Are you open to the work arrangement mentioned in the JD${arrangement ? ` (${arrangement})` : ""}?`}
                  required
                >
                  <Choice
                    value={form.work_arrangement_ok}
                    onChange={set("work_arrangement_ok")}
                    options={YES_NO}
                    required
                  />
                </Field>
              </Section>

              <Section title="7. Additional questions (optional)">
                <Field label="How did you hear about this opportunity?">
                  <Choice
                    value={form.heard_from}
                    onChange={set("heard_from")}
                    options={HEARD_FROM}
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Are you currently authorized to work in the required location/country?">
                    <Choice
                      value={form.work_authorized}
                      onChange={set("work_authorized")}
                      options={YES_NO}
                    />
                  </Field>
                  {job?.ask_sponsorship && (
                    <Field label="Do you require sponsorship?">
                      <Choice
                        value={form.needs_sponsorship}
                        onChange={set("needs_sponsorship")}
                        options={YES_NO}
                      />
                    </Field>
                  )}
                </div>
              </Section>

              {error && <div className="text-sm text-destructive">{error}</div>}
              <DialogFooter>
                <Button type="submit" disabled={mutation.isPending}>
                  {mutation.isPending ? "Submitting…" : "Submit application"}
                </Button>
              </DialogFooter>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function CareersClient() {
  const { data: org } = useQuery({
    queryKey: ["public-org"],
    queryFn: () => getPublicOrganization(),
  });
  const { data: jobs, isLoading } = useQuery({
    queryKey: ["public-jobs"],
    queryFn: () => listPublicJobs(),
  });
  const [search, setSearch] = useState("");
  const [activeJob, setActiveJob] = useState<PublicJob | null>(null);

  const companyName = org?.name ?? "Peer Consulting Resources Inc.";
  const initial = companyName.charAt(0).toUpperCase();

  const filtered = useMemo(() => {
    const list = jobs ?? [];
    if (!search) return list;
    const q = search.toLowerCase();
    return list.filter(
      (j) =>
        j.title.toLowerCase().includes(q) ||
        (j.department ?? "").toLowerCase().includes(q) ||
        (j.location ?? "").toLowerCase().includes(q),
    );
  }, [jobs, search]);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold">
            <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center text-primary-foreground text-sm font-bold">
              {initial}
            </div>
            {companyName}
          </div>
          <nav className="flex items-center gap-6 text-sm">
            <Link href="/" className="text-muted-foreground hover:text-foreground">
              ATS admin
            </Link>
          </nav>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 py-16 text-center">
        <Badge variant="secondary" className="mb-4">
          {isLoading ? "Loading roles…" : `We're hiring — ${filtered.length} open roles`}
        </Badge>
        <h1 className="text-5xl font-semibold tracking-tight">Build your career with us.</h1>
        <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
          Join {companyName} and work alongside a team shaping the future of consulting.
        </p>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-16">
        <div className="flex gap-3 mb-6">
          <div className="flex-1 relative">
            <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
            <Input
              placeholder="Search roles"
              className="pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        <div className="border rounded-lg divide-y bg-white">
          {isLoading && (
            <div className="p-6 text-center text-sm text-muted-foreground">Loading…</div>
          )}
          {!isLoading && filtered.length === 0 && (
            <div className="p-6 text-center text-sm text-muted-foreground">
              No open roles right now. Check back soon.
            </div>
          )}
          {filtered.map((j) => (
            <div
              key={j.id}
              className="p-5 flex items-center justify-between hover:bg-muted/30 transition-colors"
            >
              <div>
                <div className="font-medium">{j.title}</div>
                <div className="text-sm text-muted-foreground flex items-center gap-4 mt-1 flex-wrap">
                  {j.department && (
                    <span className="flex items-center gap-1">
                      <Building2 className="h-3.5 w-3.5" />
                      {j.department}
                    </span>
                  )}
                  {j.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5" />
                      {j.location}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Briefcase className="h-3.5 w-3.5" />
                    {j.employment_type}
                  </span>
                  <span>{j.workplace}</span>
                </div>
              </div>
              <Button size="sm" onClick={() => setActiveJob(j)}>
                Apply
              </Button>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t py-8 text-center text-xs text-muted-foreground">
        © 2026 {companyName} · Powered by ATS Tracker
      </footer>

      <ApplyDialog job={activeJob} onClose={() => setActiveJob(null)} />
    </div>
  );
}
