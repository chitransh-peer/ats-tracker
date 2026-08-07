import type { Metadata } from "next";
import { VendorDetailClient } from "./vendor-detail-client";

export const metadata: Metadata = {
  title: "Vendor",
  description:
    "Vendor snapshot with accounts, notes, contacts, documents, meeting schedules, and vendor information.",
};

export default function VendorDetailPage() {
  return <VendorDetailClient />;
}
