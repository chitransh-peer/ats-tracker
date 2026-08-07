"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useClients } from "@/lib/hooks/use-clients";
import { Plus, Search, Building2, Download } from "lucide-react";
import { cn } from "@/lib/utils";

function statusTone(s: string) {
  return s === "Active"
    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : s === "Prospect"
      ? "bg-blue-50 text-blue-700 border-blue-200"
      : "bg-amber-50 text-amber-700 border-amber-200";
}

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

export function ClientsClient() {
  const { data: clients, isLoading } = useClients();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const list = clients ?? [];
    const query = search.trim().toLowerCase();
    if (!query) return list;
    return list.filter(
      (c) =>
        c.name.toLowerCase().includes(query) ||
        c.client_code.toLowerCase().includes(query) ||
        (c.industry ?? "").toLowerCase().includes(query),
    );
  }, [clients, search]);

  const total = clients?.length ?? 0;
  const active = clients?.filter((c) => c.status === "Active").length ?? 0;
  const openJobs = clients?.reduce((sum, c) => sum + c.active_jobs, 0) ?? 0;
  const prospects = clients?.filter((c) => c.status === "Prospect").length ?? 0;

  return (
    <AppShell
      title="Clients"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Clients" }]}
      actions={
        <>
          <Button variant="outline" size="sm" className="gap-1">
            <Download className="h-4 w-4" />
            Export
          </Button>
          <Button size="sm" className="gap-1" asChild>
            <Link href="/clients/new">
              <Plus className="h-4 w-4" />
              New client
            </Link>
          </Button>
        </>
      }
    >
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Total clients" value={total} hint="All accounts" />
        <StatCard label="Active" value={active} tone="success" />
        <StatCard label="Open requisitions" value={openJobs} hint="Across all clients" />
        <StatCard label="Prospects" value={prospects} />
      </section>

      <Card>
        <CardContent className="p-0">
          <div className="flex flex-wrap items-center gap-2 p-4 border-b">
            <div className="relative flex-1 min-w-[220px] max-w-sm">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search clients, client IDs…"
                className="pl-9 h-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm whitespace-nowrap">
              <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="p-3 text-left">Client Id</th>
                  <th className="p-3 text-left">Client Name</th>
                  <th className="p-3 text-left">Contact Number</th>
                  <th className="p-3 text-left">Website</th>
                  <th className="p-3 text-left">Industry</th>
                  <th className="p-3 text-left">Status</th>
                  <th className="p-3 text-left">Category</th>
                  <th className="p-3 text-left">Primary Owner</th>
                  <th className="p-3 text-left">Business Unit</th>
                  <th className="p-3 text-left">Display on Job Posting</th>
                  <th className="p-3 text-left">Created by</th>
                  <th className="p-3 text-left">Created On</th>
                  <th className="p-3 text-left">Modified On</th>
                  <th className="p-3 text-left">Modified By</th>
                  <th className="p-3 text-left">Primary Business Unit</th>
                </tr>
              </thead>
              <tbody>
                {isLoading && (
                  <tr>
                    <td colSpan={15} className="p-6 text-center text-muted-foreground">
                      Loading…
                    </td>
                  </tr>
                )}
                {!isLoading && filtered.length === 0 && (
                  <tr>
                    <td colSpan={15} className="p-6 text-center text-muted-foreground">
                      No clients yet.{" "}
                      <Link href="/clients/new" className="text-primary hover:underline">
                        Add your first client
                      </Link>
                      .
                    </td>
                  </tr>
                )}
                {filtered.map((c) => (
                  <tr key={c.id} className="border-t border-border hover:bg-muted/30">
                    <td className="p-3 font-mono text-xs text-muted-foreground">{c.client_code}</td>
                    <td className="p-3">
                      <Link href={`/clients/${c.id}`} className="flex items-center gap-2.5 group">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback className="bg-primary/10 text-primary text-xs">
                            <Building2 className="h-4 w-4" />
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="font-medium group-hover:text-primary group-hover:underline">
                            {c.name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {c.active_jobs} open jobs
                          </div>
                        </div>
                      </Link>
                    </td>
                    <td className="p-3 text-muted-foreground">{c.contact_number ?? "—"}</td>
                    <td className="p-3">
                      {c.website ? (
                        <a
                          href={c.website}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary hover:underline"
                        >
                          {c.website.replace(/^https?:\/\//, "")}
                        </a>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="p-3 text-muted-foreground">{c.industry ?? "—"}</td>
                    <td className="p-3">
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
                          statusTone(c.status),
                        )}
                      >
                        {c.status}
                      </span>
                    </td>
                    <td className="p-3 text-muted-foreground">{c.category ?? "—"}</td>
                    <td className="p-3">{c.primary_owner_name ?? "—"}</td>
                    <td className="p-3 text-muted-foreground">{c.business_unit ?? "—"}</td>
                    <td className="p-3">
                      <Badge
                        variant={c.display_on_job_posting ? "secondary" : "outline"}
                        className="text-[11px]"
                      >
                        {c.display_on_job_posting ? "Yes" : "No"}
                      </Badge>
                    </td>
                    <td className="p-3 text-muted-foreground">{c.created_by_name ?? "—"}</td>
                    <td className="p-3 text-muted-foreground">{formatDate(c.created_at)}</td>
                    <td className="p-3 text-muted-foreground">{formatDate(c.updated_at)}</td>
                    <td className="p-3 text-muted-foreground">{c.updated_by_name ?? "—"}</td>
                    <td className="p-3 text-muted-foreground">{c.primary_business_unit ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </AppShell>
  );
}
