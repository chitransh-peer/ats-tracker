"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useHotlist,
  useHotlistSends,
  useUpdateHotlist,
  useSetHotlistMembers,
  useAddRecipients,
  useAddRecipientsFromParties,
  useImportRecipients,
  useRemoveRecipient,
  useSetRecipientUnsubscribed,
  useSendHotlist,
} from "@/lib/hooks/use-hotlists";
import { useBenchProfiles } from "@/lib/hooks/use-bench";
import { useClients } from "@/lib/hooks/use-clients";
import { useVendors } from "@/lib/hooks/use-vendors";
import { useTemplates } from "@/lib/hooks/use-templates";
import { useEmailStatus } from "@/lib/hooks/use-settings";
import { exportHotlist, downloadRecipientTemplate } from "@/lib/api/hotlists";
import { ApiError } from "@/lib/api/client";
import type { RecipientImportResult } from "@/lib/api/types";
import { cn, formatDateTime, relativeTime } from "@/lib/utils";
import { Download, Upload, Send, Trash2, Ban, CheckCircle2, AlertTriangle } from "lucide-react";

export function HotlistDetailClient() {
  const params = useParams<{ hotlistId: string }>();
  const hotlistId = params.hotlistId;

  const { data: hotlist, isLoading } = useHotlist(hotlistId);
  const { data: sends } = useHotlistSends(hotlistId);
  const { data: bench } = useBenchProfiles({ status: "Active Bench" });
  const { data: clients } = useClients();
  const { data: vendors } = useVendors();
  const { data: templates } = useTemplates();
  const { data: emailStatus } = useEmailStatus();

  const update = useUpdateHotlist(hotlistId);
  const setMembers = useSetHotlistMembers(hotlistId);
  const addRecipients = useAddRecipients(hotlistId);
  const addFromParties = useAddRecipientsFromParties(hotlistId);
  const importRecipients = useImportRecipients(hotlistId);
  const removeRecipient = useRemoveRecipient(hotlistId);
  const setUnsubscribed = useSetRecipientUnsubscribed(hotlistId);
  const send = useSendHotlist(hotlistId);

  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [importResult, setImportResult] = useState<RecipientImportResult | null>(null);
  const [manualEmail, setManualEmail] = useState("");
  const [manualFirst, setManualFirst] = useState("");
  const [manualCompany, setManualCompany] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  // Load the composer once the hotlist arrives.
  useEffect(() => {
    if (!hotlist) return;
    setSubject(hotlist.subject ?? "");
    setBody(hotlist.body ?? "");
  }, [hotlist?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (isLoading) {
    return (
      <AppShell title="Hotlist">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </AppShell>
    );
  }

  if (!hotlist) {
    return (
      <AppShell title="Hotlist not found">
        <div className="text-sm text-muted-foreground">
          This hotlist doesn&apos;t exist or you don&apos;t have access.{" "}
          <Link href="/hotlists" className="text-primary hover:underline">
            Back to hotlists
          </Link>
        </div>
      </AppShell>
    );
  }

  const memberIds = new Set(hotlist.members.map((m) => m.bench_profile_id));
  const activeRecipients = hotlist.recipients.filter((r) => !r.unsubscribed);
  const canSend = hotlist.members.length > 0 && activeRecipients.length > 0 && !!subject.trim();

  async function run(action: () => Promise<unknown>, failure: string) {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : failure);
    }
  }

  async function toggleMember(benchProfileId: string) {
    const next = memberIds.has(benchProfileId)
      ? hotlist!.members.map((m) => m.bench_profile_id).filter((id) => id !== benchProfileId)
      : [...hotlist!.members.map((m) => m.bench_profile_id), benchProfileId];
    await run(() => setMembers.mutateAsync(next), "Could not update the consultant list.");
  }

  async function handleSaveEmail() {
    setSaved(false);
    await run(async () => {
      await update.mutateAsync({ subject: subject || null, body: body || null });
      setSaved(true);
    }, "Could not save the email.");
  }

  async function handleImport(file: File) {
    setImportResult(null);
    await run(async () => {
      const result = await importRecipients.mutateAsync(file);
      setImportResult(result);
    }, "Could not import that spreadsheet.");
  }

  function applyTemplate(templateId: string) {
    const template = (templates ?? []).find((t) => t.id === templateId);
    if (!template) return;
    setSubject(template.subject);
    setBody(template.body);
    void run(
      () =>
        update.mutateAsync({
          template_id: templateId,
          subject: template.subject,
          body: template.body,
        }),
      "Could not apply the template.",
    );
  }

  return (
    <AppShell
      title={hotlist.name}
      breadcrumbs={[
        { label: "Home", to: "/" },
        { label: "Hotlists", to: "/hotlists" },
        { label: hotlist.name },
      ]}
      actions={
        <>
          <Button
            variant="outline"
            size="sm"
            onClick={() => run(() => exportHotlist(hotlist.id, hotlist.name), "Download failed.")}
            disabled={hotlist.members.length === 0}
          >
            <Download className="h-4 w-4 mr-1.5" />
            Export sheet
          </Button>
          <Button
            size="sm"
            disabled={!canSend || send.isPending}
            onClick={() =>
              window.confirm(
                `Send "${hotlist.name}" with ${hotlist.members.length} consultant(s) to ${activeRecipients.length} recipient(s)?`,
              ) && run(() => send.mutateAsync(), "Could not queue the send.")
            }
          >
            <Send className="h-4 w-4 mr-1.5" />
            {send.isPending ? "Queueing…" : "Send hotlist"}
          </Button>
        </>
      }
    >
      {error && <div className="mb-4 text-sm text-destructive">{error}</div>}

      {emailStatus && !emailStatus.enabled && (
        <div className="mb-4 flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>
            Email delivery isn&apos;t configured, so sending will record the attempt but transmit
            nothing. You can still export the spreadsheet and send it by hand.
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-6">
        <div>
          <Tabs defaultValue="consultants">
            <TabsList>
              <TabsTrigger value="consultants">Consultants ({hotlist.members.length})</TabsTrigger>
              <TabsTrigger value="recipients">Recipients ({hotlist.recipients.length})</TabsTrigger>
              <TabsTrigger value="email">Email</TabsTrigger>
              <TabsTrigger value="history">History ({(sends ?? []).length})</TabsTrigger>
            </TabsList>

            {/* ---------------------------------------------------- consultants */}
            <TabsContent value="consultants" className="mt-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Pick from the bench</CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Active bench consultants you can see. Longest-benched appear first — they are
                    the ones most in need of marketing.
                  </p>
                </CardHeader>
                <CardContent className="p-0">
                  {(bench ?? []).length === 0 ? (
                    <p className="p-6 text-center text-sm text-muted-foreground">
                      No active bench consultants.{" "}
                      <Link href="/talent-bench" className="text-primary hover:underline">
                        Add someone to the bench
                      </Link>
                      .
                    </p>
                  ) : (
                    <ul className="divide-y">
                      {[...(bench ?? [])]
                        .sort((a, b) => b.bench_age_days - a.bench_age_days)
                        .map((p) => (
                          <li key={p.id} className="flex items-center gap-3 px-5 py-3">
                            <Checkbox
                              checked={memberIds.has(p.id)}
                              onCheckedChange={() => toggleMember(p.id)}
                              aria-label={`Include ${p.full_name}`}
                            />
                            <div className="min-w-0 flex-1">
                              <div className="text-sm font-medium truncate">{p.full_name}</div>
                              <div className="text-xs text-muted-foreground truncate">
                                {p.marketing_title ?? p.current_title ?? "—"}
                                {p.work_auth ? ` · ${p.work_auth}` : ""}
                              </div>
                            </div>
                            <Badge variant="secondary" className="text-[10px] shrink-0">
                              {p.bench_age_days}d on bench
                            </Badge>
                          </li>
                        ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* ----------------------------------------------------- recipients */}
            <TabsContent value="recipients" className="mt-4 space-y-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Import from a spreadsheet</CardTitle>
                  <p className="text-xs text-muted-foreground">
                    An .xlsx with First Name, Last Name and Email. Column names are matched loosely,
                    so &ldquo;Mail ID&rdquo; and &ldquo;Surname&rdquo; work too.
                  </p>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    <input
                      ref={fileInput}
                      type="file"
                      accept=".xlsx,.xlsm"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) void handleImport(file);
                        e.target.value = "";
                      }}
                    />
                    <Button
                      size="sm"
                      onClick={() => fileInput.current?.click()}
                      disabled={importRecipients.isPending}
                    >
                      <Upload className="h-4 w-4 mr-1.5" />
                      {importRecipients.isPending ? "Importing…" : "Upload recipient list"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        run(() => downloadRecipientTemplate(), "Could not download the template.")
                      }
                    >
                      <Download className="h-4 w-4 mr-1.5" />
                      Blank template
                    </Button>
                  </div>

                  {importResult && (
                    <div className="rounded-md border bg-muted/30 p-3 text-xs">
                      <div className="font-medium">
                        Added {importResult.added} of {importResult.parsed} rows
                        {importResult.skipped > 0 && ` · ${importResult.skipped} skipped`}
                      </div>
                      {importResult.problems.length > 0 && (
                        <ul className="mt-2 space-y-0.5 text-muted-foreground">
                          {importResult.problems.slice(0, 8).map((p) => (
                            <li key={p}>· {p}</li>
                          ))}
                          {importResult.problems.length > 8 && (
                            <li>· and {importResult.problems.length - 8} more…</li>
                          )}
                        </ul>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Add from your records</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1.5">
                      <Label className="text-xs">Client</Label>
                      <Select
                        onValueChange={(id) =>
                          run(
                            () => addFromParties.mutateAsync({ client_ids: [id] }),
                            "Could not add those contacts.",
                          )
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Add all contacts…" />
                        </SelectTrigger>
                        <SelectContent>
                          {(clients ?? []).map((c) => (
                            <SelectItem key={c.id} value={c.id}>
                              {c.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Vendor</Label>
                      <Select
                        onValueChange={(id) =>
                          run(
                            () => addFromParties.mutateAsync({ vendor_ids: [id] }),
                            "Could not add those contacts.",
                          )
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Add vendor contact…" />
                        </SelectTrigger>
                        <SelectContent>
                          {(vendors ?? []).map((v) => (
                            <SelectItem key={v.id} value={v.id}>
                              {v.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <form
                    className="grid gap-2 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void run(async () => {
                        await addRecipients.mutateAsync([
                          {
                            first_name: manualFirst || null,
                            email: manualEmail,
                            company: manualCompany || null,
                          },
                        ]);
                        setManualEmail("");
                        setManualFirst("");
                        setManualCompany("");
                      }, "Could not add that recipient.");
                    }}
                  >
                    <div className="space-y-1.5">
                      <Label className="text-xs">First name</Label>
                      <Input value={manualFirst} onChange={(e) => setManualFirst(e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Email</Label>
                      <Input
                        type="email"
                        required
                        value={manualEmail}
                        onChange={(e) => setManualEmail(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Company</Label>
                      <Input
                        value={manualCompany}
                        onChange={(e) => setManualCompany(e.target.value)}
                      />
                    </div>
                    <Button type="submit" size="sm" disabled={addRecipients.isPending}>
                      Add
                    </Button>
                  </form>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">
                    Recipient list
                    <span className="ml-2 text-xs font-normal text-muted-foreground">
                      {activeRecipients.length} will receive it
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  {hotlist.recipients.length === 0 ? (
                    <p className="p-6 text-center text-sm text-muted-foreground">
                      No recipients yet.
                    </p>
                  ) : (
                    <ul className="divide-y">
                      {hotlist.recipients.map((r) => (
                        <li key={r.id} className="flex items-center gap-3 px-5 py-2.5">
                          <div className="min-w-0 flex-1">
                            <div
                              className={cn(
                                "text-sm truncate",
                                r.unsubscribed && "line-through text-muted-foreground",
                              )}
                            >
                              {[r.first_name, r.last_name].filter(Boolean).join(" ") || r.email}
                            </div>
                            <div className="text-xs text-muted-foreground truncate">
                              {r.email}
                              {r.company ? ` · ${r.company}` : ""}
                            </div>
                          </div>
                          <Badge variant="outline" className="text-[10px] shrink-0 capitalize">
                            {r.kind}
                          </Badge>
                          <Button
                            variant="ghost"
                            size="sm"
                            title={r.unsubscribed ? "Resubscribe" : "Unsubscribe"}
                            onClick={() =>
                              run(
                                () =>
                                  setUnsubscribed.mutateAsync({
                                    recipientId: r.id,
                                    unsubscribed: !r.unsubscribed,
                                  }),
                                "Could not update this recipient.",
                              )
                            }
                          >
                            <Ban
                              className={cn(
                                "h-4 w-4",
                                r.unsubscribed ? "text-destructive" : "text-muted-foreground",
                              )}
                            />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              run(
                                () => removeRecipient.mutateAsync(r.id),
                                "Could not remove this recipient.",
                              )
                            }
                          >
                            <Trash2 className="h-4 w-4 text-muted-foreground" />
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* ---------------------------------------------------------- email */}
            <TabsContent value="email" className="mt-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Covering email</CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Each recipient is greeted by their first name where known. The spreadsheet is
                    attached automatically.
                  </p>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs">Start from a template</Label>
                    <Select onValueChange={applyTemplate}>
                      <SelectTrigger>
                        <SelectValue placeholder="Compose from scratch" />
                      </SelectTrigger>
                      <SelectContent>
                        {(templates ?? []).map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.name} ({t.type})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Subject</Label>
                    <Input value={subject} onChange={(e) => setSubject(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Message</Label>
                    <Textarea
                      rows={9}
                      value={body}
                      onChange={(e) => setBody(e.target.value)}
                      placeholder="Please find our available consultants attached…"
                    />
                  </div>
                  <div className="flex items-center gap-3">
                    <Button size="sm" onClick={handleSaveEmail} disabled={update.isPending}>
                      {update.isPending ? "Saving…" : "Save email"}
                    </Button>
                    {saved && (
                      <span className="inline-flex items-center gap-1 text-xs text-[color:var(--color-success)]">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Saved
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* -------------------------------------------------------- history */}
            <TabsContent value="history" className="mt-4">
              <Card>
                <CardContent className="p-0">
                  {(sends ?? []).length === 0 ? (
                    <p className="p-6 text-center text-sm text-muted-foreground">
                      This hotlist hasn&apos;t been sent yet.
                    </p>
                  ) : (
                    <ul className="divide-y">
                      {(sends ?? []).map((s) => (
                        <li key={s.id} className="px-5 py-3">
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <div className="text-sm font-medium truncate">{s.subject}</div>
                              <div className="text-xs text-muted-foreground">
                                {formatDateTime(s.created_at)} · {s.member_count} consultants
                              </div>
                            </div>
                            <Badge
                              variant={s.status === "completed" ? "secondary" : "outline"}
                              className="text-[10px] shrink-0 capitalize"
                            >
                              {s.status}
                            </Badge>
                          </div>
                          <div className="mt-1.5 text-xs text-muted-foreground">
                            {s.sent_count} sent
                            {s.failed_count > 0 && (
                              <span className="text-destructive"> · {s.failed_count} failed</span>
                            )}
                          </div>
                          {s.error_message && (
                            <div className="mt-1 text-xs text-destructive">{s.error_message}</div>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* ------------------------------------------------------------ sidebar */}
        <aside className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Ready to send?</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {[
                { label: "Consultants added", ok: hotlist.members.length > 0 },
                { label: "Recipients added", ok: activeRecipients.length > 0 },
                { label: "Subject written", ok: !!subject.trim() },
              ].map((check) => (
                <div key={check.label} className="flex items-center gap-2">
                  <span
                    className={cn(
                      "grid h-4 w-4 place-items-center rounded-full text-[10px] font-bold",
                      check.ok
                        ? "bg-[color:var(--color-success)] text-white"
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    {check.ok ? "✓" : ""}
                  </span>
                  <span className={check.ok ? "" : "text-muted-foreground"}>{check.label}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">What goes in the sheet</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium">Attach spreadsheet</div>
                  <p className="text-xs text-muted-foreground">Sends the .xlsx with the email.</p>
                </div>
                <Switch
                  checked={hotlist.attach_spreadsheet}
                  onCheckedChange={(v) =>
                    run(
                      () => update.mutateAsync({ attach_spreadsheet: v }),
                      "Could not change that setting.",
                    )
                  }
                />
              </div>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium">Include rates</div>
                  <p className="text-xs text-muted-foreground">Desired rate and tax term.</p>
                </div>
                <Switch
                  checked={hotlist.include_rates}
                  onCheckedChange={(v) =>
                    run(
                      () => update.mutateAsync({ include_rates: v }),
                      "Could not change that setting.",
                    )
                  }
                />
              </div>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium">Include consultant email</div>
                  <p className="text-xs text-muted-foreground">
                    Off by default — sharing contact details lets recipients approach your
                    consultants directly.
                  </p>
                </div>
                <Switch
                  checked={hotlist.include_candidate_contact}
                  onCheckedChange={(v) =>
                    run(
                      () => update.mutateAsync({ include_candidate_contact: v }),
                      "Could not change that setting.",
                    )
                  }
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-xs text-muted-foreground">
              <div>
                Status: <span className="text-foreground">{hotlist.status}</span>
              </div>
              <div>Created {relativeTime(hotlist.created_at)}</div>
              <div>Updated {relativeTime(hotlist.updated_at)}</div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </AppShell>
  );
}
