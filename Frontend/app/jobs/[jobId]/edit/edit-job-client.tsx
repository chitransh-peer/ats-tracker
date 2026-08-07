"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { useJob } from "@/lib/hooks/use-jobs";
import { JobForm } from "../../job-form";

export function EditJobClient() {
  const params = useParams<{ jobId: string }>();
  const { data: job, isLoading } = useJob(params.jobId);

  if (isLoading) {
    return (
      <AppShell title="Edit job">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </AppShell>
    );
  }

  if (!job) {
    return (
      <AppShell title="Job not found">
        <div className="text-sm text-muted-foreground">
          This job doesn&apos;t exist or you don&apos;t have access.{" "}
          <Link href="/jobs" className="text-primary hover:underline">
            Back to jobs
          </Link>
        </div>
      </AppShell>
    );
  }

  return <JobForm job={job} />;
}
