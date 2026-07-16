"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateJob } from "@/lib/hooks/use-jobs";
import { ApiError } from "@/lib/api/client";
import { Loader2 } from "lucide-react";

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

function splitCommas(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function NewJobClient() {
  const router = useRouter();
  const createJob = useCreateJob();
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("Engineering");
  const [location, setLocation] = useState("");
  const [workplace, setWorkplace] = useState("Hybrid");
  const [employmentType, setEmploymentType] = useState("Full-time");
  const [openings, setOpenings] = useState(1);
  const [priority, setPriority] = useState("Medium");
  const [payMin, setPayMin] = useState("");
  const [payMax, setPayMax] = useState("");
  const [summary, setSummary] = useState("");
  const [description, setDescription] = useState("");
  const [responsibilities, setResponsibilities] = useState("");
  const [requiredSkills, setRequiredSkills] = useState("");
  const [niceToHave, setNiceToHave] = useState("");
  const [experience, setExperience] = useState("");
  const [education, setEducation] = useState("");
  const [screeningQuestions, setScreeningQuestions] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const job = await createJob.mutateAsync({
        title,
        department: department || null,
        location: location || null,
        workplace,
        employment_type: employmentType,
        openings,
        priority,
        pay_min: payMin ? Number(payMin) : null,
        pay_max: payMax ? Number(payMax) : null,
        summary: summary || null,
        description: description || null,
        responsibilities: splitLines(responsibilities),
        required_skills: splitCommas(requiredSkills),
        nice_to_have: splitCommas(niceToHave),
        screening_questions: splitLines(screeningQuestions),
        experience: experience || null,
        education: education || null,
      });
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create job.");
    }
  }

  return (
    <AppShell
      title="New job requisition"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Jobs", to: "/jobs" }, { label: "New" }]}
    >
      <form onSubmit={handleSubmit} className="max-w-3xl space-y-6">
        {error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        <Card>
          <CardContent className="p-5 space-y-4">
            <h2 className="text-base font-semibold">Basics</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5 col-span-2">
                <Label className="text-xs">Job title</Label>
                <Input
                  placeholder="e.g. Senior React Developer"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Department</Label>
                <Input value={department} onChange={(e) => setDepartment(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Location</Label>
                <Input
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. Remote"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5 space-y-4">
            <h2 className="text-base font-semibold">Classification</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs">Workplace</Label>
                <Select value={workplace} onValueChange={setWorkplace}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Remote">Remote</SelectItem>
                    <SelectItem value="Hybrid">Hybrid</SelectItem>
                    <SelectItem value="Onsite">Onsite</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Employment type</Label>
                <Select value={employmentType} onValueChange={setEmploymentType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Full-time">Full-time</SelectItem>
                    <SelectItem value="Contract">Contract</SelectItem>
                    <SelectItem value="Part-time">Part-time</SelectItem>
                    <SelectItem value="Intern">Intern</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Openings</Label>
                <Input
                  type="number"
                  min={1}
                  value={openings}
                  onChange={(e) => setOpenings(Number(e.target.value))}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Priority</Label>
                <Select value={priority} onValueChange={setPriority}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Low">Low</SelectItem>
                    <SelectItem value="Medium">Medium</SelectItem>
                    <SelectItem value="High">High</SelectItem>
                    <SelectItem value="Urgent">Urgent</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5 space-y-4">
            <h2 className="text-base font-semibold">Compensation</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs">Pay range min (USD)</Label>
                <Input type="number" value={payMin} onChange={(e) => setPayMin(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Pay range max (USD)</Label>
                <Input type="number" value={payMax} onChange={(e) => setPayMax(e.target.value)} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5 space-y-4">
            <h2 className="text-base font-semibold">Description</h2>
            <div className="space-y-1.5">
              <Label className="text-xs">Recruiter summary</Label>
              <Textarea rows={3} value={summary} onChange={(e) => setSummary(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Full description</Label>
              <Textarea
                rows={6}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Responsibilities (one per line)</Label>
              <Textarea
                rows={4}
                value={responsibilities}
                onChange={(e) => setResponsibilities(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5 space-y-4">
            <h2 className="text-base font-semibold">Requirements</h2>
            <div className="space-y-1.5">
              <Label className="text-xs">Required skills (comma separated)</Label>
              <Input value={requiredSkills} onChange={(e) => setRequiredSkills(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Nice-to-have (comma separated)</Label>
              <Input value={niceToHave} onChange={(e) => setNiceToHave(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs">Experience range</Label>
                <Input
                  value={experience}
                  onChange={(e) => setExperience(e.target.value)}
                  placeholder="e.g. 5–8 years"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Education</Label>
                <Input value={education} onChange={(e) => setEducation(e.target.value)} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5 space-y-4">
            <h2 className="text-base font-semibold">Screening questions</h2>
            <Textarea
              rows={4}
              placeholder={"One question per line"}
              value={screeningQuestions}
              onChange={(e) => setScreeningQuestions(e.target.value)}
            />
          </CardContent>
        </Card>

        <div className="flex justify-end gap-2 sticky bottom-2 bg-background/80 backdrop-blur p-3 rounded-lg border">
          <Button type="submit" size="sm" disabled={createJob.isPending}>
            {createJob.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                Creating…
              </>
            ) : (
              "Create job (draft)"
            )}
          </Button>
        </div>
      </form>
    </AppShell>
  );
}
