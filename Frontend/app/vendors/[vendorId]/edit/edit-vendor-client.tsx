"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { useVendor } from "@/lib/hooks/use-vendors";
import { VendorForm } from "../../vendor-form";

export function EditVendorClient() {
  const params = useParams<{ vendorId: string }>();
  const { data: vendor, isLoading } = useVendor(params.vendorId);

  if (isLoading) {
    return (
      <AppShell title="Edit vendor">
        <div className="text-sm text-muted-foreground">Loading…</div>
      </AppShell>
    );
  }

  if (!vendor) {
    return (
      <AppShell title="Vendor not found">
        <div className="text-sm text-muted-foreground">
          This vendor doesn&apos;t exist or you don&apos;t have access.{" "}
          <Link href="/vendors" className="text-primary hover:underline">
            Back to vendors
          </Link>
        </div>
      </AppShell>
    );
  }

  return <VendorForm vendor={vendor} />;
}
