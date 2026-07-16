import type { Metadata } from "next";
import { JobsClient } from "./jobs-client";

export const metadata: Metadata = {
  title: "Jobs",
  description:
    "Manage job requisitions, statuses, applications, and pipeline metrics across all open roles.",
};

export default function JobsList() {
  return <JobsClient />;
}
