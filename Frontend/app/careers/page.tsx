import type { Metadata } from "next";
import { CareersClient } from "./careers-client";

export const metadata: Metadata = {
  title: "Careers — Peer Consulting Resources Inc.",
  description: "Explore open roles at Peer Consulting Resources Inc. and grow your career with us.",
};

export default function Careers() {
  return <CareersClient />;
}
