import type { Metadata } from "next";
import { JobDetailClient } from "./job-detail-client";

export const metadata: Metadata = {
  title: "Job",
  description: "Job details, pipeline, applications, and hiring team.",
};

export default function JobDetail() {
  return <JobDetailClient />;
}
