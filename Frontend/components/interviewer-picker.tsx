"use client";

import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useUserOptions } from "@/lib/hooks/use-users";

/**
 * Picks the interview panel from the organization's active users. The first
 * one picked leads the round; the order is kept so the server can mark them.
 */
export function InterviewerPicker({
  value,
  onChange,
}: {
  value: string[];
  onChange: (next: string[]) => void;
}) {
  const { data: users, isLoading } = useUserOptions();
  const nameOf = new Map((users ?? []).map((u) => [u.id, u.full_name]));
  const remaining = (users ?? []).filter((u) => !value.includes(u.id));

  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map((id, i) => (
            <Badge key={id} variant="secondary" className="gap-1 pr-1 text-xs font-normal">
              {nameOf.get(id) ?? "Unknown"}
              {i === 0 && <span className="text-[10px] text-muted-foreground">· Lead</span>}
              <button
                type="button"
                aria-label={`Remove ${nameOf.get(id) ?? "interviewer"}`}
                onClick={() => onChange(value.filter((v) => v !== id))}
                className="rounded-sm p-0.5 hover:bg-muted"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
      <Select value="" onValueChange={(id) => onChange([...value, id])}>
        <SelectTrigger>
          <SelectValue
            placeholder={
              isLoading ? "Loading…" : value.length ? "Add another interviewer" : "Add interviewer"
            }
          />
        </SelectTrigger>
        <SelectContent>
          {remaining.length === 0 ? (
            <div className="px-2 py-1.5 text-xs text-muted-foreground">No more users</div>
          ) : (
            remaining.map((u) => (
              <SelectItem key={u.id} value={u.id}>
                {u.full_name}
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>
    </div>
  );
}
