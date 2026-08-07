import type { Metadata } from "next";
import { EditJobClient } from "./edit-job-client";

export const metadata: Metadata = {
  title: "Edit Job",
  description: "Update a job requisition's details, skills, and organizational information.",
};

export default function EditJobPage() {
  return <EditJobClient />;
}
