import type { Metadata } from "next";
import { HotlistDetailClient } from "./hotlist-detail-client";

export const metadata: Metadata = {
  title: "Hotlist",
  description: "Build a consultant list, choose recipients, and send it.",
};

export default function HotlistDetailPage() {
  return <HotlistDetailClient />;
}
