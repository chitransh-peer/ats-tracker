import type { Metadata } from "next";
import { CandidateDetailClient } from "./candidate-detail-client";

export const metadata: Metadata = {
  title: "Candidate",
  description: "Full candidate profile with applications, interviews, and notes.",
  robots: { index: false, follow: false },
};

export default function CandidateDetail() {
  return <CandidateDetailClient />;
}
