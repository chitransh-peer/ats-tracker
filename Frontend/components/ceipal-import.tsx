"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileArchive,
  FileUp,
  Loader2,
  RotateCcw,
  X,
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
import { Progress } from "@/components/ui/progress";
import { useCanImport } from "@/components/import-export";
import { ApiError } from "@/lib/api/client";
import {
  createCeipalImport,
  downloadCeipalReport,
  finishCeipalImport,
  listCeipalImports,
  undoCeipalImport,
  type CeipalImport,
} from "@/lib/api/ceipal";
import {
  TABLE_FILES,
  runImport,
  scanFiles,
  stageTables,
  uploadDocuments,
  type DocumentProgress,
  type ScannedBackup,
} from "@/lib/ceipal/importer";

function errorText(error: unknown, fallback: string): string {
  if (error instanceof DOMException && error.name === "AbortError") return "Stopped.";
  if (error instanceof ApiError) {
    const detail = error.detail as { detail?: unknown } | null;
    if (detail && typeof detail.detail === "string") return detail.detail;
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

function backupName(files: File[]): string {
  const zip = files.find((f) => f.name.toLowerCase().endsWith(".zip")) ?? files[0];
  if (!zip) return "Ceipal backup";
  return zip.name.replace(/\.zip$/i, "").replace(/_docs$/i, "");
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  if (bytes >= 1024 ** 2) return `${Math.round(bytes / 1024 ** 2)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/** The "Import from Ceipal" button on the candidates page; Admins only. */
export function CeipalImportButton() {
  const canImport = useCanImport();
  const [open, setOpen] = useState(false);
  if (!canImport) return null;
  return (
    <>
      <Button variant="outline" size="sm" className="gap-1" onClick={() => setOpen(true)}>
        <FileArchive className="h-4 w-4" />
        Import from Ceipal
      </Button>
      {open && <CeipalImportDialog onClose={() => setOpen(false)} />}
    </>
  );
}

type Step = "pick" | "running" | "done";
type Phase = "reading" | "staging" | "importing" | "documents";

function CeipalImportDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const { data: history, refetch: refetchHistory } = useQuery({
    queryKey: ["imports", "ceipal"],
    queryFn: listCeipalImports,
  });

  const [step, setStep] = useState<Step>("pick");
  const [phase, setPhase] = useState<Phase>("reading");
  const [files, setFiles] = useState<File[]>([]);
  const [scanned, setScanned] = useState<ScannedBackup | null>(null);
  const [scanning, setScanning] = useState(false);
  // An earlier import being carried on, rather than a new one.
  const [target, setTarget] = useState<CeipalImport | null>(null);
  const [job, setJob] = useState<CeipalImport | null>(null);
  const [staged, setStaged] = useState<Record<string, number>>({});
  const [docs, setDocs] = useState<DocumentProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmUndo, setConfirmUndo] = useState(false);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => () => abort.current?.abort(), []);

  const documentsOnly = target !== null && ["documents", "completed"].includes(target.status);

  async function rescan(list: File[]) {
    setFiles(list);
    setScanned(null);
    setError(null);
    if (list.length === 0) return;
    setScanning(true);
    try {
      setScanned(await scanFiles(list));
    } catch (err) {
      setError(errorText(err, "The files could not be read."));
    } finally {
      setScanning(false);
    }
  }

  function addFiles(picked: File[]) {
    const fresh = picked.filter((p) => !files.some((f) => f.name === p.name && f.size === p.size));
    void rescan([...files, ...fresh]);
  }

  function removeFile(file: File) {
    void rescan(files.filter((f) => f !== file));
  }

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["candidates"] });
    void queryClient.invalidateQueries({ queryKey: ["ceipal-candidates"] });
    void refetchHistory();
  }

  async function start() {
    if (!scanned) return;
    setError(null);
    setStep("running");
    const controller = new AbortController();
    abort.current = controller;
    const signal = controller.signal;
    try {
      let current = target;
      if (!documentsOnly) {
        if (current === null) {
          current = await createCeipalImport(backupName(files));
          setTarget(current);
        }
        setJob(current);
        if (current.status === "staging") {
          setPhase("staging");
          await stageTables(
            current.id,
            scanned.tables,
            (p) => setStaged((prev) => ({ ...prev, [p.label]: p.rowsSent })),
            signal,
          );
        }
        setPhase("importing");
        current = await runImport(current.id, setJob, signal);
        setTarget(current);
      }
      const waitingForFiles =
        current !== null &&
        (current.status === "documents" || current.status === "completed") &&
        current.documents_expected > current.documents_attached;
      if (current !== null && waitingForFiles && scanned.documents.length > 0) {
        setPhase("documents");
        const result = await uploadDocuments(current.id, scanned.documents, setDocs, signal);
        if (result.job) current = result.job;
      }
      setJob(current);
      setStep("done");
      refresh();
    } catch (err) {
      setError(
        errorText(err, "The import stopped.") +
          " Nothing already imported is lost — pick the same files and carry on from Recent imports.",
      );
      refresh();
    }
  }

  async function finish() {
    if (!job) return;
    setBusy(true);
    try {
      setJob(await finishCeipalImport(job.id));
      refresh();
    } catch (err) {
      setError(errorText(err, "Could not finish the import."));
    } finally {
      setBusy(false);
    }
  }

  async function undo() {
    if (!job) return;
    setBusy(true);
    setError(null);
    try {
      let result = await undoCeipalImport(job.id);
      while (result.status === "undoing") {
        setJob(result);
        result = await undoCeipalImport(job.id);
      }
      setJob(result);
      setConfirmUndo(false);
      refresh();
    } catch (err) {
      setError(errorText(err, "The import could not be undone."));
    } finally {
      setBusy(false);
    }
  }

  function carryOn(past: CeipalImport) {
    setTarget(past);
    setJob(past);
    setFiles([]);
    setScanned(null);
    setError(null);
    setDocs(null);
    if (["undone", "undoing"].includes(past.status)) {
      setStep("done");
      if (past.status === "undoing") setConfirmUndo(true);
    } else {
      setStep("pick");
    }
  }

  function addMoreParts() {
    if (job) carryOn(job);
  }

  const tablesFound = new Set(scanned?.tables.map((t) => t.table) ?? []);
  const missingApplicants =
    !documentsOnly && target === null && scanned !== null && !tablesFound.has("applicants");
  const canStart =
    !!scanned &&
    !scanning &&
    (documentsOnly
      ? scanned.documents.length > 0
      : tablesFound.has("applicants") || target !== null);

  const running = step === "running" && !error;
  const importPercent = job?.applicants_total
    ? Math.round((job.applicants_processed / job.applicants_total) * 100)
    : 0;
  const docsPercent = docs?.matched ? Math.round((docs.sent / docs.matched) * 100) : 0;
  const missingDocs = job ? Math.max(0, job.documents_expected - job.documents_attached) : 0;

  return (
    <Dialog
      open
      onOpenChange={(next) => {
        if (!next && !running && !busy) onClose();
      }}
    >
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Import from Ceipal</DialogTitle>
          <DialogDescription>
            {step === "pick" &&
              (documentsOnly
                ? `Add résumés to “${target?.name}”. Pick the remaining documents ZIP parts.`
                : target
                  ? `Carry on with “${target.name}”: pick the same backup files again.`
                  : "Pick the ZIP files Ceipal sent — the data ZIP and every documents ZIP part. They are read on this computer and sent in small pieces, so size doesn't matter.")}
            {step === "running" && "Keep this window open until it finishes."}
            {step === "done" && job?.name}
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="flex gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {step === "pick" && (
          <div className="space-y-5">
            <label className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center cursor-pointer hover:bg-muted/40">
              {scanning ? (
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              ) : (
                <FileUp className="h-8 w-8 text-muted-foreground" />
              )}
              <span className="text-sm font-medium">
                {scanning ? "Looking inside…" : "Choose ZIP files (you can add more)"}
              </span>
              <span className="text-xs text-muted-foreground">
                .zip, or the extracted .csv tables and résumé files
              </span>
              <input
                type="file"
                multiple
                className="sr-only"
                disabled={scanning}
                onChange={(e) => {
                  const picked = Array.from(e.target.files ?? []);
                  if (picked.length > 0) addFiles(picked);
                  e.target.value = "";
                }}
              />
            </label>

            {files.length > 0 && (
              <div className="rounded-md border divide-y text-sm">
                {files.map((f) => (
                  <div key={`${f.name}-${f.size}`} className="flex items-center gap-2 px-3 py-2">
                    <FileArchive className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="truncate flex-1">{f.name}</span>
                    <span className="text-xs text-muted-foreground">{formatBytes(f.size)}</span>
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      onClick={() => removeFile(f)}
                      aria-label={`Remove ${f.name}`}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {scanned && (
              <div className="rounded-md border p-3 text-sm space-y-2">
                <div className="font-medium">Found</div>
                {!documentsOnly && (
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(TABLE_FILES).map(([kind, fileName]) => (
                      <span
                        key={kind}
                        className={
                          tablesFound.has(kind as keyof typeof TABLE_FILES)
                            ? "rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700"
                            : "rounded border px-2 py-0.5 text-xs text-muted-foreground line-through"
                        }
                      >
                        {fileName}
                      </span>
                    ))}
                  </div>
                )}
                <div className="text-muted-foreground">
                  {scanned.documents.length.toLocaleString()} documents (résumés and other files)
                  {scanned.ignored.length > 0 &&
                    ` · ${scanned.ignored.length} other file${scanned.ignored.length === 1 ? "" : "s"} ignored`}
                </div>
                {missingApplicants && (
                  <div className="text-destructive text-xs">
                    Applicants.csv was not found. Add the data ZIP (the one without “_docs”).
                  </div>
                )}
                {!documentsOnly && scanned.documents.length === 0 && (
                  <div className="text-xs text-muted-foreground">
                    No documents yet — you can add the documents ZIP parts now or after the
                    candidates are in.
                  </div>
                )}
              </div>
            )}

            {!target && history && history.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Recent Ceipal imports
                </div>
                <div className="rounded-md border divide-y">
                  {history.map((past) => (
                    <div key={past.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                      <div className="flex-1 min-w-0">
                        <div className="truncate font-medium">{past.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {new Date(past.created_at).toLocaleString()} · {statusLabel(past)}
                        </div>
                      </div>
                      <Button size="sm" variant="ghost" onClick={() => carryOn(past)}>
                        {past.status === "documents" || past.status === "completed"
                          ? "Add documents"
                          : past.status === "undone"
                            ? "View"
                            : "Carry on"}
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {step === "running" && (
          <div className="space-y-4 text-sm">
            <PhaseRow
              label="Reading the tables"
              state={phase === "staging" ? "active" : phase === "reading" ? "waiting" : "done"}
              skipped={documentsOnly}
            >
              {Object.entries(staged).map(([label, rows]) => (
                <div key={label} className="text-xs text-muted-foreground">
                  {label}: {rows.toLocaleString()} rows
                </div>
              ))}
            </PhaseRow>
            <PhaseRow
              label="Importing candidates"
              state={phase === "importing" ? "active" : phase === "documents" ? "done" : "waiting"}
              skipped={documentsOnly}
            >
              {job && job.applicants_total > 0 && (
                <>
                  <Progress value={importPercent} />
                  <div className="text-xs text-muted-foreground">
                    {job.applicants_processed.toLocaleString()} of{" "}
                    {job.applicants_total.toLocaleString()} applicants
                  </div>
                </>
              )}
            </PhaseRow>
            <PhaseRow
              label="Attaching résumés"
              state={phase === "documents" ? "active" : "waiting"}
            >
              {docs && (
                <>
                  <Progress value={docsPercent} />
                  <div className="text-xs text-muted-foreground">
                    {docs.sent.toLocaleString()} of {docs.matched.toLocaleString()} files ·{" "}
                    {docs.attached.toLocaleString()} attached
                    {docs.rejected > 0 && ` · ${docs.rejected.toLocaleString()} unusable`}
                  </div>
                </>
              )}
            </PhaseRow>
          </div>
        )}

        {step === "done" && job && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              {job.status === "undone" ? (
                <>
                  <RotateCcw className="h-4 w-4" /> This import was undone.
                  {job.kept_on_undo > 0 &&
                    ` ${job.kept_on_undo.toLocaleString()} candidates were kept because they are now in use.`}
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  {missingDocs > 0
                    ? "Candidates imported. Some résumés are still to come."
                    : "Import complete."}
                </>
              )}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Stat label="Candidates added" value={job.created_count} tone="good" />
              <Stat label="Updated" value={job.updated_count} />
              <Stat
                label="Not imported"
                value={job.rejected_count}
                tone={job.rejected_count ? "bad" : undefined}
              />
              <Stat
                label={`Résumés attached (of ${job.documents_expected.toLocaleString()})`}
                value={job.documents_attached}
                tone="good"
              />
              <Stat label="Education entries" value={job.education_count} />
              <Stat label="Submissions" value={job.submissions_count} />
              <Stat label="Linked to our jobs" value={job.submissions_linked} />
              <Stat label="Files for applicants not in backup" value={job.documents_orphaned} />
            </div>

            {docs && docs.problems.length > 0 && (
              <div className="rounded-md border p-3 text-xs space-y-1 max-h-40 overflow-y-auto">
                <div className="font-medium text-sm">Files that could not be attached</div>
                {docs.problems.map((p) => (
                  <div key={p.file_name}>
                    <span className="font-mono">{p.file_name}</span> — {p.message}
                  </div>
                ))}
              </div>
            )}

            {job.status !== "undone" && missingDocs > 0 && (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                {missingDocs.toLocaleString()} résumé{missingDocs === 1 ? " is" : "s are"} still
                missing. If Ceipal sent the documents in several ZIP parts, add the rest.
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              {job.status !== "undone" && (
                <Button size="sm" variant="outline" className="gap-1" onClick={addMoreParts}>
                  <FileUp className="h-4 w-4" /> Add documents ZIP parts
                </Button>
              )}
              {(job.rejected_count > 0 || missingDocs > 0 || job.documents_orphaned > 0) && (
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1"
                  onClick={() => void downloadCeipalReport(job)}
                >
                  <Download className="h-4 w-4" /> Download what wasn&apos;t imported
                </Button>
              )}
              {job.status === "documents" && (
                <Button size="sm" variant="outline" disabled={busy} onClick={() => void finish()}>
                  Mark as finished
                </Button>
              )}
            </div>

            {["documents", "completed", "undoing", "importing"].includes(job.status) && (
              <div className="rounded-md border p-3 text-sm space-y-2">
                {confirmUndo ? (
                  <>
                    <p>
                      This deletes the {job.created_count.toLocaleString()} candidates this import
                      added, with their résumés. Candidates someone has started working with since
                      are kept. Candidates that were already here lose only what this import
                      attached.
                    </p>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={busy}
                        onClick={() => void undo()}
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
          {step === "pick" && (
            <>
              {target && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setTarget(null);
                    setJob(null);
                    setFiles([]);
                    setScanned(null);
                  }}
                >
                  Back
                </Button>
              )}
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button onClick={() => void start()} disabled={!canStart}>
                {documentsOnly ? "Attach résumés" : target ? "Carry on" : "Start import"}
              </Button>
            </>
          )}
          {step === "running" &&
            (error ? (
              <Button variant="outline" onClick={() => setStep("pick")}>
                Back
              </Button>
            ) : (
              <Button variant="outline" onClick={() => abort.current?.abort()}>
                Stop
              </Button>
            ))}
          {step === "done" && (
            <Button variant="outline" onClick={onClose} disabled={busy}>
              Close
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PhaseRow({
  label,
  state,
  skipped,
  children,
}: {
  label: string;
  state: "waiting" | "active" | "done";
  skipped?: boolean;
  children?: React.ReactNode;
}) {
  if (skipped) return null;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2 font-medium">
        {state === "active" ? (
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
        ) : state === "done" ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
        ) : (
          <span className="h-4 w-4 rounded-full border" />
        )}
        <span className={state === "waiting" ? "text-muted-foreground" : undefined}>{label}</span>
      </div>
      {state !== "waiting" && <div className="pl-6 space-y-1">{children}</div>}
    </div>
  );
}

function statusLabel(job: CeipalImport): string {
  switch (job.status) {
    case "staging":
      return "not started — carry on with the same files";
    case "importing":
      return `paused at ${job.applicants_processed.toLocaleString()} of ${job.applicants_total.toLocaleString()}`;
    case "documents":
      return `${job.created_count.toLocaleString()} added · ${job.documents_attached.toLocaleString()} of ${job.documents_expected.toLocaleString()} résumés`;
    case "completed":
      return `${job.created_count.toLocaleString()} added, ${job.updated_count.toLocaleString()} updated`;
    case "undoing":
      return "undo interrupted — open to finish it";
    case "undone":
      return "undone";
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
