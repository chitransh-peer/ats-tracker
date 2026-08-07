import type { Metadata } from "next";
import { VendorForm } from "../vendor-form";

export const metadata: Metadata = {
  title: "New Vendor",
  description:
    "Add a vendor with business information, accounts, notes, contacts, submission format, and bank details.",
};

export default function NewVendorPage() {
  return <VendorForm />;
}
