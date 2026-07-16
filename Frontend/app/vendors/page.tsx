import type { Metadata } from "next";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { vendorsList } from "@/lib/mock-data";
import { Plus, Search, Truck, MoreHorizontal, Download } from "lucide-react";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Vendors",
  description:
    "Track staffing vendors, submission volume, and partnership status for your recruiting supply chain.",
  alternates: { canonical: "/vendors" },
  openGraph: {
    title: "Vendors — ATS Tracker",
    description: "Vendor management for recruiting operations.",
  },
};

export default function VendorsPage() {
  const total = vendorsList.length;
  const active = vendorsList.filter((v) => v.status === "Active").length;
  const subs = vendorsList.reduce((s, v) => s + v.activeSubmissions, 0);
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
          <Button size="sm" className="gap-1">
            <Plus className="h-4 w-4" />
            New vendor
          </Button>
        </>
      }
    >
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Vendors" value={total} hint="Partnered agencies" />
        <StatCard label="Active" value={active} tone="success" />
        <StatCard label="Live submissions" value={subs} hint="Awaiting review" />
        <StatCard label="Submit-to-hire" value="9.4%" tone="warning" hint="Rolling 60 days" />
      </section>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 flex-wrap">
          <CardTitle className="text-base">All vendors</CardTitle>
          <div className="relative w-full max-w-xs">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input placeholder="Search vendors…" className="pl-9 h-9" />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="p-3 text-left">Vendor</th>
                <th className="p-3 text-left">Specialization</th>
                <th className="p-3 text-left">Submissions</th>
                <th className="p-3 text-left">Status</th>
                <th className="p-3 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {vendorsList.map((v) => (
                <tr key={v.id} className="border-t border-border hover:bg-muted/30">
                  <td className="p-3">
                    <div className="flex items-center gap-2.5">
                      <div className="h-8 w-8 rounded-md bg-primary/10 text-primary grid place-items-center">
                        <Truck className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="font-medium">{v.name}</div>
                        <div className="text-xs text-muted-foreground">{v.id.toUpperCase()}</div>
                      </div>
                    </div>
                  </td>
                  <td className="p-3 text-muted-foreground">{v.specialization}</td>
                  <td className="p-3">
                    <Badge variant="secondary" className="text-[11px]">
                      {v.activeSubmissions} active
                    </Badge>
                  </td>
                  <td className="p-3">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
                        v.status === "Active"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : "bg-amber-50 text-amber-700 border-amber-200",
                      )}
                    >
                      {v.status}
                    </span>
                  </td>
                  <td className="p-3 text-right">
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </AppShell>
  );
}
