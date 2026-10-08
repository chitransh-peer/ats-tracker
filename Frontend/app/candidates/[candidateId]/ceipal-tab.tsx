"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getCeipalProfile, updateCeipalProfile } from "@/lib/api/ceipal";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import { CandidateDocumentLink } from "@/components/document-preview-dialog";

/** Everything Ceipal held on a candidate, under Ceipal's own headers. */
export function CeipalTab({
  candidateId,
  canEdit = false,
}: {
  candidateId: string;
  /** Whether the viewer may correct the migrated record. */
  canEdit?: boolean;
}) {
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useQuery({
    queryKey: ["ceipal-candidates", "profile", candidateId],
    queryFn: () => getCeipalProfile(candidateId),
  });
  // The values being edited, or null when not editing.
  const [draft, setDraft] = useState<Record<string, string> | null>(null);
  const saving = useMutation({
    mutationFn: (values: Record<string, string>) => updateCeipalProfile(candidateId, values),
    onSuccess: () => {
      // The candidate's own fields follow the correction too.
      void queryClient.invalidateQueries({ queryKey: ["ceipal-candidates"] });
      void queryClient.invalidateQueries({ queryKey: ["candidates"] });
    },
  });

  async function save() {
    if (!profile || !draft) return;
    const changed = Object.fromEntries(
      Object.entries(draft).filter(
        ([column, value]) =>
          !profile.read_only_columns.includes(column) &&
          (profile.values[column] ?? "") !== value.trim(),
      ),
    );
    if (Object.keys(changed).length === 0) {
      setDraft(null);
      return;
    }
    try {
      await saving.mutateAsync(changed);
      setDraft(null);
      toast.success("Ceipal record updated.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't save the changes.");
    }
  }

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading…</div>;
  if (!profile) return null;
  const resume = profile.resume;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Resume</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {resume ? (
            <CandidateDocumentLink
              candidateId={candidateId}
              documentId={resume.document_id}
              fileName={resume.file_name}
            />
          ) : (
            <span className="text-muted-foreground">
              No résumé yet. It is attached when the backup&apos;s documents ZIP is imported.
            </span>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2 flex-row items-center justify-between gap-3 space-y-0">
          <div>
            <CardTitle className="text-base">Ceipal record</CardTitle>
            {profile.edited_columns.length > 0 && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {profile.edited_columns.length} field
                {profile.edited_columns.length === 1 ? "" : "s"} corrected here — kept when the next
                backup is imported.
              </p>
            )}
          </div>
          {canEdit &&
            (draft === null ? (
              <Button size="sm" variant="outline" onClick={() => setDraft({ ...profile.values })}>
                <Pencil className="h-4 w-4 mr-1" />
                Edit
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => setDraft(null)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={() => void save()} disabled={saving.isPending}>
                  {saving.isPending ? "Saving…" : "Save"}
                </Button>
              </div>
            ))}
        </CardHeader>
        <CardContent>
          <dl className="grid sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
            {profile.columns.map((column) => {
              const editable = draft !== null && !profile.read_only_columns.includes(column);
              const edited = profile.edited_columns.includes(column);
              return (
                <div
                  key={column}
                  className={cn(
                    "flex justify-between items-center gap-3 border-b py-1.5 min-w-0",
                    (profile.values[column]?.length ?? 0) > 80 && "sm:col-span-2",
                  )}
                >
                  <dt className="text-muted-foreground shrink-0">
                    {column}
                    {edited && (
                      <span className="ml-1 text-[10px] text-amber-700" title="Corrected here">
                        • edited
                      </span>
                    )}
                  </dt>
                  {editable ? (
                    <Input
                      className="h-7 max-w-[60%] text-right"
                      value={draft[column] ?? ""}
                      onChange={(e) =>
                        setDraft((d) => (d ? { ...d, [column]: e.target.value } : d))
                      }
                      aria-label={column}
                    />
                  ) : (
                    <dd className="font-medium text-right break-words min-w-0">
                      {profile.values[column] || "—"}
                    </dd>
                  )}
                </div>
              );
            })}
          </dl>
        </CardContent>
      </Card>

      {profile.submissions.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Ceipal submissions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {profile.submissions.map((s) => (
              <div key={s.submission_id} className="rounded-md border p-3 text-sm space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{s.job_title ?? s.job_code}</span>
                  {s.job_title && (
                    <span className="text-xs text-muted-foreground">{s.job_code}</span>
                  )}
                  <Badge variant="secondary" className="text-[10px]">
                    {s.status || "—"}
                  </Badge>
                  {s.application_id && (
                    <Link
                      href={`/applications/${s.application_id}`}
                      className="text-xs text-primary hover:underline"
                    >
                      Open application
                    </Link>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  Submitted {s.submitted_on || "—"}
                  {s.submitted_by && ` by ${s.submitted_by}`} · Source {s.source || "—"} · Pay{" "}
                  {s.pay_rate || "—"} · Bill {s.bill_rate || "—"}
                </div>
                {s.notes.map((n, i) => (
                  <div key={i} className="text-xs border-l-2 pl-2">
                    {n.subject && <span className="font-medium">{n.subject}: </span>}
                    {n.note}
                  </div>
                ))}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
