import type { Metadata } from "next";
import { VendorsClient } from "./vendors-client";

export const metadata: Metadata = {
  title: "Vendors",
  description:
    "Track staffing vendors, submission volume, and partnership status for your recruiting supply chain.",
  alternates: { canonical: "/vendors" },
  openGraph: {
    title: "Vendors — ATS Tracker",
    description: "Vendor management for recruiting operations.",
  },
};

export default function VendorsPage() {
  return <VendorsClient />;
}
