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
import { useCreateVendor, useUpdateVendor } from "@/lib/hooks/use-vendors";
import { useUsers } from "@/lib/hooks/use-users";
import {
  BANK_ACCOUNT_TYPES,
  TECHNOLOGY_OPTIONS,
  VENDOR_CLASSIFICATIONS,
  VENDOR_NOTE_ACTIONS,
  VENDOR_PAYMENT_TERMS,
  VENDOR_STATUSES,
  VENDOR_SUBMISSION_FORMAT_OPTIONS,
  VENDOR_TYPES,
  VENDOR_VISIBILITIES,
  VMS_STATUSES,
} from "@/lib/api/vendors";
import { COUNTRIES } from "@/lib/api/clients";
import { ApiError } from "@/lib/api/client";
import type {
  Vendor,
  VendorAccountInput,
  VendorBankAccountInput,
  VendorContactInput,
  VendorCreateInput,
  VendorNoteInput,
} from "@/lib/api/types";
import {
  Building2,
  Users,
  StickyNote,
  Contact,
  Table2,
  FolderOpen,
  Landmark,
  Loader2,
  Trash2,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";

const SECTIONS = [
  { key: "business", label: "Business Information", icon: Building2 },
  { key: "accounts", label: "Accounts", icon: Users },
  { key: "notes", label: "Notes", icon: StickyNote },
  { key: "contacts", label: "Contacts", icon: Contact },
  { key: "submission", label: "Vendor Submission Format", icon: Table2 },
  { key: "documents", label: "Documents", icon: FolderOpen },
  { key: "bank", label: "Bank Account Details", icon: Landmark },
] as const;

type SectionKey = (typeof SECTIONS)[number]["key"];

const NONE = "__none__";

type FormState = VendorCreateInput & { name: string };

function initialState(vendor?: Vendor): FormState {
  return {
    name: vendor?.name ?? "",
    specialization: vendor?.specialization ?? "",
    status: vendor?.status ?? "Active",
    federal_id: vendor?.federal_id ?? "",
    website: vendor?.website ?? "",
    contact_number: vendor?.contact_number ?? "",
    email_id: vendor?.email_id ?? "",
    fax: vendor?.fax ?? "",
    vendor_type: vendor?.vendor_type ?? "",
    vendor_classification: vendor?.vendor_classification ?? "",
    payment_terms: vendor?.payment_terms ?? "",
    about_vendor: vendor?.about_vendor ?? "",
    address: vendor?.address ?? "",
    city: vendor?.city ?? "",
    state: vendor?.state ?? "",
    country: vendor?.country ?? "United States",
    zip_code: vendor?.zip_code ?? "",
    primary_business_unit: vendor?.primary_business_unit ?? "",
    business_units: vendor?.business_units ?? [],
    vendor_visibility: vendor?.vendor_visibility ?? "Organization Level",
    primary_owner_id: vendor?.primary_owner_id ?? null,
    ownership_id: vendor?.ownership_id ?? null,
    vendor_lead_id: vendor?.vendor_lead_id ?? null,
    send_requirement: vendor?.send_requirement ?? false,
    send_hotlist: vendor?.send_hotlist ?? false,
    primary_vendor: vendor?.primary_vendor ?? false,
    allow_access_to_all_users: vendor?.allow_access_to_all_users ?? false,
    technologies: vendor?.technologies ?? [],
    submission_format_fields: vendor?.submission_format_fields ?? [],
    submission_instructions: vendor?.submission_instructions ?? "",
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

export function VendorForm({ vendor }: { vendor?: Vendor }) {
  const router = useRouter();
  const isEdit = Boolean(vendor);
  const createVendor = useCreateVendor();
  const updateVendor = useUpdateVendor(vendor?.id ?? "");
  const { data: users } = useUsers();

  const [section, setSection] = useState<SectionKey>("business");
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(() => initialState(vendor));
  const [businessUnitDraft, setBusinessUnitDraft] = useState("");

  // Nested rows are only collected on create; on edit they are managed from the snapshot page.
  const [accounts, setAccounts] = useState<VendorAccountInput[]>([]);
  const [contacts, setContacts] = useState<VendorContactInput[]>([]);
  const [notes, setNotes] = useState<VendorNoteInput[]>([]);
  const [bankAccounts, setBankAccounts] = useState<VendorBankAccountInput[]>([]);

  const userOptions = useMemo(
    () => (users ?? []).map((u) => ({ value: u.id, label: `${u.full_name} (${u.email})` })),
    [users],
  );

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function toggleIn(key: "technologies" | "submission_format_fields", option: string) {
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

  const pending = createVendor.isPending || updateVendor.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!form.name.trim()) {
      setSection("business");
      setError("Vendor name is required.");
      return;
    }

    // Empty strings mean "not provided" — send null so the column stays empty.
    const payload = Object.fromEntries(
      Object.entries(form).map(([k, v]) => [k, v === "" ? null : v]),
    ) as VendorCreateInput;
    payload.name = form.name.trim();

    try {
      if (isEdit && vendor) {
        await updateVendor.mutateAsync(payload);
        router.push(`/vendors/${vendor.id}`);
      } else {
        const created = await createVendor.mutateAsync({
          ...payload,
          accounts,
          contacts,
          notes,
          bank_accounts: bankAccounts,
        });
        router.push(`/vendors/${created.id}`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save vendor.");
    }
  }

  return (
    <AppShell
      title={isEdit ? `Edit ${vendor!.name}` : "Add Vendor"}
      breadcrumbs={[
        { label: "Home", to: "/" },
        { label: "Vendors", to: "/vendors" },
        { label: isEdit ? "Edit" : "New" },
      ]}
      actions={
        <>
          <Button
            variant="outline"
            size="sm"
            type="button"
            onClick={() => router.push(isEdit ? `/vendors/${vendor!.id}` : "/vendors")}
          >
            Cancel
          </Button>
          <Button size="sm" form="vendor-form" type="submit" disabled={pending}>
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
      <form id="vendor-form" onSubmit={handleSubmit}>
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
                      <Field label="Vendor Name" required>
                        <Input
                          value={form.name}
                          onChange={(e) => set("name", e.target.value)}
                          placeholder="Required"
                          required
                        />
                      </Field>
                      <Field label="Federal ID">
                        <Input
                          value={form.federal_id ?? ""}
                          onChange={(e) => set("federal_id", e.target.value)}
                        />
                      </Field>
                      <Field label="Website">
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

                      <Field label="Vendor Type">
                        <OptionalSelect
                          value={form.vendor_type}
                          onChange={(v) => set("vendor_type", v)}
                          placeholder="Select"
                          options={VENDOR_TYPES.map((t) => ({ value: t, label: t }))}
                        />
                      </Field>
                      <Field label="Vendor Classification">
                        <OptionalSelect
                          value={form.vendor_classification}
                          onChange={(v) => set("vendor_classification", v)}
                          placeholder="Select"
                          options={VENDOR_CLASSIFICATIONS.map((c) => ({ value: c, label: c }))}
                        />
                      </Field>
                      <Field label="Status" required>
                        <Select value={form.status} onValueChange={(v) => set("status", v)}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {VENDOR_STATUSES.map((s) => (
                              <SelectItem key={s} value={s}>
                                {s}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </Field>

                      <Field label="Payment Terms">
                        <OptionalSelect
                          value={form.payment_terms}
                          onChange={(v) => set("payment_terms", v)}
                          placeholder="Select"
                          options={VENDOR_PAYMENT_TERMS.map((p) => ({ value: p, label: p }))}
                        />
                      </Field>
                      <Field label="Specialization">
                        <Input
                          value={form.specialization ?? ""}
                          onChange={(e) => set("specialization", e.target.value)}
                          placeholder="e.g. Engineering"
                        />
                      </Field>
                    </div>

                    <Field label="Technologies">
                      <CheckboxGrid
                        options={TECHNOLOGY_OPTIONS}
                        selected={form.technologies ?? []}
                        onToggle={(o) => toggleIn("technologies", o)}
                      />
                    </Field>
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
                      <Field label="Zip Code">
                        <Input
                          value={form.zip_code ?? ""}
                          onChange={(e) => set("zip_code", e.target.value)}
                        />
                      </Field>
                    </div>
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
                      <Field label="Vendor Visibility">
                        <RadioGroup
                          value={form.vendor_visibility}
                          onValueChange={(v) => set("vendor_visibility", v)}
                          className="flex gap-4 pt-2"
                        >
                          {VENDOR_VISIBILITIES.map((v) => (
                            <label key={v} className="flex items-center gap-2 text-sm">
                              <RadioGroupItem value={v} />
                              {v}
                            </label>
                          ))}
                        </RadioGroup>
                      </Field>
                      <Field label="Business Units">
                        <div className="flex gap-2">
                          <Input
                            value={businessUnitDraft}
                            onChange={(e) => setBusinessUnitDraft(e.target.value)}
                            placeholder="Add a business unit"
                          />
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            disabled={!businessUnitDraft.trim()}
                            onClick={() => {
                              const value = businessUnitDraft.trim();
                              if (!form.business_units?.includes(value)) {
                                set("business_units", [...(form.business_units ?? []), value]);
                              }
                              setBusinessUnitDraft("");
                            }}
                          >
                            Add
                          </Button>
                        </div>
                      </Field>
                    </div>

                    {(form.business_units?.length ?? 0) > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {form.business_units?.map((bu) => (
                          <Badge key={bu} variant="secondary" className="gap-1 text-[11px]">
                            {bu}
                            <button
                              type="button"
                              onClick={() =>
                                set(
                                  "business_units",
                                  (form.business_units ?? []).filter((v) => v !== bu),
                                )
                              }
                              className="hover:text-destructive"
                            >
                              ×
                            </button>
                          </Badge>
                        ))}
                      </div>
                    )}

                    <div className="grid md:grid-cols-3 gap-4">
                      <Field label="Primary Owner">
                        <OptionalSelect
                          value={form.primary_owner_id}
                          onChange={(v) => set("primary_owner_id", v)}
                          placeholder="Select"
                          options={userOptions}
                        />
                      </Field>
                      <Field label="Ownership">
                        <OptionalSelect
                          value={form.ownership_id}
                          onChange={(v) => set("ownership_id", v)}
                          placeholder="Select"
                          options={userOptions}
                        />
                      </Field>
                      <Field label="Vendor Lead">
                        <OptionalSelect
                          value={form.vendor_lead_id}
                          onChange={(v) => set("vendor_lead_id", v)}
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
                          checked={form.primary_vendor}
                          onCheckedChange={(v) => set("primary_vendor", Boolean(v))}
                        />
                        Primary vendor
                      </label>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-5 space-y-4">
                    <h2 className="text-base font-semibold">About Vendor</h2>
                    <Textarea
                      rows={6}
                      value={form.about_vendor ?? ""}
                      onChange={(e) => set("about_vendor", e.target.value)}
                      placeholder="Vendor overview, coverage, and strengths…"
                    />
                  </CardContent>
                </Card>
              </>
            )}

            {section === "accounts" && (
              <RowEditor
                title="Accounts"
                description="Account-management contacts shown on the vendor snapshot."
                isEdit={isEdit}
                editHint="Accounts are managed from the vendor snapshot page."
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
              <Card>
                <CardContent className="p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-semibold">Contacts</h2>
                    <p className="text-sm text-muted-foreground">
                      {isEdit
                        ? "Contacts are managed from the vendor snapshot page."
                        : "Day-to-day contacts at this vendor."}
                    </p>
                  </div>
                  {!isEdit && (
                    <ContactEditor
                      contacts={contacts}
                      userOptions={userOptions}
                      onAdd={(c) => setContacts((r) => [...r, c])}
                      onRemove={(i) => setContacts((r) => r.filter((_, idx) => idx !== i))}
                    />
                  )}
                </CardContent>
              </Card>
            )}

            {section === "notes" && (
              <Card>
                <CardContent className="p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-semibold">Notes</h2>
                    <p className="text-sm text-muted-foreground">
                      {isEdit
                        ? "Notes are added from the vendor snapshot page."
                        : "Notes added here are saved with the new vendor."}
                    </p>
                  </div>
                  {!isEdit && (
                    <NoteEditor
                      notes={notes}
                      userOptions={userOptions}
                      onAdd={(n) => setNotes((r) => [...r, n])}
                      onRemove={(i) => setNotes((r) => r.filter((_, idx) => idx !== i))}
                    />
                  )}
                </CardContent>
              </Card>
            )}

            {section === "submission" && (
              <Card>
                <CardContent className="p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-semibold">Vendor Submission Format</h2>
                    <p className="text-sm text-muted-foreground">
                      Fields to include when this vendor submits a candidate.
                    </p>
                  </div>
                  <CheckboxGrid
                    options={VENDOR_SUBMISSION_FORMAT_OPTIONS}
                    selected={form.submission_format_fields ?? []}
                    onToggle={(o) => toggleIn("submission_format_fields", o)}
                  />
                  <Field label="Submission instructions">
                    <Textarea
                      rows={5}
                      value={form.submission_instructions ?? ""}
                      onChange={(e) => set("submission_instructions", e.target.value)}
                      placeholder="e.g. Submit through the vendor portal with the req ID in the subject."
                    />
                  </Field>
                </CardContent>
              </Card>
            )}

            {section === "documents" && (
              <Card>
                <CardContent className="p-5 space-y-3">
                  <h2 className="text-base font-semibold">Documents</h2>
                  <p className="text-sm text-muted-foreground">
                    {isEdit
                      ? "Upload documents from the vendor snapshot page."
                      : "Documents can be uploaded from the vendor snapshot page once the vendor is saved."}
                  </p>
                  {isEdit && (
                    <Button type="button" size="sm" variant="outline" asChild>
                      <a href={`/vendors/${vendor!.id}`}>Go to vendor snapshot</a>
                    </Button>
                  )}
                </CardContent>
              </Card>
            )}

            {section === "bank" && (
              <Card>
                <CardContent className="p-5 space-y-4">
                  <div>
                    <h2 className="text-base font-semibold">Bank Account Details</h2>
                    <p className="text-sm text-muted-foreground">
                      {isEdit
                        ? "Bank accounts are managed from the vendor snapshot page."
                        : "Payment details used when settling vendor invoices."}
                    </p>
                  </div>
                  {!isEdit && (
                    <BankAccountEditor
                      accounts={bankAccounts}
                      onAdd={(a) => setBankAccounts((r) => [...r, a])}
                      onRemove={(i) => setBankAccounts((r) => r.filter((_, idx) => idx !== i))}
                    />
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </form>
    </AppShell>
  );
}

/** Generic "add rows before saving" editor used by the Accounts section. */
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

function ContactEditor({
  contacts,
  userOptions,
  onAdd,
  onRemove,
}: {
  contacts: VendorContactInput[];
  userOptions: { value: string; label: string }[];
  onAdd: (contact: VendorContactInput) => void;
  onRemove: (index: number) => void;
}) {
  const [draft, setDraft] = useState<VendorContactInput>({
    name: "",
    email: "",
    work_phone: "",
    designation: "",
    vms_status: "Not Initiated",
    owner_id: null,
  });

  return (
    <>
      <div className="grid md:grid-cols-3 gap-2">
        <Input
          placeholder="Name *"
          value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
        />
        <Input
          placeholder="Email"
          value={draft.email ?? ""}
          onChange={(e) => setDraft({ ...draft, email: e.target.value })}
        />
        <Input
          placeholder="Work phone"
          value={draft.work_phone ?? ""}
          onChange={(e) => setDraft({ ...draft, work_phone: e.target.value })}
        />
        <Input
          placeholder="Designation"
          value={draft.designation ?? ""}
          onChange={(e) => setDraft({ ...draft, designation: e.target.value })}
        />
        <Select
          value={draft.vms_status ?? "Not Initiated"}
          onValueChange={(v) => setDraft({ ...draft, vms_status: v })}
        >
          <SelectTrigger>
            <SelectValue placeholder="VMS status" />
          </SelectTrigger>
          <SelectContent>
            {VMS_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <OptionalSelect
          value={draft.owner_id}
          onChange={(v) => setDraft({ ...draft, owner_id: v })}
          placeholder="Owner"
          options={userOptions}
        />
      </div>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="gap-1"
        disabled={!draft.name.trim()}
        onClick={() => {
          onAdd(draft);
          setDraft({
            name: "",
            email: "",
            work_phone: "",
            designation: "",
            vms_status: "Not Initiated",
            owner_id: null,
          });
        }}
      >
        <Plus className="h-4 w-4" />
        Add contact
      </Button>

      {contacts.length > 0 && (
        <div className="rounded-md border divide-y">
          {contacts.map((c, i) => (
            <div key={i} className="flex items-center gap-3 px-3 py-2 text-sm">
              <span className="flex-1 truncate">
                {[c.name, c.email, c.work_phone].filter(Boolean).join(" · ")}
              </span>
              <Badge variant="outline" className="text-[11px]">
                {c.vms_status}
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

function NoteEditor({
  notes,
  userOptions,
  onAdd,
  onRemove,
}: {
  notes: VendorNoteInput[];
  userOptions: { value: string; label: string }[];
  onAdd: (note: VendorNoteInput) => void;
  onRemove: (index: number) => void;
}) {
  const [body, setBody] = useState("");
  const [action, setAction] = useState<string>("General");
  const [notified, setNotified] = useState<string[]>([]);

  return (
    <>
      <Textarea
        rows={3}
        placeholder="Write a note…"
        value={body}
        onChange={(e) => setBody(e.target.value)}
      />
      <div className="grid md:grid-cols-[200px_1fr_auto] gap-2">
        <Select value={action} onValueChange={setAction}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {VENDOR_NOTE_ACTIONS.map((a) => (
              <SelectItem key={a} value={a}>
                {a}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <OptionalSelect
          value={null}
          onChange={(v) => {
            if (v && !notified.includes(v)) setNotified([...notified, v]);
          }}
          placeholder="Notify people"
          options={userOptions.filter((u) => !notified.includes(u.value))}
        />
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="gap-1"
          disabled={!body.trim()}
          onClick={() => {
            onAdd({ body: body.trim(), action, notified_user_ids: notified });
            setBody("");
            setNotified([]);
          }}
        >
          <Plus className="h-4 w-4" />
          Add note
        </Button>
      </div>

      {notified.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {notified.map((id) => (
            <Badge key={id} variant="secondary" className="gap-1 text-[11px]">
              {userOptions.find((u) => u.value === id)?.label ?? id}
              <button
                type="button"
                onClick={() => setNotified(notified.filter((v) => v !== id))}
                className="hover:text-destructive"
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
      )}

      {notes.length > 0 && (
        <div className="rounded-md border divide-y">
          {notes.map((n, i) => (
            <div key={i} className="flex items-start gap-3 px-3 py-2 text-sm">
              <Badge variant="outline" className="text-[10px] mt-0.5">
                {n.action}
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

function BankAccountEditor({
  accounts,
  onAdd,
  onRemove,
}: {
  accounts: VendorBankAccountInput[];
  onAdd: (account: VendorBankAccountInput) => void;
  onRemove: (index: number) => void;
}) {
  const blank: VendorBankAccountInput = {
    account_holder_name: "",
    bank_name: "",
    account_number: "",
    account_type: "Checking",
    routing_number: "",
    swift_code: "",
    branch_address: "",
    is_primary: false,
  };
  const [draft, setDraft] = useState<VendorBankAccountInput>(blank);

  const complete =
    draft.account_holder_name.trim() && draft.bank_name.trim() && draft.account_number.trim();

  return (
    <>
      <div className="grid md:grid-cols-3 gap-3">
        <Field label="Account holder name" required>
          <Input
            value={draft.account_holder_name}
            onChange={(e) => setDraft({ ...draft, account_holder_name: e.target.value })}
          />
        </Field>
        <Field label="Bank name" required>
          <Input
            value={draft.bank_name}
            onChange={(e) => setDraft({ ...draft, bank_name: e.target.value })}
          />
        </Field>
        <Field label="Account number" required>
          <Input
            value={draft.account_number}
            onChange={(e) => setDraft({ ...draft, account_number: e.target.value })}
          />
        </Field>
        <Field label="Account type">
          <Select
            value={draft.account_type ?? "Checking"}
            onValueChange={(v) => setDraft({ ...draft, account_type: v })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {BANK_ACCOUNT_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Routing number">
          <Input
            value={draft.routing_number ?? ""}
            onChange={(e) => setDraft({ ...draft, routing_number: e.target.value })}
          />
        </Field>
        <Field label="SWIFT code">
          <Input
            value={draft.swift_code ?? ""}
            onChange={(e) => setDraft({ ...draft, swift_code: e.target.value })}
          />
        </Field>
        <Field label="Branch address" className="md:col-span-2">
          <Input
            value={draft.branch_address ?? ""}
            onChange={(e) => setDraft({ ...draft, branch_address: e.target.value })}
          />
        </Field>
        <Field label="Effective from">
          <Input
            type="date"
            value={draft.effective_from ?? ""}
            onChange={(e) => setDraft({ ...draft, effective_from: e.target.value })}
          />
        </Field>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <Checkbox
          checked={draft.is_primary}
          onCheckedChange={(v) => setDraft({ ...draft, is_primary: Boolean(v) })}
        />
        Primary account
      </label>

      <Button
        type="button"
        size="sm"
        variant="outline"
        className="gap-1"
        disabled={!complete}
        onClick={() => {
          onAdd(draft);
          setDraft(blank);
        }}
      >
        <Plus className="h-4 w-4" />
        Add bank account
      </Button>

      {accounts.length > 0 && (
        <div className="rounded-md border divide-y">
          {accounts.map((a, i) => (
            <div key={i} className="flex items-center gap-3 px-3 py-2 text-sm">
              <span className="flex-1 truncate">
                {a.bank_name} · {a.account_holder_name} · ••••{a.account_number.slice(-4)}
              </span>
              {a.is_primary && (
                <Badge variant="secondary" className="text-[11px]">
                  Primary
                </Badge>
              )}
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
