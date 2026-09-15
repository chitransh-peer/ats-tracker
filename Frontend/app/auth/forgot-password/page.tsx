import type { Metadata } from "next";
import { ForgotPasswordClient } from "./forgot-password-client";

export const metadata: Metadata = {
  title: "Forgot password",
  description: "Request a link to reset your ATS Tracker password.",
};

export default function ForgotPasswordPage() {
  return <ForgotPasswordClient />;
}
