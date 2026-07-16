import type { Metadata } from "next";
import { NewJobClient } from "./new-job-client";

export const metadata: Metadata = {
  title: "New Job",
  description: "Create a new job requisition with description, skills, and screening questions.",
};

export default function NewJob() {
  return <NewJobClient />;
}
