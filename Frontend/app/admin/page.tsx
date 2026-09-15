import type { Metadata } from "next";
import { AdminClient } from "./admin-client";

export const metadata: Metadata = {
  title: "Admin Console",
  description: "Manage users, roles, permissions, and audit logs across the ATS.",
  robots: { index: false, follow: false },
  alternates: { canonical: "/admin" },
  openGraph: {
    title: "Admin Console — ATS Tracker",
    description: "Administer users, roles, and audit logs.",
  },
};

export default function Page() {
  return <AdminClient />;
}
