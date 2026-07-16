import type { Metadata } from "next";
import Link from "next/link";
import { jobs } from "@/lib/mock-data";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Building2, MapPin, Briefcase, Search } from "lucide-react";

export const metadata: Metadata = {
  title: "Careers — Acme Technologies",
  description: "Explore open roles at Acme and help us build enterprise software teams love.",
};

export default function Careers() {
  const open = jobs.filter((j) => j.status === "Active");
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold">
            <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center text-primary-foreground text-sm font-bold">
              A
            </div>
            Acme Technologies
          </div>
          <nav className="flex items-center gap-6 text-sm">
            <a href="#" className="text-muted-foreground hover:text-foreground">
              About
            </a>
            <a href="#" className="text-muted-foreground hover:text-foreground">
              Life at Acme
            </a>
            <Link href="/" className="text-muted-foreground hover:text-foreground">
              ATS admin
            </Link>
          </nav>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 py-16 text-center">
        <Badge variant="secondary" className="mb-4">
          We&apos;re hiring — {open.length} open roles
        </Badge>
        <h1 className="text-5xl font-semibold tracking-tight">Build the future with us.</h1>
        <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
          Join a global team of engineers, designers and operators shipping enterprise software
          loved by teams everywhere.
        </p>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-16">
        <div className="flex gap-3 mb-6">
          <div className="flex-1 relative">
            <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
            <Input placeholder="Search roles" className="pl-9" />
          </div>
          <Button variant="outline">All departments</Button>
          <Button variant="outline">All locations</Button>
        </div>
        <div className="border rounded-lg divide-y bg-white">
          {open.map((j) => (
            <div
              key={j.id}
              className="p-5 flex items-center justify-between hover:bg-muted/30 transition-colors"
            >
              <div>
                <div className="font-medium">{j.title}</div>
                <div className="text-sm text-muted-foreground flex items-center gap-4 mt-1">
                  <span className="flex items-center gap-1">
                    <Building2 className="h-3.5 w-3.5" />
                    {j.department}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" />
                    {j.location}
                  </span>
                  <span className="flex items-center gap-1">
                    <Briefcase className="h-3.5 w-3.5" />
                    {j.employmentType}
                  </span>
                </div>
              </div>
              <Button size="sm">Apply</Button>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t py-8 text-center text-xs text-muted-foreground">
        © 2026 Acme Technologies · Powered by ATS Tracker
      </footer>
    </div>
  );
}
