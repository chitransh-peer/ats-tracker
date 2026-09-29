"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Pager } from "@/components/ui/pager";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useVendorSummary, useVendorsPage } from "@/lib/hooks/use-vendors";
import { Plus, Search, Truck, Download } from "lucide-react";

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

const PAGE_SIZE = 50;

export function VendorsClient() {
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const debouncedSearch = useDebouncedValue(search.trim());

  // Paged and searched on the server: at the ~50,000 vendors a Ceipal import
  // brings in, loading them all to filter in the browser froze the page.
  const { data, isLoading } = useVendorsPage({
    search: debouncedSearch || undefined,
    limit: PAGE_SIZE,
    offset,
  });
  const { data: summary } = useVendorSummary();
  const filtered = data?.data ?? [];
  const matching = data?.total ?? 0;

  function updateSearch(value: string) {
    setSearch(value);
    // Page 3 of the old search would silently apply to the new one.
    setOffset(0);
  }

  return (
    <AppShell
      title="Vendors"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Vendors" }]}
      actions={
        <>
          <Button variant="outline" size="sm" className="gap-1">
            <Download className="h-4 w-4" />
            Export
          </Button>
          <Button size="sm" className="gap-1" asChild>
            <Link href="/vendors/new">
              <Plus className="h-4 w-4" />
              New vendor
            </Link>
          </Button>
        </>
      }
    >
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Vendors" value={summary?.total ?? 0} hint="Partnered agencies" />
        <StatCard label="Active" value={summary?.active ?? 0} tone="success" />
        <StatCard
          label="Live submissions"
          value={summary?.active_submissions ?? 0}
          hint="Awaiting review"
        />
        <StatCard label="Primary vendors" value={summary?.primary ?? 0} />
      </section>

      <Card>
        <CardContent className="p-0">
          <div className="flex flex-wrap items-center gap-2 p-4 border-b">
            <div className="relative flex-1 min-w-[220px] max-w-sm">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search vendors, state, country…"
                className="pl-9 h-9"
                value={search}
                onChange={(e) => updateSearch(e.target.value)}
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm whitespace-nowrap">
              <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="p-3 text-left">Vendor Name</th>
                  <th className="p-3 text-left">Website</th>
                  <th className="p-3 text-left">Contact Number</th>
                  <th className="p-3 text-left">State</th>
                  <th className="p-3 text-left">Created By</th>
                  <th className="p-3 text-left">Created On</th>
                  <th className="p-3 text-left">Country</th>
                  <th className="p-3 text-left">Ownership</th>
                  <th className="p-3 text-left">Business Unit</th>
                  <th className="p-3 text-left">Modified On</th>
                  <th className="p-3 text-left">Modified By</th>
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
                      {debouncedSearch ? (
                        "No vendors match that search."
                      ) : (
                        <>
                          No vendors yet.{" "}
                          <Link href="/vendors/new" className="text-primary hover:underline">
                            Add your first vendor
                          </Link>
                          .
                        </>
                      )}
                    </td>
                  </tr>
                )}
                {filtered.map((v) => (
                  <tr key={v.id} className="border-t border-border hover:bg-muted/30">
                    <td className="p-3">
                      <Link href={`/vendors/${v.id}`} className="flex items-center gap-2.5 group">
                        <div className="h-8 w-8 rounded-md bg-primary/10 text-primary grid place-items-center shrink-0">
                          <Truck className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="font-medium group-hover:text-primary group-hover:underline">
                            {v.name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {v.active_submissions} active submissions
                          </div>
                        </div>
                      </Link>
                    </td>
                    <td className="p-3">
                      {v.website ? (
                        <a
                          href={v.website}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary hover:underline"
                        >
                          {v.website.replace(/^https?:\/\//, "")}
                        </a>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="p-3 text-muted-foreground">{v.contact_number ?? "—"}</td>
                    <td className="p-3 text-muted-foreground">{v.state ?? "—"}</td>
                    <td className="p-3 text-muted-foreground">{v.created_by_name ?? "—"}</td>
                    <td className="p-3 text-muted-foreground">{formatDate(v.created_at)}</td>
                    <td className="p-3 text-muted-foreground">{v.country ?? "—"}</td>
                    <td className="p-3">{v.ownership_name ?? "—"}</td>
                    <td className="p-3 text-muted-foreground">
                      {v.business_units.length ? v.business_units.join(", ") : "—"}
                    </td>
                    <td className="p-3 text-muted-foreground">{formatDate(v.updated_at)}</td>
                    <td className="p-3 text-muted-foreground">{v.updated_by_name ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
        <Pager offset={offset} limit={PAGE_SIZE} total={matching} onOffsetChange={setOffset} />
      </Card>
    </AppShell>
  );
}
