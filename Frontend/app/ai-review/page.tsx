import type { Metadata } from "next";
import { AIReviewClient } from "./ai-review-client";

export const metadata: Metadata = {
  title: "AI Resume Review",
  description:
    "AI-assisted resume parsing, JD vs Resume comparison, match scoring, strengths and gaps analysis.",
};

export default function Page() {
  return <AIReviewClient />;
}
