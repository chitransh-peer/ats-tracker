import type { MetadataRoute } from "next";

const siteUrl = "https://ats-tracker.example.com";

const routes = [
  "",
  "/jobs",
  "/jobs/new",
  "/applications",
  "/candidates",
  "/talent-pool",
  "/pipeline",
  "/interviews",
  "/offers",
  "/ai-review",
  "/clients",
  "/vendors",
  "/reports",
  "/templates",
  "/careers",
];

export default function sitemap(): MetadataRoute.Sitemap {
  return routes.map((route) => ({
    url: `${siteUrl}${route}`,
    lastModified: new Date(),
  }));
}
