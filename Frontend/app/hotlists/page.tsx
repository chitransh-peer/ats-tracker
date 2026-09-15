import type { Metadata } from "next";
import { HotlistsClient } from "./hotlists-client";

export const metadata: Metadata = {
  title: "Hotlists",
  description: "Curated consultant lists sent to clients and vendors.",
};

export default function HotlistsPage() {
  return <HotlistsClient />;
}
