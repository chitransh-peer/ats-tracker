import type { Metadata } from "next";
import { CandidatesClient } from "./candidates-client";

export const metadata: Metadata = {
  title: "Candidates",
  description: "Search, filter, and manage candidate profiles across the recruitment pipeline.",
};

export default function CandidatesList() {
  return <CandidatesClient />;
}
