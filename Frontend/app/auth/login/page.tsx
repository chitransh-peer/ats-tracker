import type { Metadata } from "next";
import { LoginClient } from "./login-client";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to ATS Tracker to manage requisitions, pipelines, and hiring workflows.",
  robots: { index: false, follow: false },
  alternates: { canonical: "/auth/login" },
  openGraph: {
    title: "Sign in — ATS Tracker",
    description: "Access your recruiting workspace.",
  },
};

export default function LoginPage() {
  return <LoginClient />;
}
