"use client";

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useTemplates,
  useCreateTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
} from "@/lib/hooks/use-templates";
import { ApiError } from "@/lib/api/client";
import type { Template } from "@/lib/api/types";
import { Plus, Search, Mail, Copy, Trash2 } from "lucide-react";
import { cn, relativeTime } from "@/lib/utils";

const TEMPLATE_TYPES = [
  "Interview Invite",
  "Offer",
  "Rejection",
  "Follow-up",
  "Acknowledgment",
] as const;

const typeTone: Record<string, string> = {
  Acknowledgment: "bg-slate-100 text-slate-700 border-slate-200",
  "Interview Invite": "bg-violet-50 text-violet-700 border-violet-200",
  Offer: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Rejection: "bg-red-50 text-red-700 border-red-200",
  "Follow-up": "bg-blue-50 text-blue-700 border-blue-200",
};

const TOKENS = [
  "{{candidate_first_name}}",
  "{{candidate_full_name}}",
  "{{job_title}}",
  "{{company}}",
  "{{recruiter_name}}",
  "{{interview_time}}",
  "{{offer_link}}",
];

function NewTemplateDialog({ onCreated }: { onCreated: (t: Template) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState<string>(TEMPLATE_TYPES[0]);
  const [subject, setSubject] = useState("");
  const [error, setError] = useState<string | null>(null);
  const createTemplate = useCreateTemplate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const created = await createTemplate.mutateAsync({
        name,
        type,
        subject,
        body: "Hi {{candidate_first_name}},\n\n",
      });
      onCreated(created);
      setOpen(false);
      setName("");
      setSubject("");
      setType(TEMPLATE_TYPES[0]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create template.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1">
          <Plus className="h-4 w-4" />
          New template
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New template</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="space-y-1.5">
            <Label className="text-xs">Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Type</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TEMPLATE_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Subject</Label>
            <Input value={subject} onChange={(e) => setSubject(e.target.value)} required />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createTemplate.isPending}>
              {createTemplate.isPending ? "Creating…" : "Create template"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function TemplatesClient() {
  const { data: templates, isLoading } = useTemplates();
  const updateTemplate = useUpdateTemplate();
  const deleteTemplate = useDeleteTemplate();
  const createTemplate = useCreateTemplate();

  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<{ name: string; type: string; subject: string; body: string }>(
    {
      name: "",
      type: "",
      subject: "",
      body: "",
    },
  );
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const filtered = useMemo(() => {
    const list = templates ?? [];
    if (!query.trim()) return list;
    const q = query.toLowerCase();
    return list.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.type.toLowerCase().includes(q) ||
        t.subject.toLowerCase().includes(q),
    );
  }, [templates, query]);

  const selected = (templates ?? []).find((t) => t.id === selectedId) ?? null;

  // Default to the first template, and recover if the selected one is filtered
  // away or deleted underneath us.
  useEffect(() => {
    if (!templates?.length) return;
    if (!selectedId || !templates.some((t) => t.id === selectedId)) {
      setSelectedId(templates[0].id);
    }
  }, [templates, selectedId]);

  // Reload the editor whenever a different template is selected.
  useEffect(() => {
    if (!selected) return;
    setDraft({
      name: selected.name,
      type: selected.type,
      subject: selected.subject,
      body: selected.body,
    });
    setError(null);
    setSaved(false);
  }, [selected?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const isDirty =
    selected != null &&
    (draft.name !== selected.name ||
      draft.type !== selected.type ||
      draft.subject !== selected.subject ||
      draft.body !== selected.body);

  async function handleSave() {
    if (!selected) return;
    setError(null);
    try {
      await updateTemplate.mutateAsync({ templateId: selected.id, input: draft });
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save template.");
    }
  }

  async function handleDuplicate() {
    if (!selected) return;
    setError(null);
    try {
      const copy = await createTemplate.mutateAsync({
        name: `${selected.name} (copy)`,
        type: selected.type,
        subject: selected.subject,
        body: selected.body,
      });
      setSelectedId(copy.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to duplicate template.");
    }
  }

  async function handleDelete() {
    if (!selected) return;
    if (!window.confirm(`Delete "${selected.name}"? This cannot be undone.`)) return;
    setError(null);
    try {
      await deleteTemplate.mutateAsync(selected.id);
      setSelectedId(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete template.");
    }
  }

  return (
    <AppShell
      title="Email Templates"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Templates" }]}
      actions={<NewTemplateDialog onCreated={(t) => setSelectedId(t.id)} />}
    >
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        <Card className="h-fit">
          <CardHeader className="pb-2">
            <div className="relative">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search templates…"
                className="pl-9 h-9"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </CardHeader>
          <CardContent className="p-2">
            {isLoading ? (
              <div className="space-y-2 p-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : filtered.length === 0 ? (
              <p className="p-4 text-center text-sm text-muted-foreground">
                {templates?.length ? "No templates match your search." : "No templates yet."}
              </p>
            ) : (
              <ul className="space-y-1">
                {filtered.map((t) => (
                  <li key={t.id}>
                    <button
                      onClick={() => setSelectedId(t.id)}
                      className={cn(
                        "w-full text-left px-3 py-2 rounded-md text-sm transition-colors",
                        selectedId === t.id ? "bg-muted" : "hover:bg-muted/60",
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span className="font-medium truncate">{t.name}</span>
                      </div>
                      <div className="mt-1 flex items-center justify-between gap-2">
                        <span
                          className={cn(
                            "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium",
                            typeTone[t.type] ?? typeTone.Acknowledgment,
                          )}
                        >
                          {t.type}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {relativeTime(t.updated_at)}
                        </span>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {selected == null ? (
          <Card>
            <CardContent className="grid min-h-[320px] place-items-center text-center">
              <div>
                <Mail className="mx-auto h-8 w-8 text-muted-foreground" />
                <p className="mt-3 text-sm text-muted-foreground">
                  {templates?.length
                    ? "Select a template to edit it."
                    : "Create your first email template to get started."}
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-3 flex-wrap">
              <div className="min-w-0">
                <CardTitle className="text-base truncate">{selected.name}</CardTitle>
                <div className="mt-1 flex items-center gap-2">
                  <Badge
                    variant="secondary"
                    className={cn(
                      "text-[10px]",
                      typeTone[selected.type] ?? typeTone.Acknowledgment,
                    )}
                  >
                    {selected.type}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    Updated {relativeTime(selected.updated_at)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={handleDuplicate}
                  disabled={createTemplate.isPending}
                >
                  <Copy className="h-4 w-4" />
                  Duplicate
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1 text-destructive"
                  onClick={handleDelete}
                  disabled={deleteTemplate.isPending}
                >
                  <Trash2 className="h-4 w-4" />
                  Delete
                </Button>
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={!isDirty || updateTemplate.isPending}
                >
                  {updateTemplate.isPending ? "Saving…" : "Save changes"}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {error && <div className="text-sm text-destructive">{error}</div>}
              {saved && !isDirty && (
                <div className="text-sm text-[color:var(--color-success)]">Template saved.</div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-[1fr_220px] gap-3">
                <div>
                  <Label>Name</Label>
                  <Input
                    value={draft.name}
                    onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label>Type</Label>
                  <Select value={draft.type} onValueChange={(v) => setDraft({ ...draft, type: v })}>
                    <SelectTrigger className="mt-1.5">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TEMPLATE_TYPES.map((t) => (
                        <SelectItem key={t} value={t}>
                          {t}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label>Subject</Label>
                <Input
                  value={draft.subject}
                  onChange={(e) => setDraft({ ...draft, subject: e.target.value })}
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label>Body</Label>
                <Textarea
                  value={draft.body}
                  onChange={(e) => setDraft({ ...draft, body: e.target.value })}
                  className="mt-1.5 min-h-[260px] font-mono text-sm"
                />
              </div>
              <div className="rounded-md border border-border bg-muted/30 p-3 text-xs">
                <div className="font-medium mb-2 text-foreground">
                  Available tokens — click to insert at the end of the body
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {TOKENS.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setDraft((d) => ({ ...d, body: d.body + t }))}
                      className="rounded bg-background border border-border px-1.5 py-0.5 font-mono hover:bg-muted"
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
