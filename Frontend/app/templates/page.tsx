import type { Metadata } from "next";
import { TemplatesClient } from "./templates-client";

export const metadata: Metadata = {
  title: "Email Templates",
  description:
    "Create and manage recruiting email templates for acknowledgments, invites, offers, follow-ups, and rejections.",
  alternates: { canonical: "/templates" },
  openGraph: {
    title: "Email Templates — ATS Tracker",
    description: "Reusable recruiting email templates with tokens.",
  },
};

export default function TemplatesPage() {
  return <TemplatesClient />;
}
