import type { Metadata } from "next";
import { ChangePasswordClient } from "./change-password-client";

export const metadata: Metadata = {
  title: "Choose your password",
  description: "Replace your temporary password with one of your own.",
};

export default function Page() {
  return <ChangePasswordClient />;
}
