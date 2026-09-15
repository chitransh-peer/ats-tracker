import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Emits a self-contained server bundle with only the traced runtime deps, so
  // the production image doesn't need to carry node_modules.
  output: "standalone",
};

export default nextConfig;
