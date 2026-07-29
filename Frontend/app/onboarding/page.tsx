import type { Metadata } from "next";
import { OnboardingClient } from "./onboarding-client";

export const metadata: Metadata = {
  title: "Onboarding",
  description: "Track pre-boarding checklists for accepted hires through to their start date.",
};

export default function OnboardingPage() {
  return <OnboardingClient />;
}
