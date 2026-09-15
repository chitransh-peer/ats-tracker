"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useCandidates } from "@/lib/hooks/use-candidates";
import { useJobs } from "@/lib/hooks/use-jobs";
import type { Candidate, Job } from "@/lib/api/types";
import { cn, initialsOf, relativeTime } from "@/lib/utils";
import { Search, Sparkles } from "lucide-react";

type SegmentKey = "all" | "silver" | "passive" | string;

function normalizeSkill(skill: string): string {
  return skill.trim().toLowerCase();
}

/** Candidates whose skills overlap a job's required skills, best overlap first. */
function rediscoveryMatches(
  candidates: Candidate[],
  jobs: Job[],
): { candidate: Candidate; job: Job; matched: string[] }[] {
  const results: { candidate: Candidate; job: Job; matched: string[] }[] = [];

  for (const job of jobs) {
    const required = job.required_skills.map(normalizeSkill).filter(Boolean);
    if (required.length === 0) continue;

    for (const candidate of candidates) {
      const candidateSkills = new Set(candidate.skills.map(normalizeSkill));
      const matched = job.required_skills.filter((s) => candidateSkills.has(normalizeSkill(s)));
      // Half the required skills is a loose-but-useful bar for a re-engagement nudge.
      if (matched.length >= Math.ceil(required.length / 2)) {
        results.push({ candidate, job, matched });
      }
    }
  }

  return results.sort((a, b) => b.matched.length - a.matched.length);
}

export function TalentPoolClient() {
  const { data: pool, isLoading } = useCandidates({ pool: true });
  const { data: openJobs } = useJobs({ status: "Active" });
  const [segment, setSegment] = useState<SegmentKey>("all");
  const [query, setQuery] = useState("");

  // Stable identity so the memos below don't recompute on every render.
  const candidates = useMemo(() => pool ?? [], [pool]);
  const silvers = useMemo(
    () => candidates.filter((c) => c.status === "Silver Medalist"),
    [candidates],
  );
  const passive = useMemo(() => candidates.filter((c) => c.status === "Passive"), [candidates]);

  // Segments beyond the two statuses come from whatever tags recruiters actually use.
  const tagSegments = useMemo(() => {
    const counts = new Map<string, number>();
    for (const c of candidates) {
      for (const tag of c.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
  }, [candidates]);

  const segments: { key: SegmentKey; name: string; count: number; desc: string }[] = [
    {
      key: "all",
      name: "Entire pool",
      count: candidates.length,
      desc: "Everyone not actively in a live process.",
    },
    {
      key: "silver",
      name: "Silver Medalists",
      count: silvers.length,
      desc: "Reached late stages but not selected. Prime for future roles.",
    },
    {
      key: "passive",
      name: "Passive talent",
      count: passive.length,
      desc: "Not actively looking but a strong future fit.",
    },
    ...tagSegments.map(([tag, count]) => ({
      key: tag,
      name: tag,
      count,
      desc: `Tagged "${tag}".`,
    })),
  ];

  const segmentCandidates = useMemo(() => {
    let list = candidates;
    if (segment === "silver") list = silvers;
    else if (segment === "passive") list = passive;
    else if (segment !== "all") list = candidates.filter((c) => c.tags.includes(segment));

    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (c) =>
          c.full_name.toLowerCase().includes(q) ||
          (c.current_title ?? "").toLowerCase().includes(q) ||
          c.skills.some((s) => s.toLowerCase().includes(q)),
      );
    }
    return list;
  }, [candidates, silvers, passive, segment, query]);

  const rediscovery = useMemo(
    () => rediscoveryMatches(candidates, openJobs ?? []).slice(0, 6),
    [candidates, openJobs],
  );

  return (
    <AppShell
      title="Talent Pool"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Talent Pool" }]}
      actions={
        <Button size="sm" variant="outline" asChild>
          <Link href="/candidates">All candidates</Link>
        </Button>
      }
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Pool size" value={candidates.length} />
        <StatCard label="Silver medalists" value={silvers.length} />
        <StatCard label="Passive talent" value={passive.length} />
        <StatCard
          label="Rediscovery matches"
          value={rediscovery.length}
          tone={rediscovery.length > 0 ? "success" : "default"}
          hint="against open jobs"
        />
      </div>

      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4 mb-6">
        {segments.map((s) => (
          <Card
            key={s.key}
            className={cn(
              "cursor-pointer transition-colors",
              segment === s.key ? "border-primary" : "hover:border-muted-foreground/40",
            )}
            onClick={() => setSegment(s.key)}
          >
            <CardContent className="p-5 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="font-medium truncate">{s.name}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{s.desc}</div>
              </div>
              <div className="text-2xl font-semibold shrink-0">{s.count}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between gap-3 flex-wrap pb-2">
          <CardTitle className="text-base">
            {segments.find((s) => s.key === segment)?.name ?? "Pool"}{" "}
            <span className="text-muted-foreground font-normal">({segmentCandidates.length})</span>
          </CardTitle>
          <div className="relative w-full sm:w-64">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search name, title, skill…"
              className="pl-9 h-9"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-6">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : segmentCandidates.length === 0 ? (
            <p className="p-8 text-center text-sm text-muted-foreground">
              {candidates.length === 0
                ? "Nobody in the talent pool yet. Candidates land here when marked Passive or Silver Medalist."
                : "No candidates match this segment and search."}
            </p>
          ) : (
            <ul className="divide-y">
              {segmentCandidates.map((c) => (
                <li key={c.id} className="flex items-center gap-3 px-6 py-3">
                  <Avatar className="h-9 w-9">
                    <AvatarFallback className="text-xs">{initialsOf(c.full_name)}</AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <Link
                      href={`/candidates/${c.id}`}
                      className="text-sm font-medium hover:underline"
                    >
                      {c.full_name}
                    </Link>
                    <div className="text-xs text-muted-foreground truncate">
                      {c.current_title ?? "—"} · {c.current_company ?? "—"} · {c.location ?? "—"}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {c.skills.slice(0, 4).map((s) => (
                        <Badge key={s} variant="secondary" className="text-[10px]">
                          {s}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <Badge variant="secondary" className="text-[10px]">
                      {c.status}
                    </Badge>
                    <div className="text-[10px] text-muted-foreground mt-1">
                      Added {relativeTime(c.created_at)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            Rediscovery — pool candidates matching open jobs
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Matched on required skills. Open the candidate to add them to the job.
          </p>
        </CardHeader>
        <CardContent>
          {rediscovery.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No skill overlap between the pool and your open jobs yet.
            </p>
          ) : (
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
              {rediscovery.map(({ candidate, job, matched }) => (
                <div key={`${candidate.id}-${job.id}`} className="rounded-md border p-3 text-sm">
                  <Link
                    href={`/candidates/${candidate.id}`}
                    className="font-medium hover:underline"
                  >
                    {candidate.full_name}
                  </Link>
                  <div className="text-xs text-muted-foreground">
                    {candidate.current_title ?? "—"} · {candidate.location ?? "—"}
                  </div>
                  <div className="mt-2 text-xs">
                    Fits{" "}
                    <Link href={`/jobs/${job.id}`} className="font-medium hover:underline">
                      {job.title}
                    </Link>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {matched.slice(0, 4).map((s) => (
                      <Badge key={s} variant="secondary" className="text-[10px]">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
