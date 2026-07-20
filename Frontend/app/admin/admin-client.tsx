"use client";

import { useState } from "react";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Shield, Search, Activity, Users, Lock, KeyRound, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUsers, useInviteUser, useUpdateUser } from "@/lib/hooks/use-users";
import { useRoles } from "@/lib/hooks/use-roles";
import { useAuditLogs } from "@/lib/hooks/use-audit";

const ALL_ROLES = [
  "super_admin",
  "admin",
  "executive",
  "recruiter",
  "hiring_manager",
  "interviewer",
  "candidate",
];

function formatLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function AdminClient() {
  const { data: users, isLoading: usersLoading } = useUsers();
  const { data: roles, isLoading: rolesLoading } = useRoles();
  const { data: auditLogs, isLoading: auditLoading } = useAuditLogs();
  const inviteMutation = useInviteUser();
  const updateUserMutation = useUpdateUser();

  const [search, setSearch] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("recruiter");

  const filteredUsers = (users ?? []).filter(
    (u) =>
      !search ||
      u.full_name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase()),
  );

  const userById = new Map((users ?? []).map((u) => [u.id, u]));

  function handleInvite() {
    if (!inviteEmail) return;
    inviteMutation.mutate(
      { email: inviteEmail, roleName: inviteRole },
      { onSuccess: () => setInviteEmail("") },
    );
  }

  const activeCount = (users ?? []).filter((u) => u.is_active).length;

  return (
    <AppShell title="Admin Console" breadcrumbs={[{ label: "Home", to: "/" }, { label: "Admin" }]}>
      <section className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <StatCard label="Total users" value={users?.length ?? 0} hint="Across all roles" />
        <StatCard label="Active" value={activeCount} tone="success" />
        <StatCard label="Deactivated" value={(users?.length ?? 0) - activeCount} tone="warning" />
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
          <TabsTrigger value="audit" className="gap-1.5">
            <Activity className="h-4 w-4" />
            Audit log
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-1.5">
            <Lock className="h-4 w-4" />
            Security
          </TabsTrigger>
          <TabsTrigger value="api" className="gap-1.5">
            <KeyRound className="h-4 w-4" />
            API & webhooks
          </TabsTrigger>
        </TabsList>

        <TabsContent value="users">
          <Card>
            <CardHeader className="flex flex-col gap-3">
              <div className="flex flex-row items-center justify-between gap-3 flex-wrap">
                <CardTitle className="text-base">Team members</CardTitle>
                <div className="relative w-full max-w-xs">
                  <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search users…"
                    className="pl-9 h-9"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Email to invite"
                  type="email"
                  className="h-9 max-w-xs"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
                <Select value={inviteRole} onValueChange={setInviteRole}>
                  <SelectTrigger className="h-9 w-[180px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ALL_ROLES.map((r) => (
                      <SelectItem key={r} value={r}>
                        {formatLabel(r)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button size="sm" onClick={handleInvite} disabled={!inviteEmail || inviteMutation.isPending}>
                  {inviteMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Invite user"}
                </Button>
              </div>
              {inviteMutation.isSuccess && (
                <div className="text-xs text-emerald-700">
                  Invitation created for {inviteMutation.data?.email} as {formatLabel(inviteMutation.data?.role_name ?? "")}.
                  Token: <code className="font-mono">{inviteMutation.data?.invitation_token}</code> — there&apos;s no
                  invite-acceptance page built in the frontend yet, so this token needs to be exchanged manually via
                  <code className="font-mono"> POST /api/v1/auth/invite/accept</code>.
                </div>
              )}
            </CardHeader>
            <CardContent className="p-0">
              {usersLoading ? (
                <div className="p-6 text-center text-sm text-muted-foreground">Loading…</div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="p-3 text-left">User</th>
                      <th className="p-3 text-left">Roles</th>
                      <th className="p-3 text-left">Status</th>
                      <th className="p-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map((u) => (
                      <tr key={u.id} className="border-t border-border hover:bg-muted/30">
                        <td className="p-3">
                          <div className="flex items-center gap-2.5">
                            <Avatar className="h-8 w-8">
                              <AvatarFallback className="text-[10px]">
                                {u.full_name
                                  .split(" ")
                                  .map((n) => n[0])
                                  .join("")
                                  .slice(0, 2)}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <div className="font-medium">{u.full_name}</div>
                              <div className="text-xs text-muted-foreground">{u.email}</div>
                            </div>
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="flex flex-wrap gap-1">
                            {u.roles.map((r) => (
                              <Badge key={r} variant="secondary" className="text-[11px]">
                                {formatLabel(r)}
                              </Badge>
                            ))}
                          </div>
                        </td>
                        <td className="p-3">
                          <span
                            className={cn(
                              "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
                              u.is_active
                                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                : "bg-red-50 text-red-700 border-red-200",
                            )}
                          >
                            {u.is_active ? "Active" : "Deactivated"}
                          </span>
                        </td>
                        <td className="p-3 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            className={u.is_active ? "text-destructive" : ""}
                            disabled={updateUserMutation.isPending}
                            onClick={() =>
                              updateUserMutation.mutate({ userId: u.id, input: { is_active: !u.is_active } })
                            }
                          >
                            {u.is_active ? "Deactivate" : "Activate"}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roles">
          {rolesLoading ? (
            <div className="p-6 text-center text-sm text-muted-foreground">Loading…</div>
          ) : (
            <div className="grid md:grid-cols-2 gap-4">
              {(roles ?? []).map((r) => (
                <Card key={r.id}>
                  <CardHeader className="flex flex-row items-start justify-between gap-3">
                    <div>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Shield className="h-4 w-4 text-primary" />
                        {r.display_name}
                      </CardTitle>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {(users ?? []).filter((u) => u.roles.includes(r.name)).length} members
                      </p>
                    </div>
                    <Badge variant="secondary" className="text-[11px] shrink-0">
                      {r.permissions.length} permissions
                    </Badge>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xs uppercase text-muted-foreground mb-1.5">Permissions</div>
                    <div className="flex flex-wrap gap-1.5">
                      {r.permissions.map((p) => (
                        <span
                          key={`${p.resource}:${p.action}`}
                          className="inline-flex items-center rounded-md border border-border bg-muted/40 px-2 py-0.5 text-[11px]"
                        >
                          {p.resource}:{p.action}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="audit">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent activity</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {auditLoading ? (
                <div className="p-6 text-center text-sm text-muted-foreground">Loading…</div>
              ) : (auditLogs ?? []).length === 0 ? (
                <div className="p-6 text-center text-sm text-muted-foreground">No audit events yet.</div>
              ) : (
                <ul className="divide-y divide-border">
                  {(auditLogs ?? []).map((log) => (
                    <li key={log.id} className="p-3 flex items-start gap-3">
                      <div className="h-8 w-8 rounded-md grid place-items-center shrink-0 bg-muted text-muted-foreground">
                        <Activity className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm">
                          <span className="font-medium">
                            {log.actor_user_id ? userById.get(log.actor_user_id)?.full_name ?? "Unknown user" : "System"}
                          </span>{" "}
                          {formatLabel(log.action)} —{" "}
                          <span className="text-muted-foreground">
                            {log.resource_type}
                            {log.resource_id ? ` (${log.resource_id.slice(0, 8)})` : ""}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {new Date(log.created_at).toLocaleString()}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardContent className="p-8 text-center text-sm text-muted-foreground">
              SSO, 2FA, and session-policy controls aren&apos;t built yet — there&apos;s no backend support for
              them in this version of the app.
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="api">
          <Card>
            <CardContent className="p-8 text-center text-sm text-muted-foreground">
              API keys and webhooks aren&apos;t built yet — there&apos;s no backend support for them in this
              version of the app.
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
