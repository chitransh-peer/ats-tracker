import type { MetadataRoute } from "next";

const siteUrl = "https://ats-tracker.example.com";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/admin", "/auth", "/settings"] }],
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
