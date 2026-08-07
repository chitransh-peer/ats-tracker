import type { Metadata } from "next";
import { EditClientClient } from "./edit-client-client";

export const metadata: Metadata = {
  title: "Edit Client",
  description: "Update a client's business information, guidelines, markup, and submission format.",
};

export default function EditClientPage() {
  return <EditClientClient />;
}
