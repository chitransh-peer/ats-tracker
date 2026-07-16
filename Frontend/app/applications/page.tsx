import type { Metadata } from "next";
import { ApplicationsClient } from "./applications-client";

export const metadata: Metadata = {
  title: "Applications",
  description: "Review all incoming applications across jobs with current stage and status.",
};

export default function Applications() {
  return <ApplicationsClient />;
}
