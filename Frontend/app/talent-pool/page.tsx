import type { Metadata } from "next";
import { TalentPoolClient } from "./talent-pool-client";

export const metadata: Metadata = {
  title: "Talent Pool",
  description: "Saved candidates, silver medalists, and past applicants ready for re-engagement.",
};

export default function TalentPool() {
  return <TalentPoolClient />;
}
