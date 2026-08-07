"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { useClient } from "@/lib/hooks/use-clients";
import { ClientForm } from "../../client-form";

export function EditClientClient() {
  const params = useParams<{ clientId: string }>();
  const { data: client, isLoading } = useClient(params.clientId);

  if (isLoading) {
    return (
      <AppShell title="Edit client">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </AppShell>
    );
  }

  if (!client) {
    return (
      <AppShell title="Client not found">
        <div className="text-sm text-muted-foreground">
          This client doesn&apos;t exist or you don&apos;t have access.{" "}
          <Link href="/clients" className="text-primary hover:underline">
            Back to clients
          </Link>
        </div>
      </AppShell>
    );
  }

  return <ClientForm client={client} />;
}
