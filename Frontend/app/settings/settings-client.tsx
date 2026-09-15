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
import {
  useEmailStatus,
  useOrganizationSettings,
  useUpdateOrganizationSettings,
} from "@/lib/hooks/use-settings";
import { useTemplates } from "@/lib/hooks/use-templates";
import { useStages } from "@/lib/hooks/use-pipeline";
import { useAiConfig } from "@/lib/hooks/use-ai";
import { useQuery } from "@tanstack/react-query";
import { listAuditLogsPage } from "@/lib/api/audit";
import { downloadCsv } from "@/lib/csv";
import { Loader2, Mail, Users } from "lucide-react";

/** A capability that genuinely has no backend yet. Says so plainly instead of
 *  showing controls that don't do anything. */
function NotYetAvailable({ what, why }: { what: string; why: string }) {
  return (
    <div className="rounded-md border border-dashed p-4">
      <div className="text-sm font-medium">{what}</div>
      <p className="mt-1 text-xs text-muted-foreground">{why}</p>
    </div>
  );
}

function WorkflowTab() {
  const { data: template, isLoading } = useStages();

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pipeline stages</CardTitle>
          <p className="text-xs text-muted-foreground">
            The stage sequence every application moves through. Editing the sequence isn&apos;t
            exposed in this version — stage templates are provisioned server-side.
          </p>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-sm text-muted-foreground">Loading…</div>
          ) : !template ? (
            <div className="text-sm text-muted-foreground">No stage template configured.</div>
          ) : (
            <>
              <div className="mb-3 flex items-center gap-2">
                <span className="text-sm font-medium">{template.name}</span>
                {template.is_default && (
                  <Badge variant="secondary" className="text-[10px]">
                    Default
                  </Badge>
                )}
              </div>
              <ol className="space-y-2">
                {[...template.stages]
                  .sort((a, b) => a.sort_order - b.sort_order)
                  .map((stage, i) => (
                    <li
                      key={stage.id}
                      className="flex items-center gap-3 rounded-md border p-3 text-sm"
                    >
                      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-muted text-xs font-medium">
                        {i + 1}
                      </span>
                      <span className="flex-1 font-medium">{stage.name}</span>
                      {stage.terminal_outcome !== "none" && (
                        <Badge variant="secondary" className="text-[10px] capitalize">
                          Terminal · {stage.terminal_outcome}
                        </Badge>
                      )}
                    </li>
                  ))}
              </ol>
            </>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Automation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <NotYetAvailable
            what="Stage-entry automations"
            why="Triggering emails or tasks when an application enters a stage has no backend support yet."
          />
          <NotYetAvailable
            what="Custom stage templates per job"
            why="All jobs share the organization's default stage template in this version."
          />
        </CardContent>
      </Card>
    </div>
  );
}

function AiPreferencesTab() {
  const { data: config, isLoading, error } = useAiConfig();

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Active AI configuration</CardTitle>
          <p className="text-xs text-muted-foreground">
            Read-only. These come from the server environment, so changing them is a deployment
            change rather than a UI setting.
          </p>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-sm text-muted-foreground">Loading…</div>
          ) : error || !config ? (
            <div className="text-sm text-muted-foreground">
              Couldn&apos;t read the AI configuration.
            </div>
          ) : (
            <dl className="grid gap-3 sm:grid-cols-2">
              {[
                { label: "Provider", value: config.provider },
                { label: "Model", value: config.model },
                {
                  label: "Semantic embeddings",
                  value: config.embeddings_enabled
                    ? (config.embeddings_model ?? "enabled")
                    : "Disabled",
                },
                {
                  label: "Skill weight in match score",
                  value: `${Math.round(config.evaluation_skill_weight * 100)}% skills / ${Math.round(
                    (1 - config.evaluation_skill_weight) * 100,
                  )}% semantic`,
                },
              ].map((row) => (
                <div key={row.label} className="rounded-md border p-3">
                  <dt className="text-xs text-muted-foreground">{row.label}</dt>
                  <dd className="mt-0.5 text-sm font-medium break-words">{row.value}</dd>
                </div>
              ))}
            </dl>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Scoring controls</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <NotYetAvailable
            what="Per-organization model selection"
            why="The provider and model are set per deployment, not per organization."
          />
          <NotYetAvailable
            what="Editable scoring weights"
            why="Adjust EVALUATION_SKILL_WEIGHT in the backend environment to change the balance."
          />
        </CardContent>
      </Card>
    </div>
  );
}

const INTEGRATION_CATALOG = [
  { name: "Slack", purpose: "Pipeline and approval notifications" },
  { name: "Zoom / Google Meet", purpose: "Auto-created interview links" },
  { name: "DocuSign", purpose: "Offer letter e-signature" },
  { name: "Calendar sync", purpose: "Two-way interview scheduling" },
  { name: "Job boards", purpose: "Syndicated posting to LinkedIn, Indeed" },
];

function IntegrationsTab() {
  const { data: emailStatus, isLoading } = useEmailStatus();

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Email delivery</CardTitle>
          <p className="text-xs text-muted-foreground">
            Powers password resets, invitations, and candidate outreach sent from templates.
          </p>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-sm text-muted-foreground">Loading…</div>
          ) : !emailStatus ? (
            <div className="text-sm text-muted-foreground">
              Couldn&apos;t read the email configuration.
            </div>
          ) : emailStatus.enabled ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Badge className="text-[10px]" variant="secondary">
                  Connected
                </Badge>
                <span className="text-sm text-muted-foreground">
                  Sending through {emailStatus.smtp_host}
                </span>
              </div>
              <dl className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-md border p-3">
                  <dt className="text-xs text-muted-foreground">From address</dt>
                  <dd className="mt-0.5 text-sm font-medium break-words">
                    {emailStatus.from_name} &lt;{emailStatus.from_email}&gt;
                  </dd>
                </div>
                <div className="rounded-md border p-3">
                  <dt className="text-xs text-muted-foreground">Links point to</dt>
                  <dd className="mt-0.5 text-sm font-medium break-words">
                    {emailStatus.app_base_url}
                  </dd>
                </div>
              </dl>
            </div>
          ) : (
            <div className="space-y-2">
              <Badge variant="outline" className="text-[10px]">
                Not connected
              </Badge>
              <p className="text-xs text-muted-foreground">
                No SMTP host is configured, so nothing is transmitted. Resets and invitations still
                issue valid tokens and candidate messages are still recorded — they just aren&apos;t
                delivered. Set <code>SMTP_HOST</code> (plus credentials and{" "}
                <code>APP_BASE_URL</code>) in the backend environment to turn delivery on.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Other integrations</CardTitle>
          <p className="text-xs text-muted-foreground">None of these are connected yet.</p>
        </CardHeader>
        <CardContent className="p-0">
          <ul className="divide-y">
            {INTEGRATION_CATALOG.map((integration) => (
              <li
                key={integration.name}
                className="flex items-center justify-between gap-3 px-6 py-3"
              >
                <div className="min-w-0">
                  <div className="text-sm font-medium">{integration.name}</div>
                  <div className="text-xs text-muted-foreground">{integration.purpose}</div>
                </div>
                <Badge variant="outline" className="text-[10px] shrink-0">
                  Not connected
                </Badge>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function ComplianceTab() {
  // A page of 1 just to read the true total from X-Total-Count, without
  // pulling the whole trail merely to show a count.
  const { data: countProbe, isLoading } = useQuery({
    queryKey: ["audit-logs", "count-probe"],
    queryFn: () => listAuditLogsPage({ limit: 1 }),
  });
  const totalCount = countProbe?.total ?? 0;
  const [exporting, setExporting] = useState(false);

  async function handleExportAll() {
    setExporting(true);
    try {
      // The audit trail can run well past what one request should return, so
      // the export pages through everything rather than taking the first
      // batch and silently truncating a compliance record.
      const rows = [];
      let offset = 0;
      const pageSize = 200;
      for (;;) {
        const page = await listAuditLogsPage({ limit: pageSize, offset });
        rows.push(...page.data);
        if (rows.length >= page.total || page.data.length < pageSize) break;
        offset += pageSize;
      }
      downloadCsv(
        "audit-log.csv",
        ["created_at", "action", "resource_type", "resource_id", "actor_user_id", "ip_address"],
        rows,
      );
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-3 flex-wrap">
          <div>
            <CardTitle className="text-base">Audit trail</CardTitle>
            <p className="text-xs text-muted-foreground">
              Every privileged action is recorded and retained indefinitely.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href="/admin">Open audit log</Link>
            </Button>
            <Button size="sm" disabled={exporting} onClick={handleExportAll}>
              {exporting ? "Exporting…" : "Export CSV"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-sm">
            {isLoading ? (
              <span className="text-muted-foreground">Loading…</span>
            ) : (
              <>
                <span className="font-medium">{totalCount}</span>{" "}
                <span className="text-muted-foreground">
                  events recorded for this organization.
                </span>
              </>
            )}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Data handling</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="rounded-md border p-3">
            <div className="text-sm font-medium">Candidate deletion</div>
            <p className="mt-1 text-xs text-muted-foreground">
              Candidates are soft-deleted — the record is hidden from all lists but retained in the
              database, so a deletion can be reversed and the audit trail stays intact.
            </p>
          </div>
          <NotYetAvailable
            what="Automatic retention windows"
            why="Purging candidate data after a fixed period isn't implemented; nothing is deleted automatically."
          />
          <NotYetAvailable
            what="Candidate data export / right-to-erasure requests"
            why="GDPR-style subject access and erasure workflows have no backend support yet."
          />
          <NotYetAvailable
            what="EEO / OFCCP reporting"
            why="Demographic data isn't collected, so compliance reporting can't be generated."
          />
        </CardContent>
      </Card>
    </div>
  );
}

export function SettingsClient() {
  const { data: org, isLoading: orgLoading } = useOrganizationSettings();
  const updateOrgMutation = useUpdateOrganizationSettings();
  const { data: templates, isLoading: templatesLoading } = useTemplates();

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
                      {updateOrgMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Save changes"
                      )}
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
                  Managing team members, invitations, and role assignments lives in the Admin
                  console.
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
                <Button size="sm" variant="outline" asChild>
                  <Link href="/templates">
                    <Mail className="h-4 w-4 mr-1.5" />
                    Open template editor
                  </Link>
                </Button>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Full editing — subject, body, merge tokens, duplicate and delete — lives on the
                  Templates page.
                </p>
                {templatesLoading ? (
                  <div className="text-sm text-muted-foreground">Loading…</div>
                ) : (templates ?? []).length === 0 ? (
                  <div className="text-sm text-muted-foreground">No templates yet.</div>
                ) : (
                  <ul className="divide-y rounded-md border">
                    {(templates ?? []).map((t) => (
                      <li key={t.id} className="flex items-center justify-between gap-3 p-3">
                        <div className="min-w-0">
                          <div className="font-medium text-sm truncate">{t.name}</div>
                          <div className="text-xs text-muted-foreground truncate">{t.subject}</div>
                        </div>
                        <Badge variant="outline" className="text-[10px] shrink-0">
                          {t.type}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="workflow" className="mt-0">
            <WorkflowTab />
          </TabsContent>
          <TabsContent value="ai" className="mt-0">
            <AiPreferencesTab />
          </TabsContent>
          <TabsContent value="integrations" className="mt-0">
            <IntegrationsTab />
          </TabsContent>
          <TabsContent value="compliance" className="mt-0">
            <ComplianceTab />
          </TabsContent>
        </div>
      </Tabs>
    </AppShell>
  );
}
