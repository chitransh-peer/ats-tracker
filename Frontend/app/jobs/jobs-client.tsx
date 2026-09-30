"use client";

import { ImportExportButtons } from "@/components/import-export";
import { useState } from "react";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Pager } from "@/components/ui/pager";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useJobSummary, useJobsPage } from "@/lib/hooks/use-jobs";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Search } from "lucide-react";
import { cn } from "@/lib/utils";

function formatDateTime(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString(undefined, {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/** "USD 98/Hourly/C2C" — the pay column format from the job board. */
function payRate(job: {
  pay_min: number | null;
  pay_max: number | null;
  pay_rate_currency: string;
  pay_rate_unit: string;
  pay_rate_type: string | null;
}) {
  if (job.pay_min == null && job.pay_max == null) return "—";
  const amount =
    job.pay_min != null && job.pay_max != null && job.pay_min !== job.pay_max
      ? `${job.pay_min} - ${job.pay_max}`
      : `${job.pay_min ?? job.pay_max}`;
  return [`${job.pay_rate_currency} ${amount}`, job.pay_rate_unit, job.pay_rate_type]
    .filter(Boolean)
    .join("/");
}

function statusTone(status: string) {
  if (status === "Active") return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (status === "Draft") return "bg-slate-50 text-slate-700 border-slate-200";
  if (status === "On Hold") return "bg-amber-50 text-amber-700 border-amber-200";
  return "bg-rose-50 text-rose-700 border-rose-200";
}

const PAGE_SIZE = 50;

export function JobsClient() {
  const [status, setStatus] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const debouncedSearch = useDebouncedValue(search.trim());

  // Paged and searched on the server, with the headline counts from their own
  // endpoint: loading every job to filter and count here slowed the page
  // down with each requisition and would stop it loading at a few thousand.
  const { data, isLoading } = useJobsPage({
    status: status !== "all" ? status : undefined,
    search: debouncedSearch || undefined,
    limit: PAGE_SIZE,
    offset,
  });
  const { data: summary } = useJobSummary();
  const filtered = data?.data ?? [];

  function updateSearch(value: string) {
    setSearch(value);
    setOffset(0);
  }

  function updateStatus(value: string) {
    setStatus(value);
    setOffset(0);
  }

  return (
    <AppShell
      title="Job Posting"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Jobs" }]}
      actions={
        <>
          <ImportExportButtons entity="jobs" label="Jobs" />
          <Button size="sm" asChild>
            <Link href="/jobs/new">
              <Plus className="h-4 w-4 mr-1" />
              New Job
            </Link>
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Total requisitions" value={summary?.total ?? 0} />
        <StatCard label="Active" value={summary?.active ?? 0} tone="success" />
        <StatCard label="Draft" value={summary?.draft ?? 0} />
        <StatCard label="Closed / on hold" value={summary?.closed_or_on_hold ?? 0} />
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="flex flex-wrap items-center gap-2 p-4 border-b">
            <div className="relative flex-1 min-w-[220px] max-w-sm">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search jobs, job codes, clients…"
                className="pl-9 h-9"
                value={search}
                onChange={(e) => updateSearch(e.target.value)}
              />
            </div>
            <Select value={status} onValueChange={updateStatus}>
              <SelectTrigger className="h-9 w-[140px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="Draft">Draft</SelectItem>
                <SelectItem value="Active">Active</SelectItem>
                <SelectItem value="On Hold">On Hold</SelectItem>
                <SelectItem value="Closed">Closed</SelectItem>
                <SelectItem value="Cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm whitespace-nowrap">
              <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="p-3 text-left">Job Code</th>
                  <th className="p-3 text-left">Job Title</th>
                  <th className="p-3 text-left">Client</th>
                  <th className="p-3 text-left">Pay Rate / Salary</th>
                  <th className="p-3 text-left">Location</th>
                  <th className="p-3 text-left">Recruitment Manager</th>
                  <th className="p-3 text-left">Assigned To</th>
                  <th className="p-3 text-left">Job Created</th>
                  <th className="p-3 text-left">Job Modified On</th>
                  <th className="p-3 text-left">Job Status</th>
                  <th className="p-3 text-left">Job Age</th>
                </tr>
              </thead>
              <tbody>
                {isLoading && (
                  <tr>
                    <td colSpan={11} className="p-6 text-center text-muted-foreground">
                      Loading…
                    </td>
                  </tr>
                )}
                {!isLoading && filtered.length === 0 && (
                  <tr>
                    <td colSpan={11} className="p-6 text-center text-muted-foreground">
                      {debouncedSearch || status !== "all" ? (
                        "No jobs match these filters."
                      ) : (
                        <>
                          No jobs yet.{" "}
                          <Link href="/jobs/new" className="text-primary hover:underline">
                            Post your first job
                          </Link>
                          .
                        </>
                      )}
                    </td>
                  </tr>
                )}
                {filtered.map((j) => (
                  <tr key={j.id} className="border-t border-border hover:bg-muted/30">
                    <td className="p-3 font-mono text-xs text-muted-foreground">{j.req_id}</td>
                    <td className="p-3">
                      <Link
                        href={`/jobs/${j.id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {j.title}
                      </Link>
                    </td>
                    <td className="p-3 text-muted-foreground">{j.client_name ?? "—"}</td>
                    <td className="p-3 text-muted-foreground">{payRate(j)}</td>
                    <td className="p-3 text-muted-foreground">{j.location ?? "—"}</td>
                    <td className="p-3">{j.recruitment_manager_name ?? "—"}</td>
                    <td className="p-3 text-muted-foreground">
                      {j.assigned_to_names.length ? j.assigned_to_names.join(", ") : "N/A"}
                    </td>
                    <td className="p-3 text-muted-foreground">{formatDateTime(j.created_at)}</td>
                    <td className="p-3 text-muted-foreground">{formatDateTime(j.updated_at)}</td>
                    <td className="p-3">
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
                          statusTone(j.status),
                        )}
                      >
                        {j.status}
                      </span>
                    </td>
                    <td className="p-3">
                      <Badge variant="secondary" className="text-[11px]">
                        {j.job_age_days} {j.job_age_days === 1 ? "Day" : "Days"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
