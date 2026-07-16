import type { Metadata } from "next";
import { AppShell } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { templates, type EmailTemplate } from "@/lib/mock-data";
import { CheckCircle2, Link2, Mail, MessagesSquare, Video, FileText, Users } from "lucide-react";

export const metadata: Metadata = {
  title: "Settings",
  description:
    "Configure workflows, users, roles, integrations, email templates, and AI preferences.",
};

export default function Settings() {
  const integrations = [
    { name: "Gmail / Outlook", icon: Mail, connected: true },
    { name: "Google / Outlook Calendar", icon: Video, connected: true },
    { name: "Zoom", icon: Video, connected: true },
    { name: "Microsoft Teams", icon: Video, connected: false },
    { name: "Slack", icon: MessagesSquare, connected: true },
    { name: "LinkedIn Recruiter", icon: Users, connected: false },
    { name: "DocuSign", icon: FileText, connected: true },
    { name: "Workday HRIS", icon: Link2, connected: false },
  ];

  return (
    <AppShell title="Settings" breadcrumbs={[{ label: "Home", to: "/" }, { label: "Settings" }]}>
      <Tabs defaultValue="workspace" orientation="vertical" className="flex gap-6">
        <TabsList className="flex-col h-auto bg-transparent p-0 min-w-[180px] items-stretch">
          <TabsTrigger value="workspace" className="justify-start data-[state=active]:bg-muted">
            Workspace
          </TabsTrigger>
          <TabsTrigger value="users" className="justify-start data-[state=active]:bg-muted">
            Users & roles
          </TabsTrigger>
          <TabsTrigger value="workflow" className="justify-start data-[state=active]:bg-muted">
            Workflows
          </TabsTrigger>
          <TabsTrigger value="ai" className="justify-start data-[state=active]:bg-muted">
            AI preferences
          </TabsTrigger>
          <TabsTrigger value="templates" className="justify-start data-[state=active]:bg-muted">
            Email templates
          </TabsTrigger>
          <TabsTrigger value="integrations" className="justify-start data-[state=active]:bg-muted">
            Integrations
          </TabsTrigger>
          <TabsTrigger value="careers" className="justify-start data-[state=active]:bg-muted">
            Careers page
          </TabsTrigger>
          <TabsTrigger value="compliance" className="justify-start data-[state=active]:bg-muted">
            Compliance
          </TabsTrigger>
        </TabsList>

        <div className="flex-1 min-w-0">
          <TabsContent value="workspace" className="mt-0 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Company profile</CardTitle>
              </CardHeader>
              <CardContent className="grid md:grid-cols-2 gap-4">
                <div>
                  <Label>Company name</Label>
                  <Input defaultValue="Acme Technologies" className="mt-1.5" />
                </div>
                <div>
                  <Label>Website</Label>
                  <Input defaultValue="acme.com" className="mt-1.5" />
                </div>
                <div>
                  <Label>Primary timezone</Label>
                  <Select defaultValue="ist">
                    <SelectTrigger className="mt-1.5">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ist">Asia/Kolkata (IST)</SelectItem>
                      <SelectItem value="pst">America/Los_Angeles</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Currency</Label>
                  <Select defaultValue="usd">
                    <SelectTrigger className="mt-1.5">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="usd">USD</SelectItem>
                      <SelectItem value="inr">INR</SelectItem>
                      <SelectItem value="eur">EUR</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="users" className="mt-0">
            <Card>
              <CardHeader className="flex flex-row justify-between items-center">
                <CardTitle className="text-base">Team members</CardTitle>
                <Button size="sm">Invite user</Button>
              </CardHeader>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="p-3 text-left">User</th>
                      <th className="p-3 text-left">Email</th>
                      <th className="p-3 text-left">Role</th>
                      <th className="p-3 text-left">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {[
                      ["Priya Sharma", "priya@acme.com", "Recruiter", "Active"],
                      ["Marcus Chen", "marcus@acme.com", "Hiring Manager", "Active"],
                      ["Elena Rodriguez", "elena@acme.com", "Recruiter", "Active"],
                      ["Sarah Kim", "sarah@acme.com", "Admin", "Active"],
                      ["David Lee", "david@acme.com", "Executive", "Active"],
                    ].map((r) => (
                      <tr key={r[1]} className="hover:bg-muted/30">
                        <td className="p-3">{r[0]}</td>
                        <td className="p-3 text-xs">{r[1]}</td>
                        <td className="p-3">
                          <Badge variant="outline">{r[2]}</Badge>
                        </td>
                        <td className="p-3">
                          <Badge className="bg-emerald-100 text-emerald-800">{r[3]}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="workflow" className="mt-0">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Default pipeline stages</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {[
                  "Applied",
                  "AI Screening",
                  "Recruiter Screen",
                  "HM Review",
                  "Technical Interview",
                  "Panel Interview",
                  "Offer",
                  "Background Check",
                  "Hired",
                  "Onboarded",
                ].map((s, i) => (
                  <div key={s} className="flex items-center gap-3 p-2.5 border rounded-md">
                    <span className="w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
                      {i + 1}
                    </span>
                    <span className="flex-1 text-sm">{s}</span>
                    <Switch defaultChecked />
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="ai" className="mt-0 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">AI features</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  ["Auto-parse resumes", "Extract structured data on upload"],
                  ["Auto-score candidates", "Rank against active jobs"],
                  ["Suggest interview questions", "Based on gaps"],
                  ["Bias detection in JDs", "Flag exclusionary language"],
                  ["Rediscover past applicants", "Surface silver medalists"],
                ].map(([t, d]) => (
                  <div key={t} className="flex items-center justify-between p-3 border rounded-md">
                    <div>
                      <div className="text-sm font-medium">{t}</div>
                      <div className="text-xs text-muted-foreground">{d}</div>
                    </div>
                    <Switch defaultChecked />
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Match score weights</CardTitle>
              </CardHeader>
              <CardContent className="grid md:grid-cols-2 gap-3">
                {[
                  ["Skills", 30],
                  ["Experience", 25],
                  ["Education", 10],
                  ["Certifications", 5],
                  ["Location", 10],
                  ["Domain", 10],
                  ["Language", 5],
                  ["Notice period", 5],
                ].map(([k, v]) => (
                  <div key={k as string}>
                    <Label className="text-xs">
                      {k}: {v}%
                    </Label>
                    <input type="range" defaultValue={v as number} className="w-full mt-1" />
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="templates" className="mt-0">
            <Card>
              <CardHeader className="flex flex-row justify-between items-center">
                <CardTitle className="text-base">Email templates</CardTitle>
                <Button size="sm">New template</Button>
              </CardHeader>
              <CardContent className="grid md:grid-cols-2 gap-4">
                {templates.map((t: EmailTemplate) => (
                  <div key={t.id} className="border rounded-md p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <Badge variant="outline" className="text-[10px]">
                          {t.type}
                        </Badge>
                        <div className="font-medium mt-1">{t.name}</div>
                      </div>
                      <Button size="sm" variant="ghost">
                        Edit
                      </Button>
                    </div>
                    <div className="text-xs text-muted-foreground mt-2">Subject: {t.subject}</div>
                    <Textarea readOnly value={t.body} className="mt-2 text-xs min-h-[80px]" />
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="integrations" className="mt-0 grid md:grid-cols-2 gap-3">
            {integrations.map((i) => (
              <Card key={i.name}>
                <CardContent className="p-4 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-md bg-muted flex items-center justify-center">
                    <i.icon className="h-5 w-5" />
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-sm">{i.name}</div>
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      {i.connected ? (
                        <>
                          <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                          Connected
                        </>
                      ) : (
                        "Not connected"
                      )}
                    </div>
                  </div>
                  <Button size="sm" variant={i.connected ? "outline" : "default"}>
                    {i.connected ? "Manage" : "Connect"}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="careers" className="mt-0">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Public careers page</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>Page URL</Label>
                  <Input readOnly value="https://careers.acme.com" className="mt-1.5" />
                </div>
                <div>
                  <Label>Headline</Label>
                  <Input defaultValue="Build the future with us." className="mt-1.5" />
                </div>
                <div>
                  <Label>About</Label>
                  <Textarea
                    defaultValue="We're a global team building enterprise software loved by teams everywhere."
                    className="mt-1.5"
                  />
                </div>
                <div className="flex items-center justify-between p-3 border rounded-md">
                  <div>
                    <div className="text-sm font-medium">Publish careers site</div>
                    <div className="text-xs text-muted-foreground">
                      Automatically list open positions
                    </div>
                  </div>
                  <Switch defaultChecked />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="compliance" className="mt-0 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Data retention & compliance</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  ["GDPR consent capture", "EU applicants"],
                  ["EEOC data collection", "US applicants — voluntary"],
                  ["Delete candidate data after", "24 months of inactivity"],
                  ["Audit log retention", "7 years"],
                ].map(([t, d]) => (
                  <div key={t} className="flex items-center justify-between p-3 border rounded-md">
                    <div>
                      <div className="text-sm font-medium">{t}</div>
                      <div className="text-xs text-muted-foreground">{d}</div>
                    </div>
                    <Switch defaultChecked />
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>
        </div>
      </Tabs>
    </AppShell>
  );
}
