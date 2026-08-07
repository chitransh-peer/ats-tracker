import type { Metadata } from "next";
import { ClientForm } from "../client-form";

export const metadata: Metadata = {
  title: "New Client",
  description:
    "Create a client account with business information, accounts, contacts, guidelines, and submission format.",
};

export default function NewClientPage() {
  return <ClientForm />;
}
