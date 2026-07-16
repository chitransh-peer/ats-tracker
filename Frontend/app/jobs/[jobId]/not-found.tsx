import { AppShell } from "@/components/layout/AppShell";

export default function JobNotFound() {
  return (
    <AppShell title="Job not found">
      <p className="text-muted-foreground">This requisition may have been closed or moved.</p>
    </AppShell>
  );
}
