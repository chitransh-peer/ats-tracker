import type { Metadata } from "next";
import { Suspense } from "react";
import { AcceptInviteClient } from "./accept-invite-client";

export const metadata: Metadata = {
  title: "Accept invitation",
  description: "Set up your account to join the workspace.",
};

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={null}>
      <AcceptInviteClient />
    </Suspense>
  );
}
