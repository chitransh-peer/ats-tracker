"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { useOffers, useCreateOffer, useOfferAction } from "@/lib/hooks/use-offers";
import { useApplications } from "@/lib/hooks/use-applications";
import { useCandidates } from "@/lib/hooks/use-candidates";
import { useJobs } from "@/lib/hooks/use-jobs";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { ApiError } from "@/lib/api/client";

const tone: Record<string, string> = {
  Draft: "bg-slate-100 text-slate-700",
  "Approval Pending": "bg-amber-100 text-amber-800",
  Sent: "bg-blue-100 text-blue-800",
  Accepted: "bg-emerald-100 text-emerald-800",
  Declined: "bg-red-100 text-red-800",
  Expired: "bg-slate-200 text-slate-600",
};

function NewOfferDialog() {
  const [open, setOpen] = useState(false);
  const [applicationId, setApplicationId] = useState("");
  const [baseSalary, setBaseSalary] = useState("");
  const [bonus, setBonus] = useState("");
  const [equity, setEquity] = useState("");
  const [joiningDate, setJoiningDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { data: applications } = useApplications({ status: "Active" });
  const { data: candidates } = useCandidates();
  const { data: jobs } = useJobs();
  const createOffer = useCreateOffer();

  const candidateById = new Map((candidates ?? []).map((c) => [c.id, c]));
  const jobById = new Map((jobs ?? []).map((j) => [j.id, j]));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createOffer.mutateAsync({
        application_id: applicationId,
        base_salary: Number(baseSalary),
        bonus: bonus ? Number(bonus) : null,
        equity: equity || null,
        joining_date: joiningDate || null,
      });
      setOpen(false);
      setApplicationId("");
      setBaseSalary("");
      setBonus("");
      setEquity("");
      setJoiningDate("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create offer.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">New offer</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New offer</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="space-y-1.5">
            <Label className="text-xs">Application</Label>
            <Select value={applicationId} onValueChange={setApplicationId} required>
              <SelectTrigger>
                <SelectValue placeholder="Select candidate · job" />
              </SelectTrigger>
              <SelectContent>
                {(applications ?? []).map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {candidateById.get(a.candidate_id)?.full_name ?? "Unknown"} ·{" "}
                    {jobById.get(a.job_id)?.title ?? "Unknown"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Base salary (USD)</Label>
              <Input
                type="number"
                value={baseSalary}
                onChange={(e) => setBaseSalary(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Bonus (USD)</Label>
              <Input type="number" value={bonus} onChange={(e) => setBonus(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Equity</Label>
              <Input
                value={equity}
                onChange={(e) => setEquity(e.target.value)}
                placeholder="e.g. 1000 RSUs / 4yr"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Joining date</Label>
              <Input
                type="date"
                value={joiningDate}
                onChange={(e) => setJoiningDate(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createOffer.isPending || !applicationId}>
              {createOffer.isPending ? "Creating…" : "Create offer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function OffersClient() {
  const { data: offers, isLoading } = useOffers();
  const { data: applications } = useApplications();
  const { data: candidates } = useCandidates();
  const { data: jobs } = useJobs();
  const actions = useOfferAction();

  const applicationById = new Map((applications ?? []).map((a) => [a.id, a]));
  const candidateById = new Map((candidates ?? []).map((c) => [c.id, c]));
  const jobById = new Map((jobs ?? []).map((j) => [j.id, j]));

  return (
    <AppShell
      title="Offers"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Offers" }]}
      actions={<NewOfferDialog />}
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard
          label="In progress"
          value={
            offers?.filter((o) => !["Accepted", "Declined", "Expired"].includes(o.status)).length ??
            0
          }
        />
        <StatCard
          label="Awaiting approval"
          value={offers?.filter((o) => o.status === "Approval Pending").length ?? 0}
          tone="warning"
        />
        <StatCard label="Sent" value={offers?.filter((o) => o.status === "Sent").length ?? 0} />
        <StatCard
          label="Accepted"
          value={offers?.filter((o) => o.status === "Accepted").length ?? 0}
          tone="success"
        />
      </div>

      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="p-3 text-left">Candidate</th>
                <th className="p-3 text-left">Job</th>
                <th className="p-3 text-right">Base</th>
                <th className="p-3 text-left">Equity</th>
                <th className="p-3 text-left">Joining</th>
                <th className="p-3 text-left">Status</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {isLoading && (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-sm text-muted-foreground">
                    Loading…
                  </td>
                </tr>
              )}
              {!isLoading && (offers?.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-sm text-muted-foreground">
                    No offers yet.
                  </td>
                </tr>
              )}
              {offers?.map((o) => {
                const application = applicationById.get(o.application_id);
                const candidate = application
                  ? candidateById.get(application.candidate_id)
                  : undefined;
                const job = application ? jobById.get(application.job_id) : undefined;
                return (
                  <tr key={o.id} className="hover:bg-muted/30">
                    <td className="p-3">
                      {candidate ? (
                        <Link
                          href={`/candidates/${candidate.id}`}
                          className="font-medium hover:underline"
                        >
                          {candidate.full_name}
                        </Link>
                      ) : (
                        "Unknown"
                      )}
                    </td>
                    <td className="p-3 text-xs">{job?.title ?? "—"}</td>
                    <td className="p-3 text-right font-medium">
                      ${o.base_salary.toLocaleString()}
                    </td>
                    <td className="p-3 text-xs">{o.equity ?? "—"}</td>
                    <td className="p-3 text-xs">{o.joining_date ?? "—"}</td>
                    <td className="p-3">
                      <Badge className={`text-[10px] ${tone[o.status] ?? ""}`}>{o.status}</Badge>
                    </td>
                    <td className="p-3 text-right space-x-1">
                      {o.status === "Draft" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 text-xs"
                          onClick={() => actions.submitForApproval.mutate(o.id)}
                        >
                          Submit
                        </Button>
                      )}
                      {o.status === "Approval Pending" &&
                        o.approvals[o.approvals.length - 1]?.status === "Pending" && (
                          <>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 text-xs"
                              onClick={() => actions.approve.mutate(o.id)}
                            >
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 text-xs"
                              onClick={() => actions.reject.mutate(o.id)}
                            >
                              Reject
                            </Button>
                          </>
                        )}
                      {o.status === "Approval Pending" &&
                        o.approvals[o.approvals.length - 1]?.status === "Approved" && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 text-xs"
                            onClick={() => actions.send.mutate(o.id)}
                          >
                            Send
                          </Button>
                        )}
                      {o.status === "Sent" && (
                        <>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 text-xs"
                            onClick={() => actions.accept.mutate(o.id)}
                          >
                            Mark accepted
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 text-xs"
                            onClick={() => actions.decline.mutate(o.id)}
                          >
                            Mark declined
                          </Button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </AppShell>
  );
}
