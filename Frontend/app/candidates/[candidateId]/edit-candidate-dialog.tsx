"use client";

import { useState } from "react";
import { Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useUpdateCandidate } from "@/lib/hooks/use-candidates";
import { ApiError } from "@/lib/api/client";
import type { Candidate } from "@/lib/api/types";

const TEXT_FIELDS = [
  ["full_name", "Full name"],
  ["email", "Email"],
  ["phone", "Phone"],
  ["location", "Location"],
  ["current_company", "Current company"],
  ["current_title", "Current title"],
  ["work_auth", "Work authorization"],
  ["notice_period", "Notice period"],
  ["linkedin_url", "LinkedIn URL"],
] as const;

type TextField = (typeof TEXT_FIELDS)[number][0];

function initial(candidate: Candidate) {
  const form: Record<TextField | "skills" | "experience", string> = {
    full_name: candidate.full_name,
    email: candidate.email ?? "",
    phone: candidate.phone ?? "",
    location: candidate.location ?? "",
    current_company: candidate.current_company ?? "",
    current_title: candidate.current_title ?? "",
    work_auth: candidate.work_auth ?? "",
    notice_period: candidate.notice_period ?? "",
    linkedin_url: candidate.linkedin_url ?? "",
    skills: candidate.skills.join(", "),
    experience: candidate.total_experience_years?.toString() ?? "",
  };
  return form;
}

/**
 * Corrects or completes a candidate's details -- including records migrated
 * from Ceipal with gaps or inconsistencies. Only changed fields are sent; a
 * cleared field is cleared.
 */
export function EditCandidateDialog({ candidate }: { candidate: Candidate }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(() => initial(candidate));
  const [error, setError] = useState<string | null>(null);
  const update = useUpdateCandidate(candidate.id);

  function onOpenChange(next: boolean) {
    if (next) {
      setForm(initial(candidate));
      setError(null);
    }
    setOpen(next);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const before = initial(candidate);
    const changes: Parameters<typeof update.mutateAsync>[0] = {};
    for (const [key] of TEXT_FIELDS) {
      const value = form[key].trim();
      if (value === before[key].trim()) continue;
      if (key === "full_name" && !value) {
        setError("A candidate needs a name.");
        return;
      }
      // An email can be corrected but not blanked out.
      if (key === "email") {
        if (value) changes.email = value;
        continue;
      }
      changes[key] = value;
    }
    if (form.skills !== before.skills) {
      changes.skills = form.skills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    }
    if (form.experience !== before.experience && form.experience.trim()) {
      const years = Number(form.experience);
      if (!Number.isFinite(years) || years < 0 || years > 70) {
        setError("Experience must be a number of years between 0 and 70.");
        return;
      }
      changes.total_experience_years = years;
    }
    if (Object.keys(changes).length === 0) {
      setOpen(false);
      return;
    }
    try {
      await update.mutateAsync(changes);
      setOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save changes.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <Pencil className="h-4 w-4 mr-1" />
          Edit details
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit candidate</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="grid gap-3 sm:grid-cols-2">
            {TEXT_FIELDS.map(([key, label]) => (
              <div key={key} className="space-y-1.5">
                <Label className="text-xs" htmlFor={`edit-${key}`}>
                  {label}
                </Label>
                <Input
                  id={`edit-${key}`}
                  type={key === "email" ? "email" : "text"}
                  value={form[key]}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                  maxLength={key === "linkedin_url" ? 500 : 255}
                  required={key === "full_name"}
                />
              </div>
            ))}
            <div className="space-y-1.5">
              <Label className="text-xs" htmlFor="edit-experience">
                Total experience (years)
              </Label>
              <Input
                id="edit-experience"
                type="number"
                min="0"
                max="70"
                step="0.5"
                value={form.experience}
                onChange={(e) => setForm((f) => ({ ...f, experience: e.target.value }))}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs" htmlFor="edit-skills">
              Skills (comma separated)
            </Label>
            <Input
              id="edit-skills"
              value={form.skills}
              onChange={(e) => setForm((f) => ({ ...f, skills: e.target.value }))}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={update.isPending}>
              {update.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
