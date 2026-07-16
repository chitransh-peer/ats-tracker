import type { Metadata } from "next";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Shield,
  Search,
  Plus,
  KeyRound,
  Activity,
  Users,
  Lock,
  CheckCircle2,
  AlertTriangle,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Admin Console",
  description:
    "Manage users, roles, permissions, audit logs, security policies, and system health across the ATS.",
  robots: { index: false, follow: false },
  alternates: { canonical: "/admin" },
  openGraph: {
    title: "Admin Console — ATS Tracker",
    description: "Administer users, roles, security, and audit logs.",
  },
};

const users = [
  {
    id: "u1",
    name: "Priya Sharma",
    email: "priya@acme.com",
    role: "Super Admin",
    status: "Active",
    last: "2m ago",
  },
  {
    id: "u2",
    name: "David Park",
    email: "david@acme.com",
    role: "Admin",
    status: "Active",
    last: "18m ago",
  },
  {
    id: "u3",
    name: "Sarah Kim",
    email: "sarah@acme.com",
    role: "Recruiter",
    status: "Active",
    last: "1h ago",
  },
  {
    id: "u4",
    name: "Elena Rodriguez",
    email: "elena@acme.com",
    role: "Hiring Manager",
    status: "Active",
    last: "3h ago",
  },
  {
    id: "u5",
    name: "Marcus Johnson",
    email: "marcus@acme.com",
    role: "Interviewer",
    status: "Invited",
    last: "—",
  },
  {
    id: "u6",
    name: "Ravi Menon",
    email: "ravi@acme.com",
    role: "Executive",
    status: "Active",
    last: "yesterday",
  },
  {
    id: "u7",
    name: "Anna Weiss",
    email: "anna@acme.com",
    role: "Recruiter",
    status: "Suspended",
    last: "5 days ago",
  },
];

const roles = [
  {
    name: "Super Admin",
    members: 2,
    description: "Full access to all workspaces, billing, and system configuration.",
    scopes: ["All modules", "Billing", "Audit", "Security"],
  },
  {
    name: "Admin",
    members: 5,
    description: "Manage users, workflows, integrations, and templates within workspace.",
    scopes: ["Users", "Workflows", "Templates", "Reports"],
  },
  {
    name: "Executive",
    members: 4,
    description: "Read-only leadership access to reports and dashboards.",
    scopes: ["Reports", "Dashboards"],
  },
  {
    name: "Recruiter",
    members: 22,
    description: "Own requisitions and pipelines end-to-end.",
    scopes: ["Jobs", "Candidates", "Interviews", "Offers"],
  },
  {
    name: "Hiring Manager",
    members: 18,
    description: "Review shortlists, feedback, and approve offers.",
    scopes: ["Assigned jobs", "Feedback", "Offers"],
  },
  {
    name: "Interviewer",
    members: 46,
    description: "Submit interview feedback for assigned candidates.",
    scopes: ["Interviews", "Feedback"],
  },
];

const audit = [
  {
    id: "l1",
    who: "Priya Sharma",
    action: "Updated role permissions",
    target: "Recruiter",
    at: "2m ago",
    severity: "info",
  },
  {
    id: "l2",
    who: "System",
    action: "Failed sign-in attempt",
    target: "anna@acme.com",
    at: "12m ago",
    severity: "warn",
  },
  {
    id: "l3",
    who: "David Park",
    action: "Invited user",
    target: "marcus@acme.com",
    at: "1h ago",
    severity: "info",
  },
  {
    id: "l4",
    who: "Sarah Kim",
    action: "Exported candidate list",
    target: "Java Developer pipeline",
    at: "3h ago",
    severity: "info",
  },
  {
    id: "l5",
    who: "System",
    action: "Suspended user after policy trigger",
    target: "anna@acme.com",
    at: "5 days ago",
    severity: "warn",
  },
  {
    id: "l6",
    who: "Priya Sharma",
    action: "Rotated API key",
    target: "Zapier integration",
    at: "1 week ago",
    severity: "info",
  },
];

function statusTone(s: string) {
  return s === "Active"
    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : s === "Invited"
      ? "bg-blue-50 text-blue-700 border-blue-200"
      : "bg-red-50 text-red-700 border-red-200";
}

export default function AdminPage() {
  return (
    <AppShell
      title="Admin Console"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Admin" }]}
      actions={
        <>
          <Button variant="outline" size="sm" className="gap-1">
            <Download className="h-4 w-4" />
            Export audit
          </Button>
          <Button size="sm" className="gap-1">
            <Plus className="h-4 w-4" />
            Invite user
          </Button>
        </>
      }
    >
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Total users" value={97} hint="Across all roles" />
        <StatCard label="Active today" value={41} tone="success" change="+6" />
        <StatCard label="Pending invites" value={3} tone="warning" />
        <StatCard label="Failed sign-ins (24h)" value={2} tone="destructive" />
      </section>

      <Tabs defaultValue="users" className="space-y-4">
        <TabsList>
          <TabsTrigger value="users" className="gap-1.5">
            <Users className="h-4 w-4" />
            Users
          </TabsTrigger>
          <TabsTrigger value="roles" className="gap-1.5">
            <Shield className="h-4 w-4" />
            Roles & permissions
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-1.5">
            <Lock className="h-4 w-4" />
            Security
          </TabsTrigger>
          <TabsTrigger value="audit" className="gap-1.5">
            <Activity className="h-4 w-4" />
            Audit log
          </TabsTrigger>
          <TabsTrigger value="api" className="gap-1.5">
            <KeyRound className="h-4 w-4" />
            API & webhooks
          </TabsTrigger>
        </TabsList>

        <TabsContent value="users">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-3 flex-wrap">
              <CardTitle className="text-base">Team members</CardTitle>
              <div className="relative w-full max-w-xs">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input placeholder="Search users…" className="pl-9 h-9" />
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="p-3 text-left">User</th>
                    <th className="p-3 text-left">Role</th>
                    <th className="p-3 text-left">Status</th>
                    <th className="p-3 text-left">Last active</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-t border-border hover:bg-muted/30">
                      <td className="p-3">
                        <div className="flex items-center gap-2.5">
                          <Avatar className="h-8 w-8">
                            <AvatarFallback className="text-[10px]">
                              {u.name
                                .split(" ")
                                .map((n) => n[0])
                                .join("")}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <div className="font-medium">{u.name}</div>
                            <div className="text-xs text-muted-foreground">{u.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="p-3">
                        <Badge variant="secondary" className="text-[11px]">
                          {u.role}
                        </Badge>
                      </td>
                      <td className="p-3">
                        <span
                          className={cn(
                            "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
                            statusTone(u.status),
                          )}
                        >
                          {u.status}
                        </span>
                      </td>
                      <td className="p-3 text-muted-foreground">{u.last}</td>
                      <td className="p-3 text-right">
                        <Button variant="ghost" size="sm">
                          Edit
                        </Button>
                        <Button variant="ghost" size="sm" className="text-destructive">
                          Suspend
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roles">
          <div className="grid md:grid-cols-2 gap-4">
            {roles.map((r) => (
              <Card key={r.name}>
                <CardHeader className="flex flex-row items-start justify-between gap-3">
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Shield className="h-4 w-4 text-primary" />
                      {r.name}
                    </CardTitle>
                    <p className="mt-1 text-sm text-muted-foreground">{r.description}</p>
                  </div>
                  <Badge variant="secondary" className="text-[11px] shrink-0">
                    {r.members} members
                  </Badge>
                </CardHeader>
                <CardContent>
                  <div className="text-xs uppercase text-muted-foreground mb-1.5">Scopes</div>
                  <div className="flex flex-wrap gap-1.5">
                    {r.scopes.map((s) => (
                      <span
                        key={s}
                        className="inline-flex items-center rounded-md border border-border bg-muted/40 px-2 py-0.5 text-[11px]"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                  <div className="mt-4 flex gap-2">
                    <Button variant="outline" size="sm">
                      Edit permissions
                    </Button>
                    <Button variant="ghost" size="sm">
                      View members
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="security">
          <div className="grid md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Authentication</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { label: "Require SSO for all users", on: true },
                  { label: "Enforce 2FA on admin roles", on: true },
                  { label: "Allow password sign-in fallback", on: false },
                  { label: "Session timeout after 30 min idle", on: true },
                ].map((s) => (
                  <div key={s.label} className="flex items-center justify-between">
                    <Label className="text-sm font-normal">{s.label}</Label>
                    <Switch defaultChecked={s.on} />
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Data & compliance</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { label: "GDPR candidate data retention (2 years)", on: true },
                  { label: "Auto-anonymize rejected candidates after 6 months", on: true },
                  { label: "EEOC/OFCCP self-identification prompts", on: true },
                  { label: "Restrict candidate exports to admins", on: false },
                ].map((s) => (
                  <div key={s.label} className="flex items-center justify-between">
                    <Label className="text-sm font-normal">{s.label}</Label>
                    <Switch defaultChecked={s.on} />
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="audit">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Recent activity</CardTitle>
              <Button variant="outline" size="sm" className="gap-1">
                <Download className="h-4 w-4" />
                Download CSV
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <ul className="divide-y divide-border">
                {audit.map((a) => (
                  <li key={a.id} className="p-3 flex items-start gap-3">
                    <div
                      className={cn(
                        "h-8 w-8 rounded-md grid place-items-center shrink-0",
                        a.severity === "warn"
                          ? "bg-amber-50 text-amber-700"
                          : "bg-muted text-muted-foreground",
                      )}
                    >
                      {a.severity === "warn" ? (
                        <AlertTriangle className="h-4 w-4" />
                      ) : (
                        <CheckCircle2 className="h-4 w-4" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm">
                        <span className="font-medium">{a.who}</span> {a.action} —{" "}
                        <span className="text-muted-foreground">{a.target}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">{a.at}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="api">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">API keys</CardTitle>
              <Button size="sm" className="gap-1">
                <Plus className="h-4 w-4" />
                Create key
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="p-3 text-left">Name</th>
                    <th className="p-3 text-left">Key</th>
                    <th className="p-3 text-left">Created</th>
                    <th className="p-3 text-left">Last used</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    {
                      n: "Zapier integration",
                      k: "ats_live_••••••••7f24",
                      c: "Mar 12, 2024",
                      u: "5m ago",
                    },
                    {
                      n: "Careers site widget",
                      k: "ats_live_••••••••91ab",
                      c: "Jan 04, 2024",
                      u: "2h ago",
                    },
                    {
                      n: "Data warehouse sync",
                      k: "ats_live_••••••••c3e0",
                      c: "Nov 22, 2023",
                      u: "1d ago",
                    },
                  ].map((k) => (
                    <tr key={k.n} className="border-t border-border">
                      <td className="p-3 font-medium">{k.n}</td>
                      <td className="p-3 font-mono text-xs text-muted-foreground">{k.k}</td>
                      <td className="p-3 text-muted-foreground">{k.c}</td>
                      <td className="p-3 text-muted-foreground">{k.u}</td>
                      <td className="p-3 text-right">
                        <Button variant="ghost" size="sm">
                          Rotate
                        </Button>
                        <Button variant="ghost" size="sm" className="text-destructive">
                          Revoke
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
