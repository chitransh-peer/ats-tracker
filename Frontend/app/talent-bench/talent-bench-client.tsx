"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
  useBenchProfilesPage,
  useBenchSummary,
  useAddToBench,
  useUpdateBenchProfile,
  useRemoveFromBench,
} from "@/lib/hooks/use-bench";
import { useCandidates } from "@/lib/hooks/use-candidates";
import { useUsers } from "@/lib/hooks/use-users";
import { useAuth } from "@/lib/auth/auth-context";
import { ApiError } from "@/lib/api/client";
import type { BenchProfile } from "@/lib/api/types";
import { cn, initialsOf } from "@/lib/utils";
import { Pager } from "@/components/ui/pager";
import { Search, Plus, Send, Trash2 } from "lucide-react";

const BENCH_STATUSES = ["Active Bench", "Inactive Bench", "Placed", "Do Not Market"] as const;
const SUB_STATUSES = [
  "Available",
  "In Marketing",
  "Submitted",
  "Interviewing",
  "Offer In Hand",
  "On Project",
  "Not Reachable",
] as const;
const RATE_UNITS = ["Hourly", "Daily", "Monthly", "Annual"] as const;
const TAX_TERMS = ["C2C", "W2", "1099", "Full Time"] as const;

const statusTone: Record<string, string> = {
  "Active Bench": "bg-emerald-50 text-emerald-700 border-emerald-200",
  "Inactive Bench": "bg-slate-100 text-slate-700 border-slate-200",
  Placed: "bg-blue-50 text-blue-700 border-blue-200",
  "Do Not Market": "bg-red-50 text-red-700 border-red-200",
};

/** Long-benched consultants are the ones costing money, so age is colour-coded. */
function benchAgeTone(days: number): string {
  if (days >= 90) return "text-destructive font-semibold";
  if (days >= 60) return "text-[color:var(--color-warning-foreground)] font-medium";
  return "text-muted-foreground";
}

function formatRate(profile: BenchProfile): string {
  if (profile.desired_rate == null) return "—";
  const parts = [`${profile.rate_currency} ${profile.desired_rate}`];
  if (profile.rate_unit) parts.push(profile.rate_unit);
  if (profile.tax_term) parts.push(profile.tax_term);
  return parts.join(" / ");
}

function AddToBenchDialog() {
  const [open, setOpen] = useState(false);
  const [candidateId, setCandidateId] = useState("");
  const [marketingTitle, setMarketingTitle] = useState("");
  const [rate, setRate] = useState("");
  const [rateUnit, setRateUnit] = useState<string>("Hourly");
  const [taxTerm, setTaxTerm] = useState<string>("C2C");
  const [error, setError] = useState<string | null>(null);

  const { data: candidates } = useCandidates();
  const addToBench = useAddToBench();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await addToBench.mutateAsync({
        candidate_id: candidateId,
        marketing_title: marketingTitle || null,
        desired_rate: rate ? Number(rate) : null,
        rate_unit: rateUnit,
        tax_term: taxTerm,
      });
      setOpen(false);
      setCandidateId("");
      setMarketingTitle("");
      setRate("");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not add this candidate to the bench.",
      );
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1">
          <Plus className="h-4 w-4" />
          Add to bench
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add a consultant to the bench</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="space-y-1.5">
            <Label className="text-xs">Candidate</Label>
            <Select value={candidateId} onValueChange={setCandidateId}>
              <SelectTrigger>
                <SelectValue placeholder="Pick an existing candidate" />
              </SelectTrigger>
              <SelectContent>
                {(candidates ?? []).map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.full_name} — {c.email}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              The bench extends an existing candidate record, so résumés and skills carry over.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Marketing title</Label>
            <Input
              value={marketingTitle}
              onChange={(e) => setMarketingTitle(e.target.value)}
              placeholder="How you want to pitch them, e.g. Senior Java Developer"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Desired rate</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={rate}
                onChange={(e) => setRate(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Per</Label>
              <Select value={rateUnit} onValueChange={setRateUnit}>
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
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Tax term</Label>
              <Select value={taxTerm} onValueChange={setTaxTerm}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TAX_TERMS.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={!candidateId || addToBench.isPending}>
              {addToBench.isPending ? "Adding…" : "Add to bench"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EditBenchDialog({ profile }: { profile: BenchProfile }) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(profile.status);
  const [subStatus, setSubStatus] = useState(profile.sub_status ?? "");
  const [marketingTitle, setMarketingTitle] = useState(profile.marketing_title ?? "");
  const [rate, setRate] = useState(profile.desired_rate?.toString() ?? "");
  const [salesMember, setSalesMember] = useState(profile.sales_team_member_id ?? "");
  const [accountManager, setAccountManager] = useState(profile.account_manager_id ?? "");
  const [summary, setSummary] = useState(profile.marketing_summary ?? "");
  const [error, setError] = useState<string | null>(null);

  const { data: users } = useUsers();
  const update = useUpdateBenchProfile();
  const remove = useRemoveFromBench();

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await update.mutateAsync({
        profileId: profile.id,
        input: {
          status,
          sub_status: subStatus || null,
          marketing_title: marketingTitle || null,
          desired_rate: rate ? Number(rate) : null,
          sales_team_member_id: salesMember || null,
          account_manager_id: accountManager || null,
          marketing_summary: summary || null,
        },
      });
      setOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save these changes.");
    }
  }

  async function handleRemove() {
    if (
      !window.confirm(
        `Remove ${profile.full_name} from the bench? The candidate record and marketing history are kept.`,
      )
    ) {
      return;
    }
    setError(null);
    try {
      await remove.mutateAsync(profile.id);
      setOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not remove this consultant.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="text-xs">
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {profile.full_name}{" "}
            <span className="text-muted-foreground font-normal">#{profile.bench_code}</span>
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSave} className="space-y-3">
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Bench status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BENCH_STATUSES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Sub status</Label>
              <Select value={subStatus} onValueChange={setSubStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="—" />
                </SelectTrigger>
                <SelectContent>
                  {SUB_STATUSES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Marketing title</Label>
            <Input value={marketingTitle} onChange={(e) => setMarketingTitle(e.target.value)} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Desired rate</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={rate}
                onChange={(e) => setRate(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Sales member</Label>
              <Select value={salesMember} onValueChange={setSalesMember}>
                <SelectTrigger>
                  <SelectValue placeholder="—" />
                </SelectTrigger>
                <SelectContent>
                  {(users ?? []).map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Account manager</Label>
              <Select value={accountManager} onValueChange={setAccountManager}>
                <SelectTrigger>
                  <SelectValue placeholder="—" />
                </SelectTrigger>
                <SelectContent>
                  {(users ?? []).map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <p className="text-[11px] text-muted-foreground">
            Naming someone here also gives them visibility of this consultant.
          </p>
          <div className="space-y-1.5">
            <Label className="text-xs">Marketing summary</Label>
            <Textarea rows={3} value={summary} onChange={(e) => setSummary(e.target.value)} />
          </div>
          <DialogFooter className="justify-between sm:justify-between">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-1 text-destructive"
              onClick={handleRemove}
              disabled={remove.isPending}
            >
              <Trash2 className="h-4 w-4" />
              Remove from bench
            </Button>
            <Button type="submit" disabled={update.isPending}>
              {update.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

const PAGE_SIZE = 50;

export function TalentBenchClient() {
  const { user } = useAuth();
  const [status, setStatus] = useState<string>("Active Bench");
  const [search, setSearch] = useState("");
  const [onlyMine, setOnlyMine] = useState(false);
  const [offset, setOffset] = useState(0);

  const filters = useMemo(
    () => ({
      status: status === "all" ? undefined : status,
      search: search.trim() || undefined,
      owner_id: onlyMine ? user?.id : undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    [status, search, onlyMine, user?.id, offset],
  );

  const { data, isLoading } = useBenchProfilesPage(filters);
  const profiles = data?.data;
  const total = data?.total ?? 0;
  const { data: summary } = useBenchSummary();

  // Any filter change goes back to page 1, or "page 3 of the old filter"
  // would silently carry over to the new one.
  function updateStatus(value: string) {
    setStatus(value);
    setOffset(0);
  }
  function updateSearch(value: string) {
    setSearch(value);
    setOffset(0);
  }
  function toggleOnlyMine() {
    setOnlyMine((v) => !v);
    setOffset(0);
  }

  const canEdit = ["super_admin", "admin", "recruiter"].some((r) => user?.roles.includes(r));

  return (
    <AppShell
      title="Talent Bench"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Talent Bench" }]}
      actions={
        <>
          <Button variant="outline" size="sm" asChild>
            <Link href="/hotlists">
              <Send className="h-4 w-4 mr-1.5" />
              Hotlists
            </Link>
          </Button>
          {canEdit && <AddToBenchDialog />}
        </>
      }
    >
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <StatCard label="On bench" value={summary?.active ?? 0} />
        <StatCard label="Total profiles" value={summary?.total ?? 0} />
        <StatCard label="Placed" value={summary?.placed ?? 0} tone="success" />
        <StatCard
          label="Avg. bench age"
          value={
            summary?.average_bench_age_days != null
              ? `${Math.round(summary.average_bench_age_days)}d`
              : "—"
          }
        />
        <StatCard
          label="Ageing 60d+"
          value={summary?.aging_over_60_days ?? 0}
          tone={(summary?.aging_over_60_days ?? 0) > 0 ? "warning" : "default"}
        />
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="flex flex-wrap items-center gap-2 border-b p-4">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search name, email, or title…"
                className="pl-9 h-9"
                value={search}
                onChange={(e) => updateSearch(e.target.value)}
              />
            </div>
            <Select value={status} onValueChange={updateStatus}>
              <SelectTrigger className="h-9 w-[170px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                {BENCH_STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant={onlyMine ? "default" : "outline"} size="sm" onClick={toggleOnlyMine}>
              Mine only
            </Button>
          </div>

          {isLoading ? (
            <div className="space-y-2 p-6">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : (profiles ?? []).length === 0 ? (
            <p className="p-10 text-center text-sm text-muted-foreground">
              No consultants match these filters. Add a candidate to the bench to start marketing
              them.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="p-3 text-left">ID</th>
                    <th className="p-3 text-left">Consultant</th>
                    <th className="p-3 text-left">Marketing title</th>
                    <th className="p-3 text-left">Work auth</th>
                    <th className="p-3 text-left">Rate</th>
                    <th className="p-3 text-left">Status</th>
                    <th className="p-3 text-right">Bench age</th>
                    <th className="p-3 text-right sr-only">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(profiles ?? []).map((p) => (
                    <tr key={p.id} className="hover:bg-muted/30">
                      <td className="p-3 font-mono text-xs text-muted-foreground">
                        {p.bench_code}
                      </td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <Avatar className="h-7 w-7">
                            <AvatarFallback className="text-[10px]">
                              {initialsOf(p.full_name)}
                            </AvatarFallback>
                          </Avatar>
                          <div className="min-w-0">
                            <Link
                              href={`/candidates/${p.candidate_id}`}
                              className="font-medium hover:underline"
                            >
                              {p.full_name}
                            </Link>
                            <div className="text-xs text-muted-foreground truncate">{p.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="p-3 text-xs">{p.marketing_title ?? p.current_title ?? "—"}</td>
                      <td className="p-3 text-xs">{p.work_auth ?? "—"}</td>
                      <td className="p-3 text-xs whitespace-nowrap">{formatRate(p)}</td>
                      <td className="p-3">
                        <span
                          className={cn(
                            "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium whitespace-nowrap",
                            statusTone[p.status] ?? statusTone["Inactive Bench"],
                          )}
                        >
                          {p.status}
                        </span>
                        {p.sub_status && (
                          <div className="mt-1">
                            <Badge variant="secondary" className="text-[10px]">
                              {p.sub_status}
                            </Badge>
                          </div>
                        )}
                      </td>
                      <td className={cn("p-3 text-right text-xs", benchAgeTone(p.bench_age_days))}>
                        {p.bench_age_days}d
                      </td>
                      <td className="p-3 text-right">
                        {canEdit && <EditBenchDialog profile={p} />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
        <Pager offset={offset} limit={PAGE_SIZE} total={total} onOffsetChange={setOffset} />
      </Card>

      <p className="mt-4 text-xs text-muted-foreground">
        You see consultants you own or are named on. Admins and executives see the whole bench.
      </p>
    </AppShell>
  );
}
