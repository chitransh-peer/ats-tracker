import type { Metadata } from "next";
import { AppShell, StatCard } from "@/components/layout/AppShell";
import { candidates } from "@/lib/mock-data";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export const metadata: Metadata = {
  title: "Talent Pool",
  description: "Saved candidates, silver medalists, and past applicants ready for re-engagement.",
};

export default function TalentPool() {
  const silvers = candidates.filter(
    (c) => c.tags.includes("Silver Medalist") || c.status === "Silver Medalist",
  );
  const passive = candidates.filter((c) => c.status === "Passive");
  const segments = [
    {
      name: "Silver Medalists",
      count: silvers.length,
      desc: "Reached late stages but not selected. Prime for future roles.",
    },
    {
      name: "Passive talent",
      count: passive.length,
      desc: "Not actively looking but a strong future fit.",
    },
    { name: "Boomerangs", count: 4, desc: "Previous employees interested in returning." },
    {
      name: "Referrals archive",
      count: 27,
      desc: "Employee referrals kept warm for the right role.",
    },
  ];

  return (
    <AppShell
      title="Talent Pool"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Talent Pool" }]}
      actions={<Button size="sm">Create segment</Button>}
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Pool size" value={candidates.length + 340} />
        <StatCard label="Silver medalists" value={silvers.length} />
        <StatCard label="Re-engaged this month" value={12} tone="success" />
        <StatCard label="Suggested for open jobs" value={64} />
      </div>
      <div className="grid md:grid-cols-2 gap-4 mb-6">
        {segments.map((s) => (
          <Card key={s.name}>
            <CardContent className="p-5 flex items-center justify-between">
              <div>
                <div className="font-medium">{s.name}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{s.desc}</div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-semibold">{s.count}</div>
                <Button size="sm" variant="outline" className="mt-1">
                  View
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardContent className="p-5">
          <h3 className="font-medium text-sm mb-3">
            Rediscovery — likely fits for currently open jobs
          </h3>
          <div className="grid md:grid-cols-3 gap-2">
            {silvers.slice(0, 6).map((c) => (
              <div key={c.id} className="p-3 rounded-md border text-sm">
                <div className="font-medium">{c.name}</div>
                <div className="text-xs text-muted-foreground">
                  {c.currentTitle} · {c.location}
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {c.skills.slice(0, 3).map((s: string) => (
                    <Badge key={s} variant="secondary" className="text-[10px]">
                      {s}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </AppShell>
  );
}
