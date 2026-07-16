"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { templates, type EmailTemplate } from "@/lib/mock-data";
import { Plus, Search, Mail, Copy, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

const typeTone: Record<EmailTemplate["type"], string> = {
  Acknowledgment: "bg-slate-100 text-slate-700 border-slate-200",
  "Interview Invite": "bg-violet-50 text-violet-700 border-violet-200",
  Offer: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Rejection: "bg-red-50 text-red-700 border-red-200",
  "Follow-up": "bg-blue-50 text-blue-700 border-blue-200",
};

export function TemplatesClient() {
  const [selectedId, setSelectedId] = useState(templates[0].id);
  const selected = templates.find((t) => t.id === selectedId)!;

  return (
    <AppShell
      title="Email Templates"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Templates" }]}
      actions={
        <Button size="sm" className="gap-1">
          <Plus className="h-4 w-4" />
          New template
        </Button>
      }
    >
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        <Card className="h-fit">
          <CardHeader className="pb-2">
            <div className="relative">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="Search templates…" className="pl-9 h-9" />
            </div>
          </CardHeader>
          <CardContent className="p-2">
            <ul className="space-y-1">
              {templates.map((t) => (
                <li key={t.id}>
                  <button
                    onClick={() => setSelectedId(t.id)}
                    className={cn(
                      "w-full text-left px-3 py-2 rounded-md text-sm transition-colors",
                      selectedId === t.id ? "bg-muted" : "hover:bg-muted/60",
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium truncate">{t.name}</span>
                    </div>
                    <div className="mt-1 flex items-center justify-between gap-2">
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium",
                          typeTone[t.type],
                        )}
                      >
                        {t.type}
                      </span>
                      <span className="text-[10px] text-muted-foreground">{t.updated}</span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3 flex-wrap">
            <div>
              <CardTitle className="text-base">{selected.name}</CardTitle>
              <div className="mt-1 flex items-center gap-2">
                <Badge variant="secondary" className={cn("text-[10px]", typeTone[selected.type])}>
                  {selected.type}
                </Badge>
                <span className="text-xs text-muted-foreground">Updated {selected.updated}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="gap-1">
                <Copy className="h-4 w-4" />
                Duplicate
              </Button>
              <Button variant="outline" size="sm" className="gap-1 text-destructive">
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
              <Button size="sm">Save changes</Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Subject</Label>
              <Input defaultValue={selected.subject} key={selected.id + "-s"} className="mt-1.5" />
            </div>
            <div>
              <Label>Body</Label>
              <Textarea
                defaultValue={selected.body}
                key={selected.id + "-b"}
                className="mt-1.5 min-h-[260px] font-mono text-sm"
              />
            </div>
            <div className="rounded-md border border-border bg-muted/30 p-3 text-xs">
              <div className="font-medium mb-2 text-foreground">Available tokens</div>
              <div className="flex flex-wrap gap-1.5">
                {[
                  "{{candidate_first_name}}",
                  "{{candidate_full_name}}",
                  "{{job_title}}",
                  "{{company}}",
                  "{{recruiter_name}}",
                  "{{interview_time}}",
                  "{{offer_link}}",
                ].map((t) => (
                  <code
                    key={t}
                    className="rounded bg-background border border-border px-1.5 py-0.5"
                  >
                    {t}
                  </code>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
