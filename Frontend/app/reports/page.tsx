import type { Metadata } from "next";
import { ReportsClient } from "./reports-client";

export const metadata: Metadata = {
  title: "Reports",
  description:
    "Hiring funnel, time-to-fill, source effectiveness, recruiter productivity, and AI insights.",
};

export default function Page() {
  return <ReportsClient />;
}
