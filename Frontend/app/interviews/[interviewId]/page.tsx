import type { Metadata } from "next";
import { InterviewDetailClient } from "./interview-detail-client";

export const metadata: Metadata = {
  title: "Interview",
  description: "Interview details, panel, and feedback.",
};

export default function InterviewDetailPage() {
  return <InterviewDetailClient />;
}
