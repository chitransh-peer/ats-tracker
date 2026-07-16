import type { Metadata } from "next";
import { PipelineClient } from "./pipeline-client";

export const metadata: Metadata = {
  title: "Pipeline",
  description: "Visual hiring pipeline across all active applications and stages.",
};

export default function Pipeline() {
  return <PipelineClient />;
}
