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
import { Switch } from "@/components/ui/switch";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useClients, useCreateClient, useUpdateClient } from "@/lib/hooks/use-clients";
import { useUsers } from "@/lib/hooks/use-users";
import {
  ASSIGNMENT_ROLES,
  CLIENT_CATEGORIES,
  CLIENT_FACILITY_OPTIONS,
  CLIENT_NOTE_TYPES,
  CLIENT_STATUSES,
  CLIENT_VISIBILITIES,
  COUNTRIES,
  INDUSTRIES,
  PAYMENT_TERMS,
  PRACTICES,
  REQUIRED_DOCUMENT_OPTIONS,
  SUBMISSION_FORMAT_OPTIONS,
} from "@/lib/api/clients";
import { ApiError } from "@/lib/api/client";
import type {
  Client,
  ClientAccountInput,
  ClientAssignmentInput,
  ClientContactInput,
  ClientCreateInput,
  ClientNoteInput,
} from "@/lib/api/types";
import {
  Building2,
  Users,
  StickyNote,
  FolderOpen,
  FileCheck2,
  Contact,
  UserPlus,
  Calculator,
  Table2,
  Loader2,
  Trash2,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";

const SECTIONS = [
  { key: "business", label: "Business Information", icon: Building2 },
  { key: "accounts", label: "Accounts", icon: Users },
  { key: "notes", label: "Notes", icon: StickyNote },
  { key: "documents", label: "Documents", icon: FolderOpen },
  { key: "guidelines", label: "Guidelines", icon: FileCheck2 },
  { key: "contacts", label: "Contacts", icon: Contact },
  { key: "assignment", label: "Assignment", icon: UserPlus },
  { key: "markup", label: "Markup Calculation", icon: Calculator },
  { key: "submission", label: "Client Submission Format", icon: Table2 },
] as const;

type SectionKey = (typeof SECTIONS)[number]["key"];

const NONE = "__none__";

type FormState = ClientCreateInput & { name: string };

function initialState(client?: Client): FormState {
  return {
    name: client?.name ?? "",
    short_name: client?.short_name ?? "",
    vms_client_name: client?.vms_client_name ?? "",
    federal_id: client?.federal_id ?? "",
    contact_number: client?.contact_number ?? "",
    email_id: client?.email_id ?? "",
    fax: client?.fax ?? "",
    website: client?.website ?? "",
    industry: client?.industry ?? "",
    status: client?.status ?? "Active",
    category: client?.category ?? "",
    practice: client?.practice ?? "",
    payment_terms: client?.payment_terms ?? "",
    about_company: client?.about_company ?? "",
    address: client?.address ?? "",
    city: client?.city ?? "",
    state: client?.state ?? "",
    country: client?.country ?? "United States",
    postal_code: client?.postal_code ?? "",
    primary_business_unit: client?.primary_business_unit ?? "",
    business_unit: client?.business_unit ?? "",
    client_visibility: client?.client_visibility ?? "Organization Level",
    primary_owner_id: client?.primary_owner_id ?? null,
    ownership_id: client?.ownership_id ?? null,
    client_lead_id: client?.client_lead_id ?? null,
    parent_client_id: client?.parent_client_id ?? null,
    display_on_job_posting: client?.display_on_job_posting ?? true,
    send_requirement: client?.send_requirement ?? true,
    send_hotlist: client?.send_hotlist ?? true,
    allow_access_to_all_users: client?.allow_access_to_all_users ?? false,
    notify_near_client_location: client?.notify_near_client_location ?? false,
    stop_contact_email_on_submit: client?.stop_contact_email_on_submit ?? false,
    default_address_for_jobs: client?.default_address_for_jobs ?? false,
    client_facilities: client?.client_facilities ?? [],
    required_documents: client?.required_documents ?? [],
    submission_format_fields: client?.submission_format_fields ?? [],
    guidelines: client?.guidelines ?? "",
    markup_percentage: client?.markup_percentage ?? null,
    overtime_markup_percentage: client?.overtime_markup_percentage ?? null,
    standard_working_hours: client?.standard_working_hours ?? null,
    submission_instructions: client?.submission_instructions ?? "",
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

function CheckboxGrid({
  options,
  selected,
  onToggle,
}: {
  options: readonly string[];
  selected: string[];
  onToggle: (option: string) => void;
}) {
  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
      {options.map((option) => (
        <label
          key={option}
          className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm cursor-pointer hover:bg-muted/40"
        >
          <Checkbox checked={selected.includes(option)} onCheckedChange={() => onToggle(option)} />
          {option}
        </label>
      ))}
    </div>
  );
}

export function ClientForm({ client }: { client?: Client }) {
  const router = useRouter();
  const isEdit = Boolean(client);
  const createClient = useCreateClient();
  const updateClient = useUpdateClient(client?.id ?? "");
  const { data: users } = useUsers();
  const { data: allClients } = useClients();

  const [section, setSection] = useState<SectionKey>("business");
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(() => initialState(client));

  // Nested rows are only collected on create; on edit they are managed from the snapshot page.
  const [accounts, setAccounts] = useState<ClientAccountInput[]>([]);
  const [contacts, setContacts] = useState<ClientContactInput[]>([]);
  const [notes, setNotes] = useState<ClientNoteInput[]>([]);
  const [assignments, setAssignments] = useState<ClientAssignmentInput[]>([]);

  const userOptions = useMemo(
    () => (users ?? []).map((u) => ({ value: u.id, label: `${u.full_name} (${u.email})` })),
    [users],
  );
  const parentOptions = useMemo(
    () =>
      (allClients ?? [])
        .filter((c) => c.id !== client?.id)
        .map((c) => ({ value: c.id, label: c.name })),
    [allClients, client?.id],
  );

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function toggleIn(
    key: "client_facilities" | "required_documents" | "submission_format_fields",
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

  const pending = createClient.isPending || updateClient.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!form.name.trim()) {
      setSection("business");
      setError("Client name is required.");
      return;
    }
    if (!isEdit && !form.website?.trim()) {
      setSection("business");
      setError("Website is required.");
      return;
    }

    // Empty strings mean "not provided" — send null so the column stays empty.
    const payload = Object.fromEntries(
      Object.entries(form).map(([k, v]) => [k, v === "" ? null : v]),
    ) as ClientCreateInput;
    payload.name = form.name.trim();

    try {
      if (isEdit && client) {
        await updateClient.mutateAsync(payload);
        router.push(`/clients/${client.id}`);
      } else {
        const created = await createClient.mutateAsync({
          ...payload,
          accounts,
          contacts,
          notes,
          assignments,
        });
        router.push(`/clients/${created.id}`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save client.");
    }
  }

  return (
    <AppShell
      title={isEdit ? `Edit ${client!.name}` : "New Client"}
      breadcrumbs={[
        { label: "Home", to: "/" },
        { label: "Clients", to: "/clients" },
        { label: isEdit ? "Edit" : "New" },
      ]}
      actions={
        <>
          <Button
            variant="outline"
            size="sm"
            type="button"
            onClick={() => router.push(isEdit ? `/clients/${client!.id}` : "/clients")}
          >
            Cancel
          </Button>
          <Button size="sm" form="client-form" type="submit" disabled={pending}>
            {pending ? (
              <>
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                Saving…
              </>
            ) : (
              "Save"
            )}
          </Button>
        </>
      }
    >
      <form id="client-form" onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6 items-start">
          {/* ---------- Section nav ---------- */}
          <Card className="lg:sticky lg:top-4">
            <CardContent className="p-2">
              <nav className="flex lg:flex-col gap-1 overflow-x-auto">
                {SECTIONS.map((s) => {
                  const Icon = s.icon;
                  const isActive = section === s.key;
                  return (
                    <button
                      key={s.key}
                      type="button"
                      onClick={() => setSection(s.key)}
                      className={cn(
                        "flex items-center gap-2 rounded-md px-3 py-2 text-sm text-left whitespace-nowrap transition-colors",
                        isActive
                          ? "bg-primary/10 text-primary font-medium"
                          : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      {s.label}
                    </button>
                  );
                })}
              </nav>
            </CardContent>
          </Card>

          {/* ---------- Section panel ---------- */}
          <div className="space-y-4 min-w-0">
            {error && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}

            {section === "business" && (
              <>
                <Card>
                  <CardContent className="p-5 space-y-4">
                    <h2 className="text-base font-semibold">Business Information</h2>
                    <div className="grid md:grid-cols-3 gap-4">
                      <Field label="Client Name" required>
                        <Input
                          value={form.name}
                          onChange={(e) => set("name", e.target.value)}
                          placeholder="Required"
                          required
                        />
                      </Field>
                      <Field label="Client Short Name">
                        <Input
                          value={form.short_name ?? ""}
                          onChange={(e) => set("short_name", e.target.value)}
                        />
                      </Field>
                      <Field label="VMS Client Name">
                        <Input
                          value={form.vms_client_name ?? ""}
                          onChange={(e) => set("vms_client_name", e.target.value)}
                        />
                      </Field>

                      <Field label="Website" required>
                        <Input
                          type="url"
                          value={form.website ?? ""}
                          onChange={(e) => set("website", e.target.value)}
                          placeholder="https://example.com"
                        />
                      </Field>
                      <Field label="Contact Number">
                        <Input
                          value={form.contact_number ?? ""}
                          onChange={(e) => set("contact_number", e.target.value)}
                        />
                      </Field>
                      <Field label="Email ID">
                        <Input
                          type="email"
                          value={form.email_id ?? ""}
                          onChange={(e) => set("email_id", e.target.value)}
                        />
                      </Field>

                      <Field label="Fax">
                        <Input
                          value={form.fax ?? ""}
                          onChange={(e) => set("fax", e.target.value)}
                        />
                      </Field>
                      <Field label="Federal ID">
                        <Input
                          value={form.federal_id ?? ""}
                          onChange={(e) => set("federal_id", e.target.value)}
                        />
                      </Field>
                      <Field label="Status" required>
                        <Select value={form.status} onValueChange={(v) => set("status", v)}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {CLIENT_STATUSES.map((s) => (
                              <SelectItem key={s} value={s}>
                                {s}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </Field>

                      <Field label="Industry">
                        <OptionalSelect
                          value={form.industry}
                          onChange={(v) => set("industry", v)}
                          placeholder="Select"
                          options={INDUSTRIES.map((i) => ({ value: i, label: i }))}
                        />
                      </Field>
                      <Field label="Category">
                        <OptionalSelect
                          value={form.category}
                          onChange={(v) => set("category", v)}
                          placeholder="Select"
                          options={CLIENT_CATEGORIES.map((c) => ({ value: c, label: c }))}
                        />
                      </Field>
                      <Field label="Practice">
                        <OptionalSelect
                          value={form.practice}
                          onChange={(v) => set("practice", v)}
                          placeholder="Select"
                          options={PRACTICES.map((p) => ({ value: p, label: p }))}
                        />
                      </Field>

                      <Field label="Payment Terms">
                        <OptionalSelect
                          value={form.payment_terms}
                          onChange={(v) => set("payment_terms", v)}
                          placeholder="Select"
                          options={PAYMENT_TERMS.map((p) => ({ value: p, label: p }))}
                        />
                      </Field>
                      <Field label="Child / Parent Client">
                        <OptionalSelect
                          value={form.parent_client_id}
                          onChange={(v) => set("parent_client_id", v)}
                          placeholder="Select parent client"
                          options={parentOptions}
                        />
                      </Field>
                      <Field label="Client Facilities">
                        <Input
                          readOnly
                          value={
                            form.client_facilities?.length
                              ? `${form.client_facilities.length} selected`
                              : "None selected"
                          }
                          className="cursor-default text-muted-foreground"
                        />
                      </Field>
                    </div>

                    <CheckboxGrid
                      options={CLIENT_FACILITY_OPTIONS}
                      selected={form.client_facilities ?? []}
                      onToggle={(o) => toggleIn("client_facilities", o)}
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-5 space-y-4">
                    <h2 className="text-base font-semibold">Address</h2>
                    <div className="grid md:grid-cols-3 gap-4">
                      <Field label="Address" className="md:col-span-3">
                        <Input
                          value={form.address ?? ""}
                          onChange={(e) => set("address", e.target.value)}
                        />
                      </Field>
                      <Field label="Country" required>
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
                      <Field label="State">
                        <Input
                          value={form.state ?? ""}
                          onChange={(e) => set("state", e.target.value)}
                        />
                      </Field>
                      <Field label="City">
                        <Input
                          value={form.city ?? ""}
                          onChange={(e) => set("city", e.target.value)}
                        />
                      </Field>
                      <Field label="Postal Code">
                        <Input
                          value={form.postal_code ?? ""}
                          onChange={(e) => set("postal_code", e.target.value)}
                        />
                      </Field>
                    </div>
                    <label className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={form.default_address_for_jobs}
                        onCheckedChange={(v) => set("default_address_for_jobs", Boolean(v))}
                      />
                      Make this address the default for jobs
                    </label>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-5 space-y-4">
                    <h2 className="text-base font-semibold">Ownership &amp; visibility</h2>
                    <div className="grid md:grid-cols-3 gap-4">
                      <Field label="Primary Business Unit">
                        <Input
                          value={form.primary_business_unit ?? ""}
                          onChange={(e) => set("primary_business_unit", e.target.value)}
                          placeholder="e.g. Peer Consulting Resources Inc."
                        />
                      </Field>
                      <Field label="Business Unit">
                        <Input
                          value={form.business_unit ?? ""}
                          onChange={(e) => set("business_unit", e.target.value)}
                        />
                      </Field>
                      <Field label="Client Visibility">
                        <RadioGroup
                          value={form.client_visibility}
                          onValueChange={(v) => set("client_visibility", v)}
                          className="flex gap-4 pt-2"
                        >
                          {CLIENT_VISIBILITIES.map((v) => (
                            <label key={v} className="flex items-center gap-2 text-sm">
                              <RadioGroupItem value={v} />
                              {v}
                            </label>
                          ))}
                        </RadioGroup>
                      </Field>

                      <Field label="Ownership">
                        <OptionalSelect
                          value={form.ownership_id}
                          onChange={(v) => set("ownership_id", v)}
                          placeholder="Select"
                          options={userOptions}
                        />
                      </Field>
                      <Field label="Primary Owner">
                        <OptionalSelect
                          value={form.primary_owner_id}
                          onChange={(v) => set("primary_owner_id", v)}
                          placeholder="Select"
                          options={userOptions}
                        />
                      </Field>
                      <Field label="Client Lead">
                        <OptionalSelect
                          value={form.client_lead_id}
                          onChange={(v) => set("client_lead_id", v)}
                          placeholder="Select"
                          options={userOptions}
                        />
                      </Field>
                    </div>

                    <div className="grid md:grid-cols-2 gap-3 pt-2">
                      <label className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={form.send_requirement}
                          onCheckedChange={(v) => set("send_requirement", Boolean(v))}
                        />
                        Send Requirement
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={form.send_hotlist}
                          onCheckedChange={(v) => set("send_hotlist", Boolean(v))}
                        />
                        Send Hotlist
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={form.allow_access_to_all_users}
                          onCheckedChange={(v) => set("allow_access_to_all_users", Boolean(v))}
                        />
                        Allow access to all users
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={form.notify_near_client_location}
                          onCheckedChange={(v) => set("notify_near_client_location", Boolean(v))}
                        />
                        Notify user when near the client location (mobile only)
                      </label>
                      <label className="flex items-center gap-2 text-sm md:col-span-2">
                        <Checkbox
                          checked={form.stop_contact_email_on_submit}
                          onCheckedChange={(v) => set("stop_contact_email_on_submit", Boolean(v))}
                        />
                        Stop sending email notifications to client contacts on Submit to Client
                      </label>
                      <div className="flex items-center gap-3 md:col-span-2 pt-1">
                        <Switch
                          checked={form.display_on_job_posting}
                          onCheckedChange={(v) => set("display_on_job_posting", v)}
                        />
                        <span className="text-sm">Display on Job Posting</span>
                        <Badge
                          variant={form.display_on_job_posting ? "secondary" : "outline"}
                          className="text-[11px]"
                        >
                          {form.display_on_job_posting ? "ON" : "OFF"}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-5 space-y-4">
                    <h2 className="text-base font-semibold">About Company</h2>
                    <Textarea
                      rows={6}
                      value={form.about_company ?? ""}
                      onChange={(e) => set("about_company", e.target.value)}
                      placeholder="Company overview shown on job postings…"
                    />
                  </CardContent>
                </Card>
              </>
            )}

            {section === "accounts" && (
              <RowEditor
                title="Accounts"
                description="Account-management contacts shown on the client snapshot."
                isEdit={isEdit}
                editHint="Accounts are managed from the client snapshot page."
                rows={accounts}
                onAdd={(row) => setAccounts((r) => [...r, row])}
                onRemove={(i) => setAccounts((r) => r.filter((_, idx) => idx !== i))}
                blank={{
                  contact_person: "",
                  email_id: "",
                  designation: "",
                  office_number: "",
                  mobile_number: "",
                }}
                fields={[
                  { key: "contact_person", label: "Contact person", required: true },
                  { key: "email_id", label: "Email ID" },
                  { key: "designation", label: "Designation" },
                  { key: "office_number", label: "Office number" },
                  { key: "mobile_number", label: "Mobile number" },
                ]}
                requiredKey="contact_person"
              />
            )}

            {section === "contacts" && (
              <RowEditor
                title="Contacts"
                description="Day-to-day contacts at this client."
                isEdit={isEdit}
                editHint="Contacts are managed from the client snapshot page."
                rows={contacts}
                onAdd={(row) => setContacts((r) => [...r, row])}
                onRemove={(i) => setContacts((r) => r.filter((_, idx) => idx !== i))}
                blank={{ name: "", email: "", title: "", phone: "" }}
                fields={[
                  { key: "name", label: "Name", required: true },
                  { key: "email", label: "Email" },
                  { key: "title", label: "Designation" },
                  { key: "phone", label: "Phone" },
                ]}
                requiredKey="name"
              />
            )}

            {section === "notes" && (
              <Card>
                <CardContent className="p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-semibold">Notes</h2>
                    <p className="text-sm text-muted-foreground">
                      {isEdit
                        ? "Notes are added from the client snapshot page."
                        : "Notes added here are saved with the new client."}
                    </p>
                  </div>
                  {!isEdit && (
                    <NoteEditor
                      notes={notes}
                      onAdd={(n) => setNotes((r) => [...r, n])}
                      onRemove={(i) => setNotes((r) => r.filter((_, idx) => idx !== i))}
                    />
                  )}
                </CardContent>
              </Card>
            )}

            {section === "documents" && (
              <Card>
                <CardContent className="p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-semibold">Documents</h2>
                    <p className="text-sm text-muted-foreground">
                      Choose which documents this client requires. Files are uploaded from the
                      client snapshot page once the client exists.
                    </p>
                  </div>
                  <CheckboxGrid
                    options={REQUIRED_DOCUMENT_OPTIONS}
                    selected={form.required_documents ?? []}
                    onToggle={(o) => toggleIn("required_documents", o)}
                  />
                </CardContent>
              </Card>
            )}

            {section === "guidelines" && (
              <Card>
                <CardContent className="p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-semibold">Guidelines</h2>
                    <p className="text-sm text-muted-foreground">
                      Working agreements, sourcing rules, and anything recruiters must follow for
                      this client.
                    </p>
                  </div>
                  <Textarea
                    rows={12}
                    value={form.guidelines ?? ""}
                    onChange={(e) => set("guidelines", e.target.value)}
                    placeholder="e.g. Do not submit candidates already in the client's ATS within 6 months…"
                  />
                </CardContent>
              </Card>
            )}

            {section === "assignment" && (
              <Card>
                <CardContent className="p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-semibold">Assignment</h2>
                    <p className="text-sm text-muted-foreground">
                      {isEdit
                        ? "Assignments are managed from the client snapshot page."
                        : "Assign the users who will work this account."}
                    </p>
                  </div>
                  {!isEdit && (
                    <AssignmentEditor
                      assignments={assignments}
                      userOptions={userOptions}
                      onAdd={(a) => setAssignments((r) => [...r, a])}
                      onRemove={(i) => setAssignments((r) => r.filter((_, idx) => idx !== i))}
                    />
                  )}
                </CardContent>
              </Card>
            )}

            {section === "markup" && (
              <Card>
                <CardContent className="p-5 space-y-4">
                  <h2 className="text-base font-semibold">Markup Calculation</h2>
                  <div className="grid md:grid-cols-3 gap-4">
                    <Field label="Standard markup (%)">
                      <Input
                        type="number"
                        step="0.01"
                        min={0}
                        value={form.markup_percentage ?? ""}
                        onChange={(e) => set("markup_percentage", e.target.value || null)}
                      />
                    </Field>
                    <Field label="Overtime markup (%)">
                      <Input
                        type="number"
                        step="0.01"
                        min={0}
                        value={form.overtime_markup_percentage ?? ""}
                        onChange={(e) => set("overtime_markup_percentage", e.target.value || null)}
                      />
                    </Field>
                    <Field label="Standard working hours / week">
                      <Input
                        type="number"
                        min={0}
                        value={form.standard_working_hours ?? ""}
                        onChange={(e) =>
                          set(
                            "standard_working_hours",
                            e.target.value ? Number(e.target.value) : null,
                          )
                        }
                      />
                    </Field>
                  </div>
                  <MarkupPreview
                    markup={Number(form.markup_percentage ?? 0)}
                    overtime={Number(form.overtime_markup_percentage ?? 0)}
                  />
                </CardContent>
              </Card>
            )}

            {section === "submission" && (
              <Card>
                <CardContent className="p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-semibold">Client Submission Format</h2>
                    <p className="text-sm text-muted-foreground">
                      Fields to include when submitting a candidate to this client.
                    </p>
                  </div>
                  <CheckboxGrid
                    options={SUBMISSION_FORMAT_OPTIONS}
                    selected={form.submission_format_fields ?? []}
                    onToggle={(o) => toggleIn("submission_format_fields", o)}
                  />
                  <Field label="Submission instructions">
                    <Textarea
                      rows={5}
                      value={form.submission_instructions ?? ""}
                      onChange={(e) => set("submission_instructions", e.target.value)}
                      placeholder="e.g. Email submissions to staffing@client.com with the req ID in the subject."
                    />
                  </Field>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </form>
    </AppShell>
  );
}

/** Generic "add rows before saving" editor used by the Accounts and Contacts sections. */
function RowEditor<T>({
  title,
  description,
  isEdit,
  editHint,
  rows,
  onAdd,
  onRemove,
  blank,
  fields,
  requiredKey,
}: {
  title: string;
  description: string;
  isEdit: boolean;
  editHint: string;
  rows: T[];
  onAdd: (row: T) => void;
  onRemove: (index: number) => void;
  blank: T;
  fields: { key: string; label: string; required?: boolean }[];
  requiredKey: string;
}) {
  const [draft, setDraft] = useState<T>(blank);
  const draftValues = draft as Record<string, string | undefined>;

  return (
    <Card>
      <CardContent className="p-5 space-y-4">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          <p className="text-sm text-muted-foreground">{isEdit ? editHint : description}</p>
        </div>

        {!isEdit && (
          <>
            <div className="grid md:grid-cols-5 gap-2">
              {fields.map((f) => (
                <Input
                  key={f.key}
                  placeholder={f.required ? `${f.label} *` : f.label}
                  value={draftValues[f.key] ?? ""}
                  onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
                />
              ))}
            </div>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="gap-1"
              disabled={!draftValues[requiredKey]?.trim()}
              onClick={() => {
                onAdd(draft);
                setDraft(blank);
              }}
            >
              <Plus className="h-4 w-4" />
              Add {title.toLowerCase().replace(/s$/, "")}
            </Button>

            {rows.length > 0 && (
              <div className="rounded-md border divide-y">
                {rows.map((row, i) => (
                  <div key={i} className="flex items-center gap-3 px-3 py-2 text-sm">
                    <span className="flex-1 truncate">
                      {fields
                        .map((f) => (row as Record<string, string | undefined>)[f.key])
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => onRemove(i)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function NoteEditor({
  notes,
  onAdd,
  onRemove,
}: {
  notes: ClientNoteInput[];
  onAdd: (note: ClientNoteInput) => void;
  onRemove: (index: number) => void;
}) {
  const [body, setBody] = useState("");
  const [noteType, setNoteType] = useState<string>("Client");

  return (
    <>
      <Textarea
        rows={3}
        placeholder="Write a note…"
        value={body}
        onChange={(e) => setBody(e.target.value)}
      />
      <div className="flex items-center gap-2">
        <Select value={noteType} onValueChange={setNoteType}>
          <SelectTrigger className="h-9 w-[220px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {CLIENT_NOTE_TYPES.map((t) => (
              <SelectItem key={t} value={t}>
                {t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="gap-1"
          disabled={!body.trim()}
          onClick={() => {
            onAdd({ body: body.trim(), note_type: noteType });
            setBody("");
          }}
        >
          <Plus className="h-4 w-4" />
          Add note
        </Button>
      </div>

      {notes.length > 0 && (
        <div className="rounded-md border divide-y">
          {notes.map((n, i) => (
            <div key={i} className="flex items-start gap-3 px-3 py-2 text-sm">
              <Badge variant="outline" className="text-[10px] mt-0.5">
                {n.note_type}
              </Badge>
              <span className="flex-1 whitespace-pre-wrap">{n.body}</span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => onRemove(i)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function AssignmentEditor({
  assignments,
  userOptions,
  onAdd,
  onRemove,
}: {
  assignments: ClientAssignmentInput[];
  userOptions: { value: string; label: string }[];
  onAdd: (assignment: ClientAssignmentInput) => void;
  onRemove: (index: number) => void;
}) {
  const [userId, setUserId] = useState<string | null>(null);
  const [role, setRole] = useState<string>(ASSIGNMENT_ROLES[0]);

  const labelFor = (id: string) => userOptions.find((u) => u.value === id)?.label ?? id;
  const available = userOptions.filter((u) => !assignments.some((a) => a.user_id === u.value));

  return (
    <>
      <div className="grid md:grid-cols-[1fr_220px_auto] gap-2">
        <OptionalSelect
          value={userId}
          onChange={setUserId}
          placeholder="Select user"
          options={available}
        />
        <Select value={role} onValueChange={setRole}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ASSIGNMENT_ROLES.map((r) => (
              <SelectItem key={r} value={r}>
                {r}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="gap-1"
          disabled={!userId}
          onClick={() => {
            if (!userId) return;
            onAdd({ user_id: userId, assignment_role: role });
            setUserId(null);
          }}
        >
          <Plus className="h-4 w-4" />
          Assign
        </Button>
      </div>

      {assignments.length > 0 && (
        <div className="rounded-md border divide-y">
          {assignments.map((a, i) => (
            <div key={a.user_id} className="flex items-center gap-3 px-3 py-2 text-sm">
              <span className="flex-1 truncate">{labelFor(a.user_id)}</span>
              <Badge variant="secondary" className="text-[11px]">
                {a.assignment_role}
              </Badge>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => onRemove(i)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

/** Shows what a sample bill rate becomes at the configured markup. */
function MarkupPreview({ markup, overtime }: { markup: number; overtime: number }) {
  const samplePayRate = 50;
  const bill = samplePayRate * (1 + markup / 100);
  const otBill = samplePayRate * 1.5 * (1 + overtime / 100);

  return (
    <div className="rounded-md border bg-muted/30 p-4 text-sm space-y-1">
      <div className="font-medium">Preview at a $50.00/hr pay rate</div>
      <div className="text-muted-foreground">
        Standard bill rate: <span className="font-mono text-foreground">${bill.toFixed(2)}/hr</span>
      </div>
      <div className="text-muted-foreground">
        Overtime bill rate (1.5×):{" "}
        <span className="font-mono text-foreground">${otBill.toFixed(2)}/hr</span>
      </div>
    </div>
  );
}
