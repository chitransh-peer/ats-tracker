import type { Metadata } from "next";
import { InterviewsClient } from "./interviews-client";

export const metadata: Metadata = {
  title: "Interviews",
  description: "Schedule, track, and collect feedback for candidate interviews across all rounds.",
};

export default function Interviews() {
  return <InterviewsClient />;
}
