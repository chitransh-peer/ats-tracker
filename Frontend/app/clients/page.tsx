import type { Metadata } from "next";
import { ClientsClient } from "./clients-client";

export const metadata: Metadata = {
  title: "Clients",
  description:
    "Manage client accounts, active requisitions, and account owners across your recruiting portfolio.",
  alternates: { canonical: "/clients" },
  openGraph: {
    title: "Clients — ATS Tracker",
    description: "Client account management for recruiting operations.",
  },
};

export default function ClientsPage() {
  return <ClientsClient />;
}
