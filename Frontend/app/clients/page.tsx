import type { Metadata } from "next";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { clientsList } from "@/lib/mock-data";
import { Plus, Search, Building2, Download, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Clients",
  description:
    "Manage client accounts, active requisitions, and account owners across your recruiting portfolio.",
  alternates: { canonical: "/clients" },
  openGraph: {
    title: "Clients — ATS Tracker",
    description: "Client account management for recruiting operations.",
  },
};

function statusTone(s: string) {
  return s === "Active"
    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : s === "Prospect"
      ? "bg-blue-50 text-blue-700 border-blue-200"
      : "bg-amber-50 text-amber-700 border-amber-200";
}

export default function ClientsPage() {
  const total = clientsList.length;
  const active = clientsList.filter((c) => c.status === "Active").length;
  const jobs = clientsList.reduce((s, c) => s + c.activeJobs, 0);

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
          <Button size="sm" className="gap-1">
            <Plus className="h-4 w-4" />
            New client
          </Button>
        </>
      }
    >
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Total clients" value={total} hint="All accounts" />
        <StatCard label="Active" value={active} change="+2 this quarter" tone="success" />
        <StatCard label="Open requisitions" value={jobs} hint="Across all clients" />
        <StatCard label="Avg. time-to-fill" value="24d" tone="warning" hint="Rolling 90 days" />
      </section>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 flex-wrap">
          <CardTitle className="text-base">All clients</CardTitle>
          <div className="relative w-full max-w-xs">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input placeholder="Search clients…" className="pl-9 h-9" />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="p-3 text-left">Client</th>
                <th className="p-3 text-left">Industry</th>
                <th className="p-3 text-left">Account owner</th>
                <th className="p-3 text-left">Active jobs</th>
                <th className="p-3 text-left">Status</th>
                <th className="p-3 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {clientsList.map((c) => (
                <tr key={c.id} className="border-t border-border hover:bg-muted/30">
                  <td className="p-3">
                    <div className="flex items-center gap-2.5">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="bg-primary/10 text-primary text-xs">
                          <Building2 className="h-4 w-4" />
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="font-medium">{c.name}</div>
                        <div className="text-xs text-muted-foreground">{c.id.toUpperCase()}</div>
                      </div>
                    </div>
                  </td>
                  <td className="p-3 text-muted-foreground">{c.industry}</td>
                  <td className="p-3">{c.contact}</td>
                  <td className="p-3">
                    <Badge variant="secondary" className="text-[11px]">
                      {c.activeJobs} open
                    </Badge>
                  </td>
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
