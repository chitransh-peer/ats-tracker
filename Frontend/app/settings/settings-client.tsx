"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useOrganizationSettings, useUpdateOrganizationSettings } from "@/lib/hooks/use-settings";
import { useTemplates, useCreateTemplate, useUpdateTemplate } from "@/lib/hooks/use-templates";
import { Loader2, Users } from "lucide-react";

function PlaceholderTab({ label }: { label: string }) {
  return (
    <Card>
      <CardContent className="p-8 text-center text-sm text-muted-foreground">
        {label} isn&apos;t built yet — there&apos;s no backend support for it in this version of the app.
      </CardContent>
    </Card>
  );
}

export function SettingsClient() {
  const { data: org, isLoading: orgLoading } = useOrganizationSettings();
  const updateOrgMutation = useUpdateOrganizationSettings();
  const { data: templates, isLoading: templatesLoading } = useTemplates();
  const createTemplateMutation = useCreateTemplate();
  const updateTemplateMutation = useUpdateTemplate();

  const [defaultLocale, setDefaultLocale] = useState("en");
  const [careersEnabled, setCareersEnabled] = useState(true);

  useEffect(() => {
    if (org) {
      setDefaultLocale(org.settings.default_locale);
      setCareersEnabled(org.settings.careers_page_enabled);
    }
  }, [org]);

  return (
    <AppShell title="Settings" breadcrumbs={[{ label: "Home", to: "/" }, { label: "Settings" }]}>
      <Tabs defaultValue="workspace" orientation="vertical" className="flex gap-6">
        <TabsList className="flex-col h-auto bg-transparent p-0 min-w-[180px] items-stretch">
          <TabsTrigger value="workspace" className="justify-start data-[state=active]:bg-muted">
            Workspace
          </TabsTrigger>
          <TabsTrigger value="templates" className="justify-start data-[state=active]:bg-muted">
            Email templates
          </TabsTrigger>
          <TabsTrigger value="workflow" className="justify-start data-[state=active]:bg-muted">
            Workflows
          </TabsTrigger>
          <TabsTrigger value="ai" className="justify-start data-[state=active]:bg-muted">
            AI preferences
          </TabsTrigger>
          <TabsTrigger value="integrations" className="justify-start data-[state=active]:bg-muted">
            Integrations
          </TabsTrigger>
          <TabsTrigger value="compliance" className="justify-start data-[state=active]:bg-muted">
            Compliance
          </TabsTrigger>
        </TabsList>

        <div className="flex-1 min-w-0">
          <TabsContent value="workspace" className="mt-0 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Organization</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {orgLoading || !org ? (
                  <div className="text-sm text-muted-foreground">Loading…</div>
                ) : (
                  <>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div>
                        <Label>Company name</Label>
                        <Input readOnly value={org.name} className="mt-1.5" />
                      </div>
                      <div>
                        <Label>Default locale</Label>
                        <Input
                          value={defaultLocale}
                          onChange={(e) => setDefaultLocale(e.target.value)}
                          className="mt-1.5"
                          placeholder="en"
                        />
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 border rounded-md">
                      <div>
                        <div className="text-sm font-medium">Public careers page enabled</div>
                        <div className="text-xs text-muted-foreground">
                          Controls whether the public /careers job listing is reachable
                        </div>
                      </div>
                      <Switch checked={careersEnabled} onCheckedChange={setCareersEnabled} />
                    </div>
                    <Button
                      size="sm"
                      disabled={updateOrgMutation.isPending}
                      onClick={() =>
                        updateOrgMutation.mutate({
                          default_locale: defaultLocale,
                          careers_page_enabled: careersEnabled,
                        })
                      }
                    >
                      {updateOrgMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save changes"}
                    </Button>
                    {updateOrgMutation.isSuccess && (
                      <span className="ml-2 text-xs text-emerald-700">Saved.</span>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Users & roles</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-3">
                  Managing team members, invitations, and role assignments lives in the Admin console.
                </p>
                <Button variant="outline" size="sm" asChild>
                  <Link href="/admin">
                    <Users className="h-4 w-4 mr-1.5" />
                    Open Admin console
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="templates" className="mt-0">
            <Card>
              <CardHeader className="flex flex-row justify-between items-center">
                <CardTitle className="text-base">Email templates</CardTitle>
                <Button
                  size="sm"
                  disabled={createTemplateMutation.isPending}
                  onClick={() =>
                    createTemplateMutation.mutate({
                      name: "New template",
                      type: "Follow-up",
                      subject: "Subject line",
                      body: "Write your message…",
                    })
                  }
                >
                  New template
                </Button>
              </CardHeader>
              <CardContent className="grid md:grid-cols-2 gap-4">
                {templatesLoading ? (
                  <div className="text-sm text-muted-foreground">Loading…</div>
                ) : (templates ?? []).length === 0 ? (
                  <div className="text-sm text-muted-foreground">No templates yet.</div>
                ) : (
                  (templates ?? []).map((t) => (
                    <div key={t.id} className="border rounded-md p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <Badge variant="outline" className="text-[10px]">
                            {t.type}
                          </Badge>
                          <div className="font-medium mt-1">{t.name}</div>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={updateTemplateMutation.isPending}
                          onClick={() =>
                            updateTemplateMutation.mutate({
                              templateId: t.id,
                              input: { subject: t.subject },
                            })
                          }
                        >
                          Save
                        </Button>
                      </div>
                      <div className="text-xs text-muted-foreground mt-2">Subject: {t.subject}</div>
                      <Textarea readOnly value={t.body} className="mt-2 text-xs min-h-[80px]" />
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="workflow" className="mt-0">
            <PlaceholderTab label="Custom pipeline stage configuration" />
          </TabsContent>
          <TabsContent value="ai" className="mt-0">
            <PlaceholderTab label="AI provider/model configuration via the UI" />
          </TabsContent>
          <TabsContent value="integrations" className="mt-0">
            <PlaceholderTab label="Third-party integrations (Slack, Zoom, DocuSign, etc.)" />
          </TabsContent>
          <TabsContent value="compliance" className="mt-0">
            <PlaceholderTab label="Data retention & compliance policy controls" />
          </TabsContent>
        </div>
      </Tabs>
    </AppShell>
  );
}
