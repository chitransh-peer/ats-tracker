"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileUp,
  Loader2,
  RotateCcw,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError } from "@/lib/api/client";
import {
  checkImport,
  downloadExport,
  downloadRejectedRows,
  getImportCatalog,
  listImports,
  processImportChunk,
  undoImport,
  uploadImport,
  type CheckResult,
  type ImportEntity,
  type ImportJob,
  type ImportPreset,
} from "@/lib/api/imports";
import { useAuth } from "@/lib/auth/auth-context";

const SKIP = "__skip__";

/** React Query keys whose data an import of each kind changes. */
const AFFECTED_QUERIES: Record<ImportEntity, string[]> = {
  candidates: ["candidates"],
  vendors: ["vendors"],
  clients: ["clients"],
  jobs: ["jobs"],
  bench: ["talent-bench", "candidates"],
};

/** Import and export are for Admins and Super Admins only, as on the server.
 * A Super Admin previewing another role sees what that role would. */
export function useCanImport(): boolean {
  const { user, viewAsRole } = useAuth();
  const roles = viewAsRole ? [viewAsRole] : (user?.roles ?? []);
  return roles.includes("admin") || roles.includes("super_admin");
}

function errorText(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    const detail = error.detail as { detail?: unknown } | null;
    if (detail && typeof detail.detail === "string") return detail.detail;
    return error.message;
  }
  return fallback;
}

type Step = "upload" | "map" | "review" | "importing" | "done";

export function ImportExportButtons({ entity, label }: { entity: ImportEntity; label: string }) {
  const canImport = useCanImport();
  const [open, setOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  if (!canImport) return null;

  async function runExport(format: "csv" | "json") {
    setExporting(true);
    try {
      await downloadExport(entity, format);
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-1" disabled={exporting}>
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Export
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={() => void runExport("csv")}>
            All {label.toLowerCase()} as CSV
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => void runExport("json")}>
            All {label.toLowerCase()} as JSON
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <Button variant="outline" size="sm" className="gap-1" onClick={() => setOpen(true)}>
        <Upload className="h-4 w-4" />
        Import
      </Button>
      {open && <ImportDialog entity={entity} label={label} onClose={() => setOpen(false)} />}
    </>
  );
}

function ImportDialog({
  entity,
  label,
  onClose,
}: {
  entity: ImportEntity;
  label: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const { data: catalog } = useQuery({
    queryKey: ["imports", "catalog"],
    queryFn: getImportCatalog,
  });
  const { data: history, refetch: refetchHistory } = useQuery({
    queryKey: ["imports", entity],
    queryFn: () => listImports(entity),
  });
  const fields = useMemo(
    () => catalog?.entities.find((e) => e.key === entity)?.fields ?? [],
    [catalog, entity],
  );

  const [step, setStep] = useState<Step>("upload");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<ImportJob | null>(null);
  const [sample, setSample] = useState<Record<string, string>[]>([]);
  const [presets, setPresets] = useState<ImportPreset[]>([]);
  const [mapping, setMapping] = useState<Record<string, string | null>>({});
  const [duplicateMode, setDuplicateMode] = useState<"skip" | "update">("skip");
  const [presetName, setPresetName] = useState("");
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [confirmUndo, setConfirmUndo] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const paused = useRef(false);

  function refreshAffected() {
    for (const key of AFFECTED_QUERIES[entity]) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
    void refetchHistory();
  }

  async function handleFile(file: File) {
    setError(null);
    setBusy(true);
    try {
      const result = await uploadImport(entity, file);
      setJob(result.job);
      setSample(result.sample);
      setPresets(result.presets);
      setMapping(result.job.mapping);
      setStep("map");
    } catch (err) {
      setError(errorText(err, "The file could not be uploaded."));
    } finally {
      setBusy(false);
    }
  }

  async function handleCheck() {
    if (!job) return;
    setError(null);
    setBusy(true);
    try {
      const result = await checkImport(job.id, {
        mapping,
        duplicate_mode: duplicateMode,
        save_preset_as: presetName.trim() || null,
      });
      setCheck(result);
      setJob(result.job);
      setStep("review");
    } catch (err) {
      setError(errorText(err, "The file could not be checked."));
    } finally {
      setBusy(false);
    }
  }

  async function runImport(current: ImportJob) {
    setError(null);
    setStep("importing");
    paused.current = false;
    setIsPaused(false);
    let latest = current;
    try {
      while (latest.status !== "completed" && !paused.current) {
        latest = await processImportChunk(latest.id);
        setJob(latest);
      }
      if (latest.status === "completed") {
        setStep("done");
        refreshAffected();
      } else {
        setIsPaused(true);
      }
    } catch (err) {
      setError(
        errorText(err, "The import stopped.") +
          " Nothing already imported is lost — press Resume to carry on.",
      );
    }
  }

  async function handleUndo() {
    if (!job) return;
    setBusy(true);
    setError(null);
    try {
      let result = await undoImport(job.id);
      while (result.status === "undoing") {
        setJob(result);
        result = await undoImport(job.id);
      }
      setJob(result);
      setConfirmUndo(false);
      refreshAffected();
    } catch (err) {
      setError(errorText(err, "The import could not be undone."));
    } finally {
      setBusy(false);
    }
  }

  function openPastImport(past: ImportJob) {
    setJob(past);
    setError(null);
    if (past.status === "importing") {
      void runImport(past);
    } else if (["completed", "undoing", "undone"].includes(past.status)) {
      setStep("done");
      if (past.status === "undoing") setConfirmUndo(true);
    }
  }

  // Leaving mid-import pauses it; it can be resumed from "Recent imports".
  useEffect(() => {
    return () => {
      paused.current = true;
    };
  }, []);

  const requiredMissing = fields
    .filter((f) => f.required)
    .filter((f) => !Object.values(mapping).includes(f.key));
  const progress = job?.total_rows ? Math.round((job.processed_rows / job.total_rows) * 100) : 0;

  return (
    <Dialog open onOpenChange={(next) => !next && !busy && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Import {label.toLowerCase()}</DialogTitle>
          <DialogDescription>
            {step === "upload" &&
              "Upload a CSV, Excel or JSON file. Nothing is saved until you confirm."}
            {step === "map" &&
              "Match each column in your file to a field. Columns set to “Don't import” are ignored."}
            {step === "review" && "Every row has been checked. Nothing has been saved yet."}
            {step === "importing" && "Importing in batches of 1,000 rows. Keep this window open."}
            {step === "done" && job?.file_name}
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="flex gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {step === "upload" && (
          <div className="space-y-5">
            <label className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-10 text-center cursor-pointer hover:bg-muted/40">
              {busy ? (
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              ) : (
                <FileUp className="h-8 w-8 text-muted-foreground" />
              )}
              <span className="text-sm font-medium">
                {busy ? "Reading the file…" : "Choose a file to upload"}
              </span>
              <span className="text-xs text-muted-foreground">
                {catalog
                  ? `${catalog.limits.extensions.join(", ")} · up to ${catalog.limits.max_file_mb} MB and ${catalog.limits.max_rows.toLocaleString()} rows`
                  : "CSV, Excel or JSON"}
              </span>
              <input
                type="file"
                className="sr-only"
                accept={catalog?.limits.extensions.join(",") ?? ".csv,.xlsx,.json"}
                disabled={busy}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void handleFile(file);
                  e.target.value = "";
                }}
              />
            </label>

            {(history ?? []).length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-medium uppercase text-muted-foreground">
                  Recent imports
                </div>
                <ul className="divide-y rounded-md border text-sm">
                  {(history ?? []).map((past) => (
                    <li key={past.id} className="flex items-center justify-between gap-3 p-2.5">
                      <div className="min-w-0">
                        <div className="truncate font-medium">{past.file_name}</div>
                        <div className="text-xs text-muted-foreground">
                          {new Date(past.created_at).toLocaleString()} · {statusLabel(past)}
                        </div>
                      </div>
                      {["importing", "completed", "undoing", "undone"].includes(past.status) && (
                        <Button size="sm" variant="ghost" onClick={() => openPastImport(past)}>
                          {past.status === "importing" ? "Resume" : "View"}
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {step === "map" && job && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-end gap-3">
              {presets.length > 0 && (
                <div className="space-y-1.5">
                  <Label className="text-xs">Use a saved mapping</Label>
                  <Select
                    onValueChange={(name) => {
                      const preset = presets.find((p) => p.name === name);
                      if (preset) {
                        setMapping(
                          Object.fromEntries(
                            job.columns.map((c) => [c, preset.mapping[c] ?? null]),
                          ),
                        );
                      }
                    }}
                  >
                    <SelectTrigger className="w-56">
                      <SelectValue placeholder="Choose…" />
                    </SelectTrigger>
                    <SelectContent>
                      {presets.map((p) => (
                        <SelectItem key={p.name} value={p.name}>
                          {p.name}
                          {p.built_in ? " (built in)" : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              <div className="text-sm text-muted-foreground">
                {job.total_rows.toLocaleString()} rows · {job.columns.length} columns
              </div>
            </div>

            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="p-2.5 text-left">Column in your file</th>
                    <th className="p-2.5 text-left">Example values</th>
                    <th className="p-2.5 text-left w-64">Import as</th>
                  </tr>
                </thead>
                <tbody>
                  {job.columns.map((column) => (
                    <tr key={column} className="border-t">
                      <td className="p-2.5 font-medium">{column}</td>
                      <td className="p-2.5 text-xs text-muted-foreground max-w-[240px] truncate">
                        {sample
                          .map((row) => row[column])
                          .filter(Boolean)
                          .slice(0, 2)
                          .join(" · ") || "—"}
                      </td>
                      <td className="p-2.5">
                        <Select
                          value={mapping[column] ?? SKIP}
                          onValueChange={(value) =>
                            setMapping((prev) => ({
                              ...prev,
                              [column]: value === SKIP ? null : value,
                            }))
                          }
                        >
                          <SelectTrigger className="h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value={SKIP}>Don&apos;t import</SelectItem>
                            {fields.map((f) => (
                              <SelectItem key={f.key} value={f.key}>
                                {f.label}
                                {f.required ? " *" : ""}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {busy && (
              <p className="text-sm text-muted-foreground">
                Checking {job.total_rows.toLocaleString()} rows… a file of 100,000 rows takes about
                a minute.
              </p>
            )}

            {requiredMissing.length > 0 && (
              <p className="text-sm text-destructive">
                Map a column to {requiredMissing.map((f) => f.label).join(", ")} — it is required.
              </p>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label className="text-xs">When a row matches a record already in the system</Label>
                <RadioGroup
                  value={duplicateMode}
                  onValueChange={(v) => setDuplicateMode(v as "skip" | "update")}
                >
                  <label className="flex items-center gap-2 text-sm">
                    <RadioGroupItem value="skip" /> Skip it (keep the existing record as it is)
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <RadioGroupItem value="update" /> Update the existing record with the
                    file&apos;s values
                  </label>
                </RadioGroup>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs" htmlFor="preset-name">
                  Save this mapping for next time (optional)
                </Label>
                <Input
                  id="preset-name"
                  placeholder="e.g. Ceipal vendors"
                  value={presetName}
                  onChange={(e) => setPresetName(e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        {step === "review" && check && job && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Stat label="Ready to import" value={check.valid} tone="good" />
              <Stat
                label={duplicateMode === "update" ? "Will update" : "Duplicates to skip"}
                value={check.duplicates}
              />
              <Stat
                label="Have problems"
                value={check.invalid}
                tone={check.invalid ? "bad" : undefined}
              />
              <Stat label="With warnings" value={check.with_warnings} />
            </div>
            {check.invalid > 0 && (
              <div className="space-y-2">
                <p className="text-sm">
                  Rows with problems will be left out. After the import you can download them, fix
                  them and import just those.
                </p>
                <ul className="max-h-48 overflow-y-auto divide-y rounded-md border text-sm">
                  {check.problems.map((p) => (
                    <li key={p.row_number} className="p-2">
                      <span className="font-medium">Row {p.row_number}:</span> {p.message}
                    </li>
                  ))}
                </ul>
                {check.invalid > check.problems.length && (
                  <p className="text-xs text-muted-foreground">
                    Showing the first {check.problems.length} of {check.invalid.toLocaleString()}.
                  </p>
                )}
              </div>
            )}
            {entity === "candidates" && (
              <p className="text-xs text-muted-foreground">
                Imported candidates are tagged “Imported” and are not AI-scored. Candidates without
                an email are imported and tagged “Missing email”.
              </p>
            )}
            {entity === "jobs" && (
              <p className="text-xs text-muted-foreground">
                Jobs are imported as drafts; publish them when they are ready.
              </p>
            )}
          </div>
        )}

        {step === "importing" && job && (
          <div className="space-y-3 py-4">
            <Progress value={progress} />
            <div className="flex justify-between text-sm">
              <span>
                {job.processed_rows.toLocaleString()} of {job.total_rows.toLocaleString()} rows
              </span>
              <span className="text-muted-foreground">
                {job.created_count.toLocaleString()} added · {job.updated_count.toLocaleString()}{" "}
                updated · {job.skipped_count.toLocaleString()} skipped
              </span>
            </div>
          </div>
        )}

        {step === "done" && job && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              {job.status === "undone" ? (
                <>
                  <RotateCcw className="h-4 w-4" /> This import was undone.
                  {job.kept_on_undo > 0 &&
                    ` ${job.kept_on_undo.toLocaleString()} records were kept because they are now in use.`}
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Import complete.
                </>
              )}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Stat label="Added" value={job.created_count} tone="good" />
              <Stat label="Updated" value={job.updated_count} />
              <Stat label="Skipped (duplicates)" value={job.skipped_count} />
              <Stat
                label="Rejected"
                value={job.rejected_count}
                tone={job.rejected_count ? "bad" : undefined}
              />
            </div>
            {job.rejected_count > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                onClick={() => void downloadRejectedRows(job)}
              >
                <Download className="h-4 w-4" /> Download rejected rows
              </Button>
            )}
            {(job.status === "completed" || job.status === "undoing") && job.created_count > 0 && (
              <div className="rounded-md border p-3 text-sm space-y-2">
                {confirmUndo ? (
                  <>
                    <p>
                      This deletes the {job.created_count.toLocaleString()} records this import
                      added. Records someone has started using since are kept, and records it
                      updated keep their new values.
                    </p>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={busy}
                        onClick={() => void handleUndo()}
                      >
                        {busy && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                        Yes, undo this import
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setConfirmUndo(false)}>
                        Cancel
                      </Button>
                    </div>
                  </>
                ) : (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="gap-1 px-0"
                    onClick={() => setConfirmUndo(true)}
                  >
                    <RotateCcw className="h-4 w-4" /> Undo this import
                  </Button>
                )}
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          {step === "map" && (
            <>
              <Button variant="ghost" onClick={() => setStep("upload")} disabled={busy}>
                Back
              </Button>
              <Button
                onClick={() => void handleCheck()}
                disabled={busy || requiredMissing.length > 0}
              >
                {busy && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                Check file
              </Button>
            </>
          )}
          {step === "review" && check && job && (
            <>
              <Button variant="ghost" onClick={() => setStep("map")}>
                Change mapping
              </Button>
              <Button
                onClick={() => void runImport(job)}
                disabled={check.valid + check.duplicates === 0}
              >
                Import {(check.valid + check.duplicates).toLocaleString()} rows
              </Button>
            </>
          )}
          {step === "importing" && (
            <Button
              variant="outline"
              onClick={() => {
                if ((error || isPaused) && job) void runImport(job);
                else paused.current = true;
              }}
            >
              {error || isPaused ? "Resume" : "Pause"}
            </Button>
          )}
          {(step === "done" || step === "upload") && (
            <Button variant="outline" onClick={onClose} disabled={busy}>
              Close
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function statusLabel(job: ImportJob): string {
  switch (job.status) {
    case "completed":
      return `${job.created_count.toLocaleString()} added, ${job.updated_count.toLocaleString()} updated`;
    case "importing":
      return `paused at ${job.processed_rows.toLocaleString()} of ${job.total_rows.toLocaleString()}`;
    case "undoing":
      return "undo interrupted — open to finish it";
    case "undone":
      return "undone";
    default:
      return "not imported";
  }
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: "good" | "bad" }) {
  return (
    <div className="rounded-md border p-3">
      <div
        className={
          tone === "good"
            ? "text-xl font-semibold text-emerald-600"
            : tone === "bad"
              ? "text-xl font-semibold text-destructive"
              : "text-xl font-semibold"
        }
      >
        {value.toLocaleString()}
      </div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}
