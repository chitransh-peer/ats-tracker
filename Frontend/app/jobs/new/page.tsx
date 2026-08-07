import type { Metadata } from "next";
import { JobForm } from "../job-form";

export const metadata: Metadata = {
  title: "New Job",
  description:
    "Create a new job requisition with job details, skills, and organizational information.",
};

export default function NewJob() {
  return <JobForm />;
}
