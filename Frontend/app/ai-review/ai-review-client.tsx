"use client";

import { AppShell, StatCard, ScorePill } from "@/components/layout/AppShell";
import { candidates, jobs } from "@/lib/mock-data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Sparkles, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

export function AIReviewClient() {
  const job = jobs[3];
  const cand = [...candidates].sort((a, b) => b.aiScore - a.aiScore)[0];
  const donut = [
    { name: "Matched", value: 68 },
    { name: "Partial", value: 18 },
    { name: "Missing", value: 14 },
  ];
  const colors = ["#10b981", "#f59e0b", "#ef4444"];

  const criteria = [
    {
      type: "Skill",
      req: "React",
      weight: 20,
      resume: "8y React",
      status: "Matched",
      score: 20,
      remark: "Strong match",
    },
    {
      type: "Skill",
      req: "TypeScript",
      weight: 15,
      resume: "6y TS",
      status: "Matched",
      score: 15,
      remark: "Strong match",
    },
    {
      type: "Skill",
      req: "GraphQL",
      weight: 10,
      resume: "Apollo Client",
      status: "Partial",
      score: 6,
      remark: "Client only",
    },
    {
      type: "Experience",
      req: "5+ yrs frontend",
      weight: 15,
      resume: "8 yrs",
      status: "Matched",
      score: 15,
      remark: "Exceeds",
    },
    {
      type: "Qualification",
      req: "B.S. CS",
      weight: 8,
      resume: "B.S. Computer Science",
      status: "Matched",
      score: 8,
      remark: "Match",
    },
    {
      type: "Certification",
      req: "AWS Cert.",
      weight: 6,
      resume: "—",
      status: "Missing",
      score: 0,
      remark: "Not present",
    },
    {
      type: "Domain",
      req: "SaaS / B2B",
      weight: 10,
      resume: "SaaS at Meta",
      status: "Matched",
      score: 10,
      remark: "Match",
    },
    {
      type: "Location",
      req: "Bengaluru",
      weight: 6,
      resume: "Bengaluru, IN",
      status: "Matched",
      score: 6,
      remark: "Same city",
    },
    {
      type: "Language",
      req: "English fluent",
      weight: 5,
      resume: "English, Hindi",
      status: "Matched",
      score: 5,
      remark: "Fluent",
    },
    {
      type: "Notice",
      req: "≤60 days",
      weight: 5,
      resume: "60 days",
      status: "Partial",
      score: 3,
      remark: "At limit",
    },
  ];

  const total = criteria.reduce((a, c) => a + c.score, 0);

  const statusChip = (s: string) =>
    s === "Matched"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : s === "Partial"
        ? "bg-amber-50 text-amber-700 border-amber-200"
        : "bg-red-50 text-red-700 border-red-200";

  return (
    <AppShell
      title="AI Resume Review"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "AI Review" }]}
      actions={
        <>
          <Select defaultValue={cand.id}>
            <SelectTrigger className="h-9 w-[220px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {candidates.slice(0, 10).map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select defaultValue={job.id}>
            <SelectTrigger className="h-9 w-[220px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {jobs.map((j) => (
                <SelectItem key={j.id} value={j.id}>
                  {j.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button size="sm">Re-run analysis</Button>
        </>
      }
    >
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <StatCard label="Overall match" value={`${total}%`} tone="success" />
        <StatCard label="Matched criteria" value="6/10" tone="success" />
        <StatCard label="Partial" value="3/10" tone="warning" />
        <StatCard label="Missing" value="1/10" tone="destructive" />
        <StatCard label="Confidence" value="94%" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-6">
        <Card className="xl:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-primary" />
              AI recommendation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="text-4xl font-semibold">
                {total}
                <span className="text-sm text-muted-foreground">/100</span>
              </div>
              <div className="flex-1">
                <Progress value={total} className="h-2" />
                <div className="text-xs text-muted-foreground mt-1">
                  Recommendation:{" "}
                  <span className="font-semibold text-[color:var(--color-success)]">
                    Proceed to interview
                  </span>
                </div>
              </div>
              <ScorePill score={total} />
            </div>
            <p className="text-sm text-muted-foreground">
              Candidate demonstrates strong React/TypeScript expertise with proven track record
              building large-scale SaaS applications. Minor gaps in AWS certification and GraphQL
              server experience; the recruiter should probe on system design and cloud fundamentals
              during interview.
            </p>
            <div className="grid md:grid-cols-3 gap-3">
              <div className="p-3 rounded-md border">
                <div className="text-xs font-semibold text-[color:var(--color-success)] mb-1 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  Top strengths
                </div>
                <ul className="text-xs list-disc pl-4 space-y-0.5">
                  <li>8y React at scale</li>
                  <li>Design systems ownership</li>
                  <li>Frontend performance focus</li>
                </ul>
              </div>
              <div className="p-3 rounded-md border">
                <div className="text-xs font-semibold text-amber-700 mb-1 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Gaps
                </div>
                <ul className="text-xs list-disc pl-4 space-y-0.5">
                  <li>No AWS certification</li>
                  <li>Limited GraphQL server work</li>
                  <li>60d notice period</li>
                </ul>
              </div>
              <div className="p-3 rounded-md border">
                <div className="text-xs font-semibold text-destructive mb-1 flex items-center gap-1">
                  <XCircle className="h-3 w-3" />
                  Risks
                </div>
                <ul className="text-xs list-disc pl-4 space-y-0.5">
                  <li>Compensation above band</li>
                  <li>1 short tenure (11 mo)</li>
                  <li>No management experience</li>
                </ul>
              </div>
            </div>
            <div className="p-3 rounded-md bg-muted/50">
              <div className="text-xs font-semibold mb-1">Suggested interview questions</div>
              <ul className="text-xs list-disc pl-4 space-y-0.5">
                <li>Walk through the architecture of a recent React app you led.</li>
                <li>How would you approach migrating a legacy REST integration to GraphQL?</li>
                <li>Describe a design system decision you regret and what you learned.</li>
              </ul>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Match visualization</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={donut} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80}>
                  {donut.map((_, i) => (
                    <Cell key={i} fill={colors[i]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex justify-around text-xs mt-2">
              {donut.map((d, i) => (
                <div key={d.name} className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full" style={{ background: colors[i] }} />
                  {d.name}: {d.value}%
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="comparison">
        <TabsList>
          <TabsTrigger value="comparison">JD vs Resume</TabsTrigger>
          <TabsTrigger value="parsed">Parsed resume</TabsTrigger>
          <TabsTrigger value="capabilities">AI capabilities</TabsTrigger>
        </TabsList>

        <TabsContent value="comparison" className="mt-4 space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Job requirements — {job.title}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <div>
                  <span className="text-muted-foreground text-xs">Must-have skills</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {job.requiredSkills.map((s: string) => (
                      <Badge key={s} variant="secondary">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Experience</span>
                  <div className="font-medium">{job.experience}</div>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Education</span>
                  <div className="font-medium">{job.education}</div>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Location</span>
                  <div className="font-medium">
                    {job.location} · {job.workplace}
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Candidate data — {cand.name}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <div>
                  <span className="text-muted-foreground text-xs">Skills</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {cand.skills.map((s: string) => (
                      <Badge key={s} variant="outline">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Experience</span>
                  <div className="font-medium">
                    {cand.totalExperience}y total, {cand.relevantExperience}y relevant
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Education</span>
                  <div className="font-medium">{cand.education[0].degree}</div>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Location</span>
                  <div className="font-medium">{cand.location}</div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Weighted comparison</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="p-3 text-left">Type</th>
                    <th className="p-3 text-left">Requirement</th>
                    <th className="p-3 text-right">Weight</th>
                    <th className="p-3 text-left">Resume</th>
                    <th className="p-3 text-left">Status</th>
                    <th className="p-3 text-right">Score</th>
                    <th className="p-3 text-left">Remarks</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {criteria.map((c, i) => (
                    <tr key={i} className="hover:bg-muted/30">
                      <td className="p-3 text-xs">
                        <Badge variant="outline" className="text-[10px]">
                          {c.type}
                        </Badge>
                      </td>
                      <td className="p-3">{c.req}</td>
                      <td className="p-3 text-right text-xs">{c.weight}</td>
                      <td className="p-3 text-xs text-muted-foreground">{c.resume}</td>
                      <td className="p-3">
                        <span
                          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${statusChip(c.status)}`}
                        >
                          {c.status}
                        </span>
                      </td>
                      <td className="p-3 text-right font-medium">{c.score}</td>
                      <td className="p-3 text-xs text-muted-foreground">{c.remark}</td>
                    </tr>
                  ))}
                  <tr className="bg-muted/30 font-semibold">
                    <td className="p-3" colSpan={5}>
                      Total match score
                    </td>
                    <td className="p-3 text-right">{total}</td>
                    <td />
                  </tr>
                </tbody>
              </table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="parsed" className="mt-4 grid md:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Personal</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-1">
              <div>
                <span className="text-muted-foreground">Name:</span> {cand.name}
              </div>
              <div>
                <span className="text-muted-foreground">Email:</span> {cand.email}
              </div>
              <div>
                <span className="text-muted-foreground">Phone:</span> {cand.phone}
              </div>
              <div>
                <span className="text-muted-foreground">Location:</span> {cand.location}
              </div>
              <div>
                <span className="text-muted-foreground">LinkedIn:</span> {cand.linkedin}
              </div>
              <div>
                <span className="text-muted-foreground">Notice:</span> {cand.noticePeriod}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Professional</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-1">
              <div>
                <span className="text-muted-foreground">Title:</span> {cand.currentTitle}
              </div>
              <div>
                <span className="text-muted-foreground">Company:</span> {cand.currentCompany}
              </div>
              <div>
                <span className="text-muted-foreground">Total exp:</span> {cand.totalExperience}y
              </div>
              <div>
                <span className="text-muted-foreground">Relevant exp:</span>{" "}
                {cand.relevantExperience}y
              </div>
              <div>
                <span className="text-muted-foreground">Work auth:</span> {cand.workAuth}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Skills & tools</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-1">
              {cand.skills.map((s: string) => (
                <Badge key={s} variant="secondary">
                  {s}
                </Badge>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Resume metadata</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-1">
              <div>
                <span className="text-muted-foreground">File:</span> resume_
                {cand.name.replace(/ /g, "_").toLowerCase()}.pdf
              </div>
              <div>
                <span className="text-muted-foreground">Pages:</span> 2
              </div>
              <div>
                <span className="text-muted-foreground">Uploaded:</span> 2026-07-05
              </div>
              <div>
                <span className="text-muted-foreground">Parsing confidence:</span> 94%
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="capabilities" className="mt-4 grid md:grid-cols-3 gap-3">
          {[
            ["Resume parsing", "Extract structured data from PDF/DOCX with 90%+ confidence."],
            ["Resume scoring", "Score candidates against a job with weighted criteria."],
            ["JD analyzer", "Detect ambiguities, bias language, and missing must-haves."],
            ["JD vs Resume", "Side-by-side matching with match/partial/missing chips."],
            ["Interview assistant", "Suggest questions and probe areas based on gaps."],
            ["Candidate rediscovery", "Auto-surface relevant past applicants from talent pool."],
          ].map(([t, d]) => (
            <Card key={t}>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  {t}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">{d}</CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
