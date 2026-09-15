import type { Metadata } from "next";
import { Suspense } from "react";
import { ResetPasswordClient } from "./reset-password-client";

export const metadata: Metadata = {
  title: "Reset password",
  description: "Choose a new password for your ATS Tracker account.",
};

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordClient />
    </Suspense>
  );
}
