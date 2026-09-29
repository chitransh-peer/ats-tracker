import { apiClient, downloadFile } from "./client";

export type ImportEntity = "candidates" | "vendors" | "clients" | "jobs" | "bench";

export interface ImportField {
  key: string;
  label: string;
  kind: string;
  required: boolean;
  help: string | null;
  choices: string[];
}

export interface ImportCatalog {
  entities: { key: ImportEntity; label: string; fields: ImportField[] }[];
  limits: { max_file_mb: number; max_rows: number; extensions: string[] };
}

export interface ImportJob {
  id: string;
  entity: ImportEntity;
  status: "uploaded" | "checked" | "importing" | "completed" | "undoing" | "undone";
  file_name: string;
  columns: string[];
  /** Source column -> field key, or null for "don't import". */
  mapping: Record<string, string | null>;
  duplicate_mode: "skip" | "update";
  total_rows: number;
  processed_rows: number;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  rejected_count: number;
  kept_on_undo: number;
  created_at: string;
  updated_at: string;
}

export interface ImportPreset {
  id: string | null;
  name: string;
  mapping: Record<string, string>;
  built_in: boolean;
}

export interface UploadResult {
  job: ImportJob;
  sample: Record<string, string>[];
  presets: ImportPreset[];
}

export interface CheckResult {
  job: ImportJob;
  valid: number;
  invalid: number;
  duplicates: number;
  with_warnings: number;
  problems: { row_number: number; message: string }[];
}

export function getImportCatalog() {
  return apiClient.get<ImportCatalog>("/imports/catalog");
}

export function uploadImport(entity: ImportEntity, file: File) {
  const form = new FormData();
  form.append("entity", entity);
  form.append("file", file);
  return apiClient.postForm<UploadResult>("/imports", form);
}

export function checkImport(
  jobId: string,
  input: {
    mapping: Record<string, string | null>;
    duplicate_mode: "skip" | "update";
    save_preset_as?: string | null;
  },
) {
  return apiClient.post<CheckResult>(`/imports/${jobId}/check`, input);
}

/** Imports the next chunk (up to 1,000 rows) and returns the progress. */
export function processImportChunk(jobId: string) {
  return apiClient.post<ImportJob>(`/imports/${jobId}/process`);
}

/** Undoes the next batch; call until the status is "undone". */
export function undoImport(jobId: string) {
  return apiClient.post<ImportJob>(`/imports/${jobId}/undo`);
}

export function listImports(entity: ImportEntity) {
  return apiClient.get<ImportJob[]>(`/imports?entity=${entity}&limit=10`);
}

export function downloadRejectedRows(job: ImportJob) {
  const stem = job.file_name.replace(/\.[^.]+$/, "");
  return downloadFile(`/imports/${job.id}/rejected`, `${stem}-rejected.csv`);
}

export function downloadExport(entity: ImportEntity, format: "csv" | "json") {
  const stamp = new Date().toISOString().slice(0, 10);
  return downloadFile(`/exports/${entity}?format=${format}`, `${entity}-${stamp}.${format}`);
}
