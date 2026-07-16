import type { Metadata } from "next";
import { DashboardClient } from "./dashboard-client";

export const metadata: Metadata = {
  title: "Dashboard",
  description:
    "Recruiter dashboard: pipelines, interviews, offers, AI candidate scores and productivity insights.",
};

export default function Page() {
  return <DashboardClient />;
}
