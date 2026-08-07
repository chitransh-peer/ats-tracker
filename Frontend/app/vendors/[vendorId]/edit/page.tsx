import type { Metadata } from "next";
import { EditVendorClient } from "./edit-vendor-client";

export const metadata: Metadata = {
  title: "Edit Vendor",
  description: "Update a vendor's business information, submission format, and bank details.",
};

export default function EditVendorPage() {
  return <EditVendorClient />;
}
