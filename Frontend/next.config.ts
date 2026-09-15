import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Change "export" back to "standalone" to allow dynamic routing in Cloud Run
  output: "standalone",
};

export default nextConfig;
