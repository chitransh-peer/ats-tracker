"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { useCandidates, useCreateCandidate } from "@/lib/hooks/use-candidates";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Search } from "lucide-react";
import { initialsOf } from "@/lib/utils";
import { ApiError } from "@/lib/api/client";

function AddCandidateDialog() {
  const [open, setOpen] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [currentTitle, setCurrentTitle] = useState("");
  const [currentCompany, setCurrentCompany] = useState("");
  const [skills, setSkills] = useState("");
  const [error, setError] = useState<string | null>(null);
  const createCandidate = useCreateCandidate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createCandidate.mutateAsync({
        full_name: fullName,
        email,
        phone: phone || null,
        current_title: currentTitle || null,
        current_company: currentCompany || null,
        skills: skills
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setOpen(false);
      setFullName("");
      setEmail("");
      setPhone("");
      setCurrentTitle("");
      setCurrentCompany("");
      setSkills("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add candidate.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">Add candidate</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add candidate</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="space-y-1.5">
            <Label className="text-xs">Full name</Label>
            <Input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Email</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Phone</Label>
              <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Current title</Label>
              <Input value={currentTitle} onChange={(e) => setCurrentTitle(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Current company</Label>
            <Input value={currentCompany} onChange={(e) => setCurrentCompany(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Skills (comma separated)</Label>
            <Input value={skills} onChange={(e) => setSkills(e.target.value)} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createCandidate.isPending}>
              {createCandidate.isPending ? "Adding…" : "Add candidate"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function CandidatesClient() {
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");
  const { data: candidates, isLoading } = useCandidates({
    status: status !== "all" ? status : undefined,
    search: search || undefined,
  });

  const silverMedalists = candidates?.filter((c) => c.tags.includes("Silver Medalist")).length ?? 0;

  return (
    <AppShell
      title="Candidates"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Candidates" }]}
      actions={<AddCandidateDialog />}
    >
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <StatCard label="Total candidates" value={candidates?.length ?? 0} />
        <StatCard
          label="Active pipeline"
          value={candidates?.filter((c) => c.status === "Active").length ?? 0}
          tone="success"
        />
        <StatCard label="Silver medalists" value={silverMedalists} />
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="flex flex-wrap items-center gap-2 p-4 border-b">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by name or email…"
                className="pl-9 h-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="h-9 w-[160px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="Active">Active</SelectItem>
                <SelectItem value="Passive">Passive</SelectItem>
                <SelectItem value="Silver Medalist">Silver Medalist</SelectItem>
                <SelectItem value="Do Not Contact">Do Not Contact</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="p-3 text-left font-medium">Candidate</th>
                  <th className="p-3 text-left font-medium">Current</th>
                  <th className="p-3 text-left font-medium">Location</th>
                  <th className="p-3 text-left font-medium">Skills</th>
                  <th className="p-3 text-left font-medium">Status</th>
                  <th className="p-3 text-left font-medium">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {isLoading && (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-sm text-muted-foreground">
                      Loading candidates…
                    </td>
                  </tr>
                )}
                {!isLoading && (candidates?.length ?? 0) === 0 && (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-sm text-muted-foreground">
                      No candidates yet.
                    </td>
                  </tr>
                )}
                {candidates?.map((c) => (
                  <tr key={c.id} className="hover:bg-muted/30">
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback className="text-xs">
                            {initialsOf(c.full_name)}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <Link
                            href={`/candidates/${c.id}`}
                            className="font-medium hover:underline"
                          >
                            {c.full_name}
                          </Link>
                          <div className="text-[11px] text-muted-foreground">{c.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-xs">
                      <div className="font-medium">{c.current_title ?? "—"}</div>
                      <div className="text-muted-foreground">
                        {c.current_company ?? "—"}
                        {c.total_experience_years ? ` · ${c.total_experience_years}y` : ""}
                      </div>
                    </td>
                    <td className="p-3 text-xs text-muted-foreground">{c.location ?? "—"}</td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-1 max-w-[220px]">
                        {c.skills.slice(0, 3).map((s) => (
                          <Badge key={s} variant="secondary" className="text-[10px]">
                            {s}
                          </Badge>
                        ))}
                        {c.skills.length > 3 && (
                          <Badge variant="outline" className="text-[10px]">
                            +{c.skills.length - 3}
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      <Badge variant="secondary" className="text-[10px]">
                        {c.status}
                      </Badge>
                    </td>
                    <td className="p-3 text-xs text-muted-foreground">{c.source ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </AppShell>
  );
}
