import type { Metadata } from "next";
import { ApplicationDetailClient } from "./application-detail-client";

export const metadata: Metadata = {
  title: "Application",
  description: "Application timeline, stage, interviews, and AI review.",
};

export default function ApplicationDetailPage() {
  return <ApplicationDetailClient />;
}
