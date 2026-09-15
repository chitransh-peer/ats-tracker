"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useHotlists, useCreateHotlist, useDeleteHotlist } from "@/lib/hooks/use-hotlists";
import { ApiError } from "@/lib/api/client";
import { cn, relativeTime } from "@/lib/utils";
import { Plus, Trash2, Users, Send } from "lucide-react";

const statusTone: Record<string, string> = {
  Draft: "bg-slate-100 text-slate-700 border-slate-200",
  Ready: "bg-blue-50 text-blue-700 border-blue-200",
  Sent: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Archived: "bg-slate-100 text-slate-500 border-slate-200",
};

function NewHotlistDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [subject, setSubject] = useState("");
  const [error, setError] = useState<string | null>(null);
  const create = useCreateHotlist();
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const created = await create.mutateAsync({ name, subject: subject || null });
      setOpen(false);
      setName("");
      setSubject("");
      // Straight into the builder — a hotlist is useless until it has members.
      router.push(`/hotlists/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the hotlist.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1">
          <Plus className="h-4 w-4" />
          New hotlist
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New hotlist</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="space-y-1.5">
            <Label className="text-xs">Name</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Java consultants — March"
              required
            />
            <p className="text-[11px] text-muted-foreground">
              Internal only, and used as the attachment filename.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Email subject</Label>
            <Input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="e.g. 6 available Java consultants — immediate start"
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={!name.trim() || create.isPending}>
              {create.isPending ? "Creating…" : "Create and add consultants"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function HotlistsClient() {
  const { data: hotlists, isLoading } = useHotlists();
  const remove = useDeleteHotlist();

  const rows = hotlists ?? [];
  const sentCount = rows.filter((h) => h.status === "Sent").length;
  const draftCount = rows.filter((h) => h.status === "Draft").length;

  async function handleDelete(id: string, name: string) {
    if (!window.confirm(`Delete "${name}"? Its send history goes with it.`)) return;
    await remove.mutateAsync(id);
  }

  return (
    <AppShell
      title="Hotlists"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Hotlists" }]}
      actions={
        <>
          <Button variant="outline" size="sm" asChild>
            <Link href="/talent-bench">
              <Users className="h-4 w-4 mr-1.5" />
              Talent Bench
            </Link>
          </Button>
          <NewHotlistDialog />
        </>
      }
    >
      <div className="grid grid-cols-3 gap-3 mb-6">
        <StatCard label="Hotlists" value={rows.length} />
        <StatCard label="Drafts" value={draftCount} />
        <StatCard label="Sent" value={sentCount} tone="success" />
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-6">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : rows.length === 0 ? (
            <div className="p-10 text-center">
              <Send className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="mt-3 text-sm text-muted-foreground">
                No hotlists yet. Create one to market your bench consultants to clients and vendors.
              </p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="p-3 text-left">Name</th>
                  <th className="p-3 text-left">Subject</th>
                  <th className="p-3 text-right">Consultants</th>
                  <th className="p-3 text-right">Recipients</th>
                  <th className="p-3 text-left">Status</th>
                  <th className="p-3 text-left">Updated</th>
                  <th className="p-3 text-right sr-only">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rows.map((h) => (
                  <tr key={h.id} className="hover:bg-muted/30">
                    <td className="p-3">
                      <Link href={`/hotlists/${h.id}`} className="font-medium hover:underline">
                        {h.name}
                      </Link>
                    </td>
                    <td className="p-3 text-xs text-muted-foreground max-w-[280px] truncate">
                      {h.subject ?? "—"}
                    </td>
                    <td className="p-3 text-right tabular-nums">{h.member_count}</td>
                    <td className="p-3 text-right tabular-nums">{h.recipient_count}</td>
                    <td className="p-3">
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium",
                          statusTone[h.status] ?? statusTone.Draft,
                        )}
                      >
                        {h.status}
                      </span>
                    </td>
                    <td className="p-3 text-xs text-muted-foreground">
                      {relativeTime(h.updated_at)}
                    </td>
                    <td className="p-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => handleDelete(h.id, h.name)}
                        disabled={remove.isPending}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
