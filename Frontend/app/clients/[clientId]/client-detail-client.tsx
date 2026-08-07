"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
  useAddClientAccount,
  useAddClientContact,
  useAddClientNote,
  useClient,
  useClientDocuments,
  useClientNotes,
} from "@/lib/hooks/use-clients";
import { CLIENT_NOTE_TYPES } from "@/lib/api/clients";
import { Building2, ExternalLink, Plus, Globe, Phone, Mail } from "lucide-react";
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
    : s === "Prospect"
      ? "bg-blue-50 text-blue-700 border-blue-200"
      : "bg-amber-50 text-amber-700 border-amber-200";
}

/** A label/value row in the right-hand Client Information rail. */
function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-sm font-medium break-words">{value || "N/A"}</div>
    </div>
  );
}

/** An empty-state-aware section table matching the snapshot layout. */
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

export function ClientDetailClient() {
  const params = useParams<{ clientId: string }>();
  const clientId = params.clientId;

  const { data: client, isLoading } = useClient(clientId);
  const { data: notes } = useClientNotes(clientId);
  const { data: documents } = useClientDocuments(clientId);
  const addNote = useAddClientNote(clientId);
  const addContact = useAddClientContact(clientId);
  const addAccount = useAddClientAccount(clientId);

  const [noteBody, setNoteBody] = useState("");
  const [noteType, setNoteType] = useState<string>("Client");
  const [noteFilter, setNoteFilter] = useState<string>("Client");
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [showContactForm, setShowContactForm] = useState(false);
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
    title: "",
    phone: "",
  });

  if (isLoading) {
    return (
      <AppShell title="Client">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </AppShell>
    );
  }

  if (!client) {
    return (
      <AppShell title="Client not found">
        <div className="text-sm text-muted-foreground">
          This client doesn&apos;t exist or you don&apos;t have access.{" "}
          <Link href="/clients" className="text-primary hover:underline">
            Back to clients
          </Link>
        </div>
      </AppShell>
    );
  }

  const location = [client.city, client.state, client.country].filter(Boolean).join(", ");
  const visibleNotes = (notes ?? []).filter((n) => n.note_type === noteFilter);

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!noteBody.trim()) return;
    await addNote.mutateAsync({ body: noteBody.trim(), note_type: noteType });
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
    setContactDraft({ name: "", email: "", title: "", phone: "" });
    setShowContactForm(false);
  }

  return (
    <AppShell
      title={client.name}
      breadcrumbs={[
        { label: "Home", to: "/" },
        { label: "Clients", to: "/clients" },
        { label: client.name },
      ]}
    >
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-6 items-start">
        {/* ---------- Main column ---------- */}
        <div className="space-y-6 min-w-0">
          <Card>
            <CardContent className="p-5">
              <div className="flex items-start gap-4">
                <Avatar className="h-12 w-12">
                  <AvatarFallback className="bg-primary/10 text-primary">
                    <Building2 className="h-6 w-6" />
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-semibold">{client.name}</h2>
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
                        statusTone(client.status),
                      )}
                    >
                      {client.status}
                    </span>
                    <Badge variant="outline" className="font-mono text-[10px]">
                      {client.client_code}
                    </Badge>
                  </div>

                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {client.email_id ?? "N/A"}
                    </span>
                    <span className="flex items-center gap-1">
                      <Phone className="h-3 w-3" />
                      {client.contact_number ?? "N/A"}
                    </span>
                    <span>{location || "N/A"}</span>
                  </div>

                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-xs">
                    {client.website && (
                      <a
                        href={client.website}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 text-primary hover:underline"
                      >
                        <Globe className="h-3 w-3" />
                        {client.website.replace(/^https?:\/\//, "")}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                    <span className="text-muted-foreground">
                      Business Unit: {client.primary_business_unit ?? "N/A"}
                    </span>
                  </div>

                  <div className="mt-1.5 text-xs text-muted-foreground">
                    Created By &amp; On — {client.created_by_name ?? "N/A"} ·{" "}
                    {formatDateTime(client.created_at)}
                  </div>

                  <div className="flex flex-wrap gap-2 mt-4">
                    <Button size="sm" variant="outline" asChild>
                      <Link href={`/clients/${client.id}/edit`}>Edit Client</Link>
                    </Button>
                    <Button size="sm" variant="outline" asChild>
                      <Link href="/jobs/new">Add Job</Link>
                    </Button>
                    <Badge variant="secondary" className="self-center text-[11px]">
                      {client.active_jobs} active jobs
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
              rows={client.accounts.map((a) => [
                a.contact_person,
                a.email_id ?? "—",
                a.designation ?? "—",
                a.office_number ?? "—",
                a.mobile_number ?? "—",
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
                  placeholder="Designation"
                  value={contactDraft.title}
                  onChange={(e) => setContactDraft({ ...contactDraft, title: e.target.value })}
                />
                <Input
                  placeholder="Phone"
                  value={contactDraft.phone}
                  onChange={(e) => setContactDraft({ ...contactDraft, phone: e.target.value })}
                />
                <Button type="submit" size="sm" disabled={addContact.isPending}>
                  Save
                </Button>
              </form>
            )}
            <SectionTable
              columns={["Name", "Email", "Designation", "Contacts", "Status"]}
              rows={client.contacts.map((c) => [
                c.name,
                c.email ?? "—",
                c.title ?? "—",
                c.phone ?? "—",
                <Badge key="s" variant="secondary" className="text-[11px]">
                  {c.status}
                </Badge>,
              ])}
            />
          </SectionCard>

          {/* Notes */}
          <SectionCard
            title="Notes"
            action={
              <div className="flex items-center gap-1">
                {CLIENT_NOTE_TYPES.map((t) => (
                  <Button
                    key={t}
                    size="sm"
                    variant={noteFilter === t ? "default" : "outline"}
                    className="h-7 text-[11px]"
                    onClick={() => setNoteFilter(t)}
                  >
                    {t}
                  </Button>
                ))}
              </div>
            }
          >
            <form onSubmit={handleAddNote} className="p-4 border-b space-y-2">
              <Textarea
                rows={2}
                placeholder="Add a note…"
                value={noteBody}
                onChange={(e) => setNoteBody(e.target.value)}
              />
              <div className="flex items-center gap-2">
                <Select value={noteType} onValueChange={setNoteType}>
                  <SelectTrigger className="h-8 w-[200px]">
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
                <Button type="submit" size="sm" disabled={addNote.isPending || !noteBody.trim()}>
                  Add note
                </Button>
              </div>
            </form>
            <SectionTable
              columns={["Added by / on", "Note", "Priority"]}
              rows={visibleNotes.map((n) => [
                <div key="a">
                  <div className="font-medium">{n.author_name ?? "—"}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatDateTime(n.created_at)}
                  </div>
                </div>,
                <span key="b" className="whitespace-pre-wrap">
                  {n.body}
                </span>,
                <Badge key="c" variant="outline" className="text-[11px]">
                  {n.priority}
                </Badge>,
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
        </div>

        {/* ---------- Client information rail ---------- */}
        <Card className="xl:sticky xl:top-4">
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <CardTitle className="text-base">Client Information</CardTitle>
            <Button size="sm" variant="ghost" asChild>
              <Link href={`/clients/${client.id}/edit`}>Edit</Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-4 max-h-[70vh] overflow-y-auto">
            <InfoRow label="Ownership" value={client.ownership_name} />
            <InfoRow label="Client Lead" value={client.client_lead_name} />
            <InfoRow label="Primary Owner" value={client.primary_owner_name} />
            <InfoRow label="Email ID" value={client.email_id} />
            <InfoRow label="Fax" value={client.fax} />
            <InfoRow label="Federal ID" value={client.federal_id} />
            <InfoRow label="VMS Client Name" value={client.vms_client_name} />
            <InfoRow label="Client Short Name" value={client.short_name} />
            <InfoRow label="Send Hotlist" value={client.send_hotlist ? "Yes" : "No"} />
            <InfoRow label="Send Requirement" value={client.send_requirement ? "Yes" : "No"} />
            <InfoRow
              label="Display on Job Posting"
              value={client.display_on_job_posting ? "Yes" : "No"}
            />
            <InfoRow label="Client Visibility" value={client.client_visibility} />
            <InfoRow label="Payment Terms" value={client.payment_terms} />
            <InfoRow label="Practice" value={client.practice} />
            <InfoRow label="Category" value={client.category} />
            <InfoRow label="Industry" value={client.industry} />
            <InfoRow label="Primary Business Unit" value={client.primary_business_unit} />
            <InfoRow label="Business Unit" value={client.business_unit} />
            <InfoRow label="Parent Client" value={client.parent_client_name} />
            <InfoRow
              label="Address"
              value={[client.address, location, client.postal_code].filter(Boolean).join(", ")}
            />
            <InfoRow label="Client Facilities" value={client.client_facilities.join(", ")} />
            <InfoRow label="Required Documents" value={client.required_documents.join(", ")} />
            <InfoRow
              label="Markup"
              value={client.markup_percentage ? `${client.markup_percentage}%` : null}
            />
            <InfoRow
              label="Modified By & On"
              value={`${client.updated_by_name ?? "N/A"} · ${formatDateTime(client.updated_at)}`}
            />
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
