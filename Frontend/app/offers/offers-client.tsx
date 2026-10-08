"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import {
  useCreateOffer,
  useOfferAction,
  useOfferSummary,
  useOffersPage,
} from "@/lib/hooks/use-offers";
import { EntityPicker } from "@/components/entity-picker";
import { Pager } from "@/components/ui/pager";
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
import {
  OFFER_CURRENCIES,
  OFFER_EMPLOYMENT_TYPES,
  OFFER_PAY_TYPES,
  OFFER_TAX_TERMS,
  formatOfferPay,
} from "@/lib/api/offers";

const tone: Record<string, string> = {
  Draft: "bg-slate-100 text-slate-700",
  "Approval Pending": "bg-amber-100 text-amber-800",
  Sent: "bg-blue-100 text-blue-800",
  Accepted: "bg-emerald-100 text-emerald-800",
  Declined: "bg-red-100 text-red-800",
  Expired: "bg-slate-200 text-slate-600",
};

const NONE = "__none__";

/** A select whose empty value reads as "Not set". */
function OptionalSelect({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (value: string) => void;
  options: readonly string[];
}) {
  return (
    <Select value={value || NONE} onValueChange={(v) => onChange(v === NONE ? "" : v)}>
      <SelectTrigger>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={NONE}>Not set</SelectItem>
        {options.map((o) => (
          <SelectItem key={o} value={o}>
            {o}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

const EMPTY_FORM = {
  applicationId: "",
  payType: "Salary",
  currency: "USD",
  baseSalary: "",
  hourlyRate: "",
  employmentType: "Full-time",
  taxTerm: "W-2",
  contractDuration: "",
  bonus: "",
  equity: "",
  joiningDate: "",
};

function NewOfferDialog() {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const createOffer = useCreateOffer();

  const set = (key: keyof typeof EMPTY_FORM, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  // Picking the engagement fills in what usually goes with it; each field can
  // still be changed afterwards.
  function changeTaxTerm(taxTerm: string) {
    setForm((prev) => {
      const next = { ...prev, taxTerm };
      if (taxTerm === "C2C" || taxTerm === "1099") {
        next.payType = "Hourly";
        if (prev.employmentType === "Full-time") next.employmentType = "Contract";
      }
      if (taxTerm === "India Payroll" || taxTerm === "India Contract") next.currency = "INR";
      if (taxTerm === "India Contract" && prev.employmentType === "Full-time") {
        next.employmentType = "Contract";
      }
      return next;
    });
  }

  const hourly = form.payType === "Hourly";
  const isContract = form.employmentType.startsWith("Contract");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createOffer.mutateAsync({
        application_id: form.applicationId,
        pay_type: form.payType,
        currency: form.currency,
        base_salary: hourly ? null : Number(form.baseSalary),
        hourly_rate: hourly ? Number(form.hourlyRate) : null,
        employment_type: form.employmentType || null,
        tax_term: form.taxTerm || null,
        contract_duration: isContract ? form.contractDuration.trim() || null : null,
        bonus: !hourly && form.bonus ? Number(form.bonus) : null,
        equity: (!hourly && form.equity) || null,
        joining_date: form.joiningDate || null,
      });
      setOpen(false);
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create offer.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">New offer</Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>New offer</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="space-y-1.5">
            <Label className="text-xs">Application</Label>
            <EntityPicker
              kind="applications"
              status="Active"
              value={form.applicationId || null}
              onChange={(id) => set("applicationId", id ?? "")}
              placeholder="Search candidate or job"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Employment terms</Label>
              <OptionalSelect
                value={form.taxTerm}
                onChange={changeTaxTerm}
                options={OFFER_TAX_TERMS}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Employment type</Label>
              <OptionalSelect
                value={form.employmentType}
                onChange={(v) => set("employmentType", v)}
                options={OFFER_EMPLOYMENT_TYPES}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Pay type</Label>
              <Select value={form.payType} onValueChange={(v) => set("payType", v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OFFER_PAY_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t === "Salary" ? "Annual salary" : "Hourly rate"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Currency</Label>
              <Select value={form.currency} onValueChange={(v) => set("currency", v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OFFER_CURRENCIES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          {hourly ? (
            <div className="space-y-1.5">
              <Label className="text-xs">Hourly rate ({form.currency})</Label>
              <Input
                type="number"
                min="0.01"
                step="0.01"
                value={form.hourlyRate}
                onChange={(e) => set("hourlyRate", e.target.value)}
                required
              />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">
                    {form.currency === "INR" ? "Annual CTC" : "Base salary"} ({form.currency})
                  </Label>
                  <Input
                    type="number"
                    min="1"
                    value={form.baseSalary}
                    onChange={(e) => set("baseSalary", e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Bonus ({form.currency})</Label>
                  <Input
                    type="number"
                    min="0"
                    value={form.bonus}
                    onChange={(e) => set("bonus", e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Equity</Label>
                <Input
                  value={form.equity}
                  onChange={(e) => set("equity", e.target.value)}
                  placeholder="e.g. 1000 RSUs / 4yr"
                />
              </div>
            </>
          )}
          <div className="grid grid-cols-2 gap-3">
            {isContract && (
              <div className="space-y-1.5">
                <Label className="text-xs">Contract duration</Label>
                <Input
                  value={form.contractDuration}
                  onChange={(e) => set("contractDuration", e.target.value)}
                  placeholder="e.g. 6 months"
                  maxLength={100}
                />
              </div>
            )}
            <div className="space-y-1.5">
              <Label className="text-xs">Joining date</Label>
              <Input
                type="date"
                value={form.joiningDate}
                onChange={(e) => set("joiningDate", e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createOffer.isPending || !form.applicationId}>
              {createOffer.isPending ? "Creating…" : "Create offer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

const PAGE_SIZE = 50;

export function OffersClient() {
  const [offset, setOffset] = useState(0);
  // Paged, named and counted by the server; see the interviews page.
  const { data, isLoading } = useOffersPage({ limit: PAGE_SIZE, offset });
  const { data: summary } = useOfferSummary();
  const offers = data?.data;
  const actions = useOfferAction();

  return (
    <AppShell
      title="Offers"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Offers" }]}
      actions={<NewOfferDialog />}
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="In progress" value={summary?.in_progress ?? 0} />
        <StatCard
          label="Awaiting approval"
          value={summary?.awaiting_approval ?? 0}
          tone="warning"
        />
        <StatCard label="Sent" value={summary?.sent ?? 0} />
        <StatCard label="Accepted" value={summary?.accepted ?? 0} tone="success" />
      </div>

      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="p-3 text-left">Candidate</th>
                <th className="p-3 text-left">Job</th>
                <th className="p-3 text-right">Pay</th>
                <th className="p-3 text-left">Terms</th>
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
                return (
                  <tr key={o.id} className="hover:bg-muted/30">
                    <td className="p-3">
                      {o.candidate_id && o.candidate_name ? (
                        <Link
                          href={`/candidates/${o.candidate_id}`}
                          className="font-medium hover:underline"
                        >
                          {o.candidate_name}
                        </Link>
                      ) : (
                        "Unknown"
                      )}
                    </td>
                    <td className="p-3 text-xs">{o.job_title ?? "—"}</td>
                    <td className="p-3 text-right font-medium whitespace-nowrap">
                      {formatOfferPay(o)}
                    </td>
                    <td className="p-3 text-xs">
                      {[o.tax_term, o.employment_type, o.contract_duration]
                        .filter(Boolean)
                        .join(" · ") || "—"}
                    </td>
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
        <Pager
          offset={offset}
          limit={PAGE_SIZE}
          total={data?.total ?? 0}
          onOffsetChange={setOffset}
        />
      </Card>
    </AppShell>
  );
}
