import type { Metadata } from "next";
import { TalentBenchClient } from "./talent-bench-client";

export const metadata: Metadata = {
  title: "Talent Bench",
  description: "Consultants available to market to clients and vendors.",
};

export default function TalentBenchPage() {
  return <TalentBenchClient />;
}
