"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileText, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getCeipalProfile } from "@/lib/api/ceipal";
import { downloadFile } from "@/lib/api/client";

/** Everything Ceipal held on a candidate, under Ceipal's own headers. */
export function CeipalTab({ candidateId }: { candidateId: string }) {
  const { data: profile, isLoading } = useQuery({
    queryKey: ["ceipal-candidates", "profile", candidateId],
    queryFn: () => getCeipalProfile(candidateId),
  });
  const [downloading, setDownloading] = useState(false);

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading…</div>;
  if (!profile) return null;
  const resume = profile.resume;

  async function downloadResume() {
    if (!resume) return;
    setDownloading(true);
    try {
      await downloadFile(
        `/candidates/${candidateId}/documents/${resume.document_id}/download`,
        resume.file_name,
      );
    } catch {
      toast.error("Couldn't download the résumé. Try again.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Resume</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {resume ? (
            <button
              type="button"
              onClick={() => void downloadResume()}
              disabled={downloading}
              className="inline-flex items-center gap-1.5 text-primary hover:underline"
            >
              {downloading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileText className="h-4 w-4" />
              )}
              {resume.file_name}
            </button>
          ) : (
            <span className="text-muted-foreground">
              No résumé yet. It is attached when the backup&apos;s documents ZIP is imported.
            </span>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Ceipal record</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
            {profile.columns.map((column) => (
              <div
                key={column}
                className={
                  (profile.values[column]?.length ?? 0) > 80
                    ? "sm:col-span-2 flex justify-between gap-3 border-b py-1.5 min-w-0"
                    : "flex justify-between gap-3 border-b py-1.5 min-w-0"
                }
              >
                <dt className="text-muted-foreground shrink-0">{column}</dt>
                <dd className="font-medium text-right break-words min-w-0">
                  {profile.values[column] || "—"}
                </dd>
              </div>
            ))}
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
