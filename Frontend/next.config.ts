import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Ensure Next.js generates the 'out' directory for static hosting on Firebase
  output: "export",
  // Disable native Next.js image optimization as it is not supported in static exports
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
