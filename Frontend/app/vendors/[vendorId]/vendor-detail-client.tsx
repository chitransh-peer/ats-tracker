"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useAddVendorAccount,
  useAddVendorContact,
  useAddVendorMeeting,
  useAddVendorNote,
  useVendor,
  useVendorDocuments,
  useVendorMeetings,
  useVendorNotes,
} from "@/lib/hooks/use-vendors";
import { VENDOR_NOTE_ACTIONS, VMS_STATUSES } from "@/lib/api/vendors";
import { Truck, ExternalLink, Plus, Globe, Phone, Mail } from "lucide-react";
import { cn } from "@/lib/utils";

function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusTone(s: string) {
  return s === "Active"
    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : "bg-amber-50 text-amber-700 border-amber-200";
}

/** A label/value row in the right-hand Vendor Information rail. */
function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-sm font-medium break-words">{value || "N/A"}</div>
    </div>
  );
}

/** An ON/OFF pill, matching the toggle chips in the vendor information rail. */
function TogglePill({ label, on }: { label: string; on: boolean }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <Badge
        variant={on ? "secondary" : "outline"}
        className={cn("text-[10px]", on && "bg-emerald-50 text-emerald-700 border-emerald-200")}
      >
        {on ? "ON" : "OFF"}
      </Badge>
    </div>
  );
}

function SectionTable({
  columns,
  rows,
  emptyLabel = "No data available",
}: {
  columns: string[];
  rows: React.ReactNode[][];
  emptyLabel?: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-[11px] uppercase tracking-wide text-muted-foreground">
          <tr className="border-b">
            {columns.map((c) => (
              <th key={c} className="px-4 py-2.5 text-left font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-4 text-muted-foreground">
                {emptyLabel}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr key={i} className="border-b last:border-0 hover:bg-muted/30">
                {row.map((cell, j) => (
                  <td key={j} className="px-4 py-2.5 align-top">
                    {cell}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
      <div className="px-4 py-2 text-xs text-muted-foreground">
        Showing {rows.length === 0 ? 0 : 1} to {rows.length} of {rows.length} entries
      </div>
    </div>
  );
}

function SectionCard({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 py-4">
        <CardTitle className="text-base">{title}</CardTitle>
        {action}
      </CardHeader>
      <CardContent className="p-0">{children}</CardContent>
    </Card>
  );
}

export function VendorDetailClient() {
  const params = useParams<{ vendorId: string }>();
  const vendorId = params.vendorId;

  const { data: vendor, isLoading } = useVendor(vendorId);
  const { data: notes } = useVendorNotes(vendorId);
  const { data: documents } = useVendorDocuments(vendorId);
  const { data: meetings } = useVendorMeetings(vendorId);
  const addNote = useAddVendorNote(vendorId);
  const addContact = useAddVendorContact(vendorId);
  const addAccount = useAddVendorAccount(vendorId);
  const addMeeting = useAddVendorMeeting(vendorId);

  const [noteBody, setNoteBody] = useState("");
  const [noteAction, setNoteAction] = useState<string>("General");
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [showContactForm, setShowContactForm] = useState(false);
  const [showMeetingForm, setShowMeetingForm] = useState(false);
  const [accountDraft, setAccountDraft] = useState({
    contact_person: "",
    email_id: "",
    designation: "",
    office_number: "",
    mobile_number: "",
  });
  const [contactDraft, setContactDraft] = useState({
    name: "",
    email: "",
    work_phone: "",
    vms_status: "Not Initiated",
  });
  const [meetingDraft, setMeetingDraft] = useState({
    meeting_for: "",
    description: "",
    start_time: "",
    duration_minutes: "",
  });

  if (isLoading) {
    return (
      <AppShell title="Vendor">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </AppShell>
    );
  }

  if (!vendor) {
    return (
      <AppShell title="Vendor not found">
        <div className="text-sm text-muted-foreground">
          This vendor doesn&apos;t exist or you don&apos;t have access.{" "}
          <Link href="/vendors" className="text-primary hover:underline">
            Back to vendors
          </Link>
        </div>
      </AppShell>
    );
  }

  const location = [vendor.city, vendor.state, vendor.country].filter(Boolean).join(", ");

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!noteBody.trim()) return;
    await addNote.mutateAsync({ body: noteBody.trim(), action: noteAction });
    setNoteBody("");
  }

  async function handleAddAccount(e: React.FormEvent) {
    e.preventDefault();
    if (!accountDraft.contact_person.trim()) return;
    await addAccount.mutateAsync(accountDraft);
    setAccountDraft({
      contact_person: "",
      email_id: "",
      designation: "",
      office_number: "",
      mobile_number: "",
    });
    setShowAccountForm(false);
  }

  async function handleAddContact(e: React.FormEvent) {
    e.preventDefault();
    if (!contactDraft.name.trim()) return;
    await addContact.mutateAsync(contactDraft);
    setContactDraft({ name: "", email: "", work_phone: "", vms_status: "Not Initiated" });
    setShowContactForm(false);
  }

  async function handleAddMeeting(e: React.FormEvent) {
    e.preventDefault();
    if (!meetingDraft.meeting_for.trim()) return;
    await addMeeting.mutateAsync({
      meeting_for: meetingDraft.meeting_for,
      description: meetingDraft.description || null,
      start_time: meetingDraft.start_time ? new Date(meetingDraft.start_time).toISOString() : null,
      duration_minutes: meetingDraft.duration_minutes
        ? Number(meetingDraft.duration_minutes)
        : null,
    });
    setMeetingDraft({ meeting_for: "", description: "", start_time: "", duration_minutes: "" });
    setShowMeetingForm(false);
  }

  return (
    <AppShell
      title={vendor.name}
      breadcrumbs={[
        { label: "Home", to: "/" },
        { label: "Vendors", to: "/vendors" },
        { label: vendor.name },
      ]}
      actions={
        <Button size="sm" variant="outline" asChild>
          <Link href={`/vendors/${vendor.id}/edit`}>Edit</Link>
        </Button>
      }
    >
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-6 items-start">
        {/* ---------- Main column ---------- */}
        <div className="space-y-6 min-w-0">
          <Card>
            <CardContent className="p-5">
              <div className="flex items-start gap-4">
                <div className="h-12 w-12 rounded-md bg-primary/10 text-primary grid place-items-center shrink-0">
                  <Truck className="h-6 w-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-semibold">{vendor.name}</h2>
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
                        statusTone(vendor.status),
                      )}
                    >
                      {vendor.status}
                    </span>
                    {vendor.primary_vendor && (
                      <Badge variant="secondary" className="text-[10px]">
                        Primary vendor
                      </Badge>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {vendor.email_id ?? "N/A"}
                    </span>
                    <span className="flex items-center gap-1">
                      <Phone className="h-3 w-3" />
                      {vendor.contact_number ?? "N/A"}
                    </span>
                    <span>{location || "N/A"}</span>
                  </div>

                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-xs">
                    {vendor.website && (
                      <a
                        href={vendor.website}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 text-primary hover:underline"
                      >
                        <Globe className="h-3 w-3" />
                        {vendor.website.replace(/^https?:\/\//, "")}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                    <span className="text-muted-foreground">
                      Business Unit: {vendor.primary_business_unit ?? "N/A"}
                    </span>
                  </div>

                  <div className="mt-1.5 text-xs text-muted-foreground">
                    Created By &amp; On — {vendor.created_by_name ?? "N/A"} ·{" "}
                    {formatDateTime(vendor.created_at)}
                  </div>

                  <div className="flex flex-wrap gap-2 mt-4">
                    <Button size="sm" variant="outline" asChild>
                      <Link href={`/vendors/${vendor.id}/edit`}>Edit Vendor</Link>
                    </Button>
                    <Badge variant="secondary" className="self-center text-[11px]">
                      {vendor.active_submissions} active submissions
                    </Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Accounts */}
          <SectionCard
            title="Accounts"
            action={
              <Button size="sm" className="gap-1" onClick={() => setShowAccountForm((v) => !v)}>
                <Plus className="h-4 w-4" />
                Add
              </Button>
            }
          >
            {showAccountForm && (
              <form onSubmit={handleAddAccount} className="grid md:grid-cols-5 gap-2 p-4 border-b">
                <Input
                  placeholder="Contact person"
                  value={accountDraft.contact_person}
                  onChange={(e) =>
                    setAccountDraft({ ...accountDraft, contact_person: e.target.value })
                  }
                  required
                />
                <Input
                  placeholder="Email ID"
                  value={accountDraft.email_id}
                  onChange={(e) => setAccountDraft({ ...accountDraft, email_id: e.target.value })}
                />
                <Input
                  placeholder="Designation"
                  value={accountDraft.designation}
                  onChange={(e) =>
                    setAccountDraft({ ...accountDraft, designation: e.target.value })
                  }
                />
                <Input
                  placeholder="Office number"
                  value={accountDraft.office_number}
                  onChange={(e) =>
                    setAccountDraft({ ...accountDraft, office_number: e.target.value })
                  }
                />
                <div className="flex gap-2">
                  <Input
                    placeholder="Mobile number"
                    value={accountDraft.mobile_number}
                    onChange={(e) =>
                      setAccountDraft({ ...accountDraft, mobile_number: e.target.value })
                    }
                  />
                  <Button type="submit" size="sm" disabled={addAccount.isPending}>
                    Save
                  </Button>
                </div>
              </form>
            )}
            <SectionTable
              columns={[
                "Contact person",
                "Email ID",
                "Designation",
                "Office number",
                "Mobile number",
              ]}
              rows={vendor.accounts.map((a) => [
                a.contact_person,
                a.email_id ?? "—",
                a.designation ?? "—",
                a.office_number ?? "—",
                a.mobile_number ?? "—",
              ])}
            />
          </SectionCard>

          {/* Notes */}
          <SectionCard title="Notes">
            <form onSubmit={handleAddNote} className="p-4 border-b space-y-2">
              <Textarea
                rows={2}
                placeholder="Add a note…"
                value={noteBody}
                onChange={(e) => setNoteBody(e.target.value)}
              />
              <div className="flex items-center gap-2">
                <Select value={noteAction} onValueChange={setNoteAction}>
                  <SelectTrigger className="h-8 w-[180px]">
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
                <Button type="submit" size="sm" disabled={addNote.isPending || !noteBody.trim()}>
                  Add note
                </Button>
              </div>
            </form>
            <SectionTable
              columns={["Added by / date", "Action", "Note", "Notified people"]}
              rows={(notes ?? []).map((n) => [
                <div key="a">
                  <div className="font-medium">{n.author_name ?? "—"}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatDateTime(n.created_at)}
                  </div>
                </div>,
                <Badge key="b" variant="outline" className="text-[11px]">
                  {n.action ?? "—"}
                </Badge>,
                <span key="c" className="whitespace-pre-wrap">
                  {n.body}
                </span>,
                n.notified_people.length ? n.notified_people.join(", ") : "—",
              ])}
            />
          </SectionCard>

          {/* Contacts */}
          <SectionCard
            title="Contacts"
            action={
              <Button size="sm" className="gap-1" onClick={() => setShowContactForm((v) => !v)}>
                <Plus className="h-4 w-4" />
                Add
              </Button>
            }
          >
            {showContactForm && (
              <form onSubmit={handleAddContact} className="grid md:grid-cols-5 gap-2 p-4 border-b">
                <Input
                  placeholder="Name"
                  value={contactDraft.name}
                  onChange={(e) => setContactDraft({ ...contactDraft, name: e.target.value })}
                  required
                />
                <Input
                  placeholder="Email"
                  value={contactDraft.email}
                  onChange={(e) => setContactDraft({ ...contactDraft, email: e.target.value })}
                />
                <Input
                  placeholder="Work phone"
                  value={contactDraft.work_phone}
                  onChange={(e) => setContactDraft({ ...contactDraft, work_phone: e.target.value })}
                />
                <Select
                  value={contactDraft.vms_status}
                  onValueChange={(v) => setContactDraft({ ...contactDraft, vms_status: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {VMS_STATUSES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button type="submit" size="sm" disabled={addContact.isPending}>
                  Save
                </Button>
              </form>
            )}
            <SectionTable
              columns={["Name / Email", "Work phone", "Status", "VMS status", "Owner"]}
              rows={vendor.contacts.map((c) => [
                <div key="n">
                  <div className="font-medium">{c.name}</div>
                  <div className="text-xs text-muted-foreground">{c.email ?? "—"}</div>
                </div>,
                c.work_phone ?? c.phone ?? "—",
                <Badge key="s" variant="secondary" className="text-[11px]">
                  {c.status}
                </Badge>,
                <Badge key="v" variant="outline" className="text-[11px]">
                  {c.vms_status}
                </Badge>,
                c.owner_name ?? "—",
              ])}
            />
          </SectionCard>

          {/* Documents */}
          <SectionCard title="Documents">
            <SectionTable
              columns={["File name", "Type", "Size", "Uploaded on"]}
              rows={(documents ?? []).map((d) => [
                d.file_name,
                d.content_type,
                `${Math.round(d.size_bytes / 1024)} KB`,
                formatDateTime(d.created_at),
              ])}
            />
          </SectionCard>

          {/* Meeting Schedules */}
          <SectionCard
            title="Meeting Schedules"
            action={
              <Button size="sm" className="gap-1" onClick={() => setShowMeetingForm((v) => !v)}>
                <Plus className="h-4 w-4" />
                Add
              </Button>
            }
          >
            {showMeetingForm && (
              <form onSubmit={handleAddMeeting} className="grid md:grid-cols-5 gap-2 p-4 border-b">
                <Input
                  placeholder="Meeting for"
                  value={meetingDraft.meeting_for}
                  onChange={(e) =>
                    setMeetingDraft({ ...meetingDraft, meeting_for: e.target.value })
                  }
                  required
                />
                <Input
                  placeholder="Description"
                  value={meetingDraft.description}
                  onChange={(e) =>
                    setMeetingDraft({ ...meetingDraft, description: e.target.value })
                  }
                />
                <Input
                  type="datetime-local"
                  value={meetingDraft.start_time}
                  onChange={(e) => setMeetingDraft({ ...meetingDraft, start_time: e.target.value })}
                />
                <Input
                  type="number"
                  min={0}
                  placeholder="Duration (min)"
                  value={meetingDraft.duration_minutes}
                  onChange={(e) =>
                    setMeetingDraft({ ...meetingDraft, duration_minutes: e.target.value })
                  }
                />
                <Button type="submit" size="sm" disabled={addMeeting.isPending}>
                  Save
                </Button>
              </form>
            )}
            <SectionTable
              columns={[
                "Meeting for",
                "Contacts",
                "Description",
                "Attendees",
                "Guest attendees",
                "Start time / duration",
                "Created by",
              ]}
              rows={(meetings ?? []).map((m) => [
                m.meeting_for,
                m.contact_name ?? "—",
                m.description ?? "—",
                m.attendee_names.length ? m.attendee_names.join(", ") : "—",
                m.guest_attendees.length ? m.guest_attendees.join(", ") : "—",
                <span key="t">
                  {formatDateTime(m.start_time)}
                  {m.duration_minutes ? ` · ${m.duration_minutes} min` : ""}
                </span>,
                m.created_by_name ?? "—",
              ])}
            />
          </SectionCard>
        </div>

        {/* ---------- Vendor information rail ---------- */}
        <Card className="xl:sticky xl:top-4">
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <CardTitle className="text-base">Vendor Information</CardTitle>
            <Button size="sm" variant="ghost" asChild>
              <Link href={`/vendors/${vendor.id}/edit`}>Edit</Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-4 max-h-[70vh] overflow-y-auto">
            <InfoRow label="Primary Owner" value={vendor.primary_owner_name} />
            <InfoRow label="Ownership" value={vendor.ownership_name} />
            <InfoRow label="Primary Business Unit" value={vendor.primary_business_unit} />
            <InfoRow label="Vendor Lead" value={vendor.vendor_lead_name} />
            <InfoRow label="Fax" value={vendor.fax} />
            <InfoRow label="Federal ID" value={vendor.federal_id} />
            <TogglePill label="Send Requirement" on={vendor.send_requirement} />
            <TogglePill label="Primary Vendor" on={vendor.primary_vendor} />
            <TogglePill label="Send Hotlist" on={vendor.send_hotlist} />
            <InfoRow label="Technologies" value={vendor.technologies.join(", ")} />
            <InfoRow label="Payment Terms" value={vendor.payment_terms} />
            <InfoRow label="Vendor Type" value={vendor.vendor_type} />
            <InfoRow label="About Vendor" value={vendor.about_vendor} />
            <InfoRow label="Vendor Classification" value={vendor.vendor_classification} />
            <InfoRow label="Vendor Visibility" value={vendor.vendor_visibility} />
            <InfoRow label="Business Units" value={vendor.business_units.join(", ")} />
            <InfoRow label="Specialization" value={vendor.specialization} />
            <InfoRow
              label="Address"
              value={[vendor.address, location, vendor.zip_code].filter(Boolean).join(", ")}
            />
            <InfoRow
              label="Bank accounts"
              value={
                vendor.bank_accounts.length
                  ? vendor.bank_accounts
                      .map((b) => `${b.bank_name} ••••${b.account_number.slice(-4)}`)
                      .join(", ")
                  : null
              }
            />
            <InfoRow
              label="Modified By & On"
              value={`${vendor.updated_by_name ?? "N/A"} · ${formatDateTime(vendor.updated_at)}`}
            />
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
