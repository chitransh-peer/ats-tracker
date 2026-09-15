import type { MetadataRoute } from "next";

export const dynamic = "force-static"; // Force static generation for export

const siteUrl = "https://ats-tracker.example.com";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/admin", "/auth", "/settings"] }],
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
