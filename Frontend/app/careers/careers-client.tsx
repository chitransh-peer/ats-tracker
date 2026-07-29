"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  getPublicOrganization,
  listPublicJobs,
  applyToJob,
  type PublicJob,
} from "@/lib/api/careers-public";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Building2, MapPin, Briefcase, Search, CheckCircle2 } from "lucide-react";

function ApplyDialog({
  job,
  onClose,
}: {
  job: PublicJob | null;
  onClose: () => void;
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [resume, setResume] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const mutation = useMutation({
    mutationFn: () =>
      applyToJob(job!.id, { full_name: fullName, email, phone: phone || undefined, resume }),
    onSuccess: () => setDone(true),
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again."),
  });

  function reset() {
    setFullName("");
    setEmail("");
    setPhone("");
    setResume(null);
    setError(null);
    setDone(false);
  }

  function handleClose() {
    reset();
    onClose();
  }

  return (
    <Dialog open={job !== null} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent>
        {done ? (
          <div className="text-center py-6 space-y-3">
            <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto" />
            <DialogTitle>Application received</DialogTitle>
            <p className="text-sm text-muted-foreground">
              Thanks for applying to {job?.title}. Our team will review your profile and be in touch.
            </p>
            <Button onClick={handleClose}>Close</Button>
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Apply — {job?.title}</DialogTitle>
            </DialogHeader>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setError(null);
                mutation.mutate();
              }}
              className="space-y-3"
            >
              {error && <div className="text-sm text-destructive">{error}</div>}
              <div className="space-y-1.5">
                <Label className="text-xs">Full name</Label>
                <Input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Email</Label>
                  <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Phone</Label>
                  <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Résumé (PDF or DOCX)</Label>
                <Input
                  type="file"
                  accept=".pdf,.doc,.docx"
                  onChange={(e) => setResume(e.target.files?.[0] ?? null)}
                />
                <p className="text-[11px] text-muted-foreground">
                  Uploading a résumé lets our AI pre-screen your profile faster.
                </p>
              </div>
              <DialogFooter>
                <Button type="submit" disabled={mutation.isPending || !fullName || !email}>
                  {mutation.isPending ? "Submitting…" : "Submit application"}
                </Button>
              </DialogFooter>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function CareersClient() {
  const { data: org } = useQuery({ queryKey: ["public-org"], queryFn: () => getPublicOrganization() });
  const { data: jobs, isLoading } = useQuery({
    queryKey: ["public-jobs"],
    queryFn: () => listPublicJobs(),
  });
  const [search, setSearch] = useState("");
  const [activeJob, setActiveJob] = useState<PublicJob | null>(null);

  const companyName = org?.name ?? "Peer Consulting Resources Inc.";
  const initial = companyName.charAt(0).toUpperCase();

  const filtered = useMemo(() => {
    const list = jobs ?? [];
    if (!search) return list;
    const q = search.toLowerCase();
    return list.filter(
      (j) =>
        j.title.toLowerCase().includes(q) ||
        (j.department ?? "").toLowerCase().includes(q) ||
        (j.location ?? "").toLowerCase().includes(q),
    );
  }, [jobs, search]);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold">
            <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center text-primary-foreground text-sm font-bold">
              {initial}
            </div>
            {companyName}
          </div>
          <nav className="flex items-center gap-6 text-sm">
            <Link href="/" className="text-muted-foreground hover:text-foreground">
              ATS admin
            </Link>
          </nav>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 py-16 text-center">
        <Badge variant="secondary" className="mb-4">
          {isLoading ? "Loading roles…" : `We're hiring — ${filtered.length} open roles`}
        </Badge>
        <h1 className="text-5xl font-semibold tracking-tight">Build your career with us.</h1>
        <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
          Join {companyName} and work alongside a team shaping the future of consulting.
        </p>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-16">
        <div className="flex gap-3 mb-6">
          <div className="flex-1 relative">
            <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
            <Input
              placeholder="Search roles"
              className="pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        <div className="border rounded-lg divide-y bg-white">
          {isLoading && <div className="p-6 text-center text-sm text-muted-foreground">Loading…</div>}
          {!isLoading && filtered.length === 0 && (
            <div className="p-6 text-center text-sm text-muted-foreground">
              No open roles right now. Check back soon.
            </div>
          )}
          {filtered.map((j) => (
            <div
              key={j.id}
              className="p-5 flex items-center justify-between hover:bg-muted/30 transition-colors"
            >
              <div>
                <div className="font-medium">{j.title}</div>
                <div className="text-sm text-muted-foreground flex items-center gap-4 mt-1 flex-wrap">
                  {j.department && (
                    <span className="flex items-center gap-1">
                      <Building2 className="h-3.5 w-3.5" />
                      {j.department}
                    </span>
                  )}
                  {j.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5" />
                      {j.location}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Briefcase className="h-3.5 w-3.5" />
                    {j.employment_type}
                  </span>
                  <span>{j.workplace}</span>
                </div>
              </div>
              <Button size="sm" onClick={() => setActiveJob(j)}>
                Apply
              </Button>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t py-8 text-center text-xs text-muted-foreground">
        © 2026 {companyName} · Powered by ATS Tracker
      </footer>

      <ApplyDialog job={activeJob} onClose={() => setActiveJob(null)} />
    </div>
  );
}
