import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

const siteUrl = "https://ats-tracker.example.com";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "ATS Tracker — Modern Recruiting Operations Platform",
    template: "%s — ATS Tracker",
  },
  description:
    "ATS Tracker centralizes recruitment: job requisitions, candidate pipelines, AI resume review, interviews, offers, and analytics for modern hiring teams.",
  authors: [{ name: "ATS Tracker" }],
  openGraph: {
    title: "ATS Tracker — Recruiting Operations Platform",
    description:
      "Run every part of hiring — from requisition to onboarding — with AI-assisted candidate matching, pipelines, interviews, and reporting.",
    type: "website",
    siteName: "ATS Tracker",
    url: siteUrl,
  },
  twitter: {
    card: "summary_large_image",
  },
  icons: {
    icon: "/favicon.ico",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
