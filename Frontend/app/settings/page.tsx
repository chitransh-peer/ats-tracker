import type { Metadata } from "next";
import { SettingsClient } from "./settings-client";

export const metadata: Metadata = {
  title: "Settings",
  description: "Configure workspace settings and email templates.",
};

export default function Page() {
  return <SettingsClient />;
}
