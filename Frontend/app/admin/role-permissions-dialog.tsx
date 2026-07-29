"use client";

import { useMemo, useState } from "react";
import { useUpdateRolePermissions } from "@/lib/hooks/use-roles";
import { ApiError } from "@/lib/api/client";
import type { Role } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

const RESOURCES = [
  "organization",
  "user",
  "role",
  "job",
  "candidate",
  "application",
  "pipeline",
  "ai_evaluation",
  "interview",
  "offer",
  "onboarding",
  "report",
  "template",
  "settings",
  "audit_log",
  "client",
  "vendor",
];
const ACTIONS = ["create", "read", "update", "delete", "manage"];

function keyOf(resource: string, action: string) {
  return `${resource}:${action}`;
}

export function RolePermissionsDialog({
  role,
  open,
  onOpenChange,
}: {
  role: Role;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const mutation = useUpdateRolePermissions();
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(role.permissions.map((p) => keyOf(p.resource, p.action))),
  );

  // Re-seed local state whenever a different role is opened.
  const initialKey = useMemo(() => role.id, [role.id]);
  const [trackedRole, setTrackedRole] = useState(initialKey);
  if (trackedRole !== initialKey) {
    setTrackedRole(initialKey);
    setSelected(new Set(role.permissions.map((p) => keyOf(p.resource, p.action))));
    setError(null);
  }

  function toggle(resource: string, action: string) {
    const k = keyOf(resource, action);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });
  }

  async function handleSave() {
    setError(null);
    const permissions = Array.from(selected).map((k) => {
      const [resource, action] = k.split(":");
      return { resource, action };
    });
    try {
      await mutation.mutateAsync({ roleId: role.id, permissions });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save permissions.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit permissions — {role.display_name}</DialogTitle>
        </DialogHeader>
        {error && <div className="text-sm text-destructive">{error}</div>}
        <div className="max-h-[60vh] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-background">
              <tr className="text-[11px] uppercase text-muted-foreground">
                <th className="p-2 text-left">Resource</th>
                {ACTIONS.map((a) => (
                  <th key={a} className="p-2 text-center">
                    {a}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {RESOURCES.map((resource) => (
                <tr key={resource} className="border-t border-border">
                  <td className="p-2 font-medium">{resource}</td>
                  {ACTIONS.map((action) => (
                    <td key={action} className="p-2 text-center">
                      <Checkbox
                        checked={selected.has(keyOf(resource, action))}
                        onCheckedChange={() => toggle(resource, action)}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={mutation.isPending}>
            {mutation.isPending ? "Saving…" : "Save permissions"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
