"use client";

import { useState } from "react";
import { useAuditLogs, useAuditSummaryByUser } from "@/lib/hooks/use-audit";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity } from "lucide-react";
import { cn } from "@/lib/utils";

function formatLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function AuditPanel() {
  const { data: summary, isLoading: summaryLoading } = useAuditSummaryByUser();
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  const { data: logs, isLoading: logsLoading } = useAuditLogs(
    selectedUserId ? { actor_user_id: selectedUserId } : {},
  );

  const selected = (summary ?? []).find((s) => s.actor_user_id === selectedUserId);

  return (
    <div className="grid md:grid-cols-[280px_1fr] gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">By user</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {summaryLoading ? (
            <div className="p-4 text-center text-sm text-muted-foreground">Loading…</div>
          ) : (summary ?? []).length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">No activity yet.</div>
          ) : (
            <ul className="divide-y divide-border">
              <li>
                <button
                  onClick={() => setSelectedUserId(null)}
                  className={cn(
                    "w-full text-left p-3 hover:bg-muted/40",
                    selectedUserId === null && "bg-muted/60",
                  )}
                >
                  <div className="text-sm font-medium">All activity</div>
                  <div className="text-xs text-muted-foreground">Org-wide stream</div>
                </button>
              </li>
              {(summary ?? []).map((row) => (
                <li key={row.actor_user_id ?? "system"}>
                  <button
                    onClick={() => setSelectedUserId(row.actor_user_id)}
                    className={cn(
                      "w-full text-left p-3 hover:bg-muted/40",
                      selectedUserId === row.actor_user_id && "bg-muted/60",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium truncate">
                        {row.full_name ?? (row.actor_user_id ? "Unknown user" : "System")}
                      </span>
                      <Badge variant="secondary" className="text-[10px] shrink-0">
                        {row.event_count}
                      </Badge>
                    </div>
                    {row.email && (
                      <div className="text-xs text-muted-foreground truncate">{row.email}</div>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {selected ? `${selected.full_name ?? "User"} — activity` : "Recent activity"}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {logsLoading ? (
            <div className="p-6 text-center text-sm text-muted-foreground">Loading…</div>
          ) : (logs ?? []).length === 0 ? (
            <div className="p-6 text-center text-sm text-muted-foreground">No audit events.</div>
          ) : (
            <ul className="divide-y divide-border">
              {(logs ?? []).map((log) => (
                <li key={log.id} className="p-3 flex items-start gap-3">
                  <div className="h-8 w-8 rounded-md grid place-items-center shrink-0 bg-muted text-muted-foreground">
                    <Activity className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm">
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
    </div>
  );
}
