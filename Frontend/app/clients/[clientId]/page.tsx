import type { Metadata } from "next";
import { ClientDetailClient } from "./client-detail-client";

export const metadata: Metadata = {
  title: "Client",
  description:
    "Client snapshot with accounts, contacts, notes, documents, and account information.",
};

export default function ClientDetailPage() {
  return <ClientDetailClient />;
}
