import type { Metadata } from "next";
import { OffersClient } from "./offers-client";

export const metadata: Metadata = {
  title: "Offers",
  description: "Manage offer letters, approval chains, and compensation packages.",
};

export default function OffersPage() {
  return <OffersClient />;
}
