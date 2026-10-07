/**
 * Driving a Ceipal backup import from the browser.
 *
 * The backup arrives as ZIPs -- one of CSV tables, one or more of résumé
 * files -- that are far too big to upload whole. So they are opened here
 * (lib/ceipal/zip.ts), the tables are parsed (lib/ceipal/csv.ts) and sent
 * as row batches, and the résumés are sent a few at a time. Every request is
 * small and can be repeated, so a dropped connection costs one retry, and
 * closing the tab costs nothing that picking the same files again won't
 * restore.
 */

import { ApiError } from "@/lib/api/client";
import {
  pendingCeipalDocuments,
  processCeipalImport,
  stageCeipalRows,
  uploadCeipalDocuments,
  type CeipalDocumentResult,
  type CeipalImport,
  type CeipalTableKind,
} from "@/lib/api/ceipal";
import { readCsvRecords } from "./csv";
import { ZipReader } from "./zip";

export interface TableSource {
  table: CeipalTableKind;
  /** Where it came from, e.g. "backup_08_2026.zip › Applicants.csv". */
  label: string;
  open: () => Promise<ReadableStream<Uint8Array>>;
}

export interface DocumentSource {
  /** The file name Ceipal stored it under, which is how it is matched. */
  name: string;
  size: number;
  blob: () => Promise<Blob>;
}

export interface ScannedBackup {
  tables: TableSource[];
  documents: DocumentSource[];
  /** Files picked that are neither a Ceipal table nor a document. */
  ignored: string[];
}

const TABLE_STEMS: Record<string, CeipalTableKind> = {
  applicants: "applicants",
  applicant_documents: "documents",
  applicant_education_details: "education",
  applicant_action_notes: "notes",
  submissions: "submissions",
  submission_notes: "submission_notes",
  user_profiles: "users",
  master_data_degrees: "degrees",
};

/** Ceipal's file name for each table, for showing what was found. */
export const TABLE_FILES: Record<CeipalTableKind, string> = {
  applicants: "Applicants.csv",
  documents: "Applicant_Documents.csv",
  education: "Applicant_Education_Details.csv",
  notes: "Applicant_Action_Notes.csv",
  submissions: "Submissions.csv",
  submission_notes: "Submission_Notes.csv",
  users: "User_Profiles.csv",
  degrees: "Master_Data_Degrees.csv",
};

function tableFor(fileName: string): CeipalTableKind | null {
  if (!fileName.toLowerCase().endsWith(".csv")) return null;
  const stem = fileName.slice(0, -4).split(" (")[0].trim().toLowerCase();
  return TABLE_STEMS[stem] ?? null;
}

function isJunk(name: string): boolean {
  return name.startsWith(".") || name === "Thumbs.db" || name === "desktop.ini";
}

/** Sort what was picked into tables and documents. ZIPs are looked inside. */
export async function scanFiles(files: File[]): Promise<ScannedBackup> {
  const scanned: ScannedBackup = { tables: [], documents: [], ignored: [] };
  for (const file of files) {
    if (file.name.toLowerCase().endsWith(".zip")) {
      const zip = await ZipReader.open(file);
      for (const entry of zip.entries) {
        if (entry.path.startsWith("__MACOSX/") || isJunk(entry.name)) continue;
        const table = tableFor(entry.name);
        if (table) {
          scanned.tables.push({
            table,
            label: `${file.name} › ${entry.name}`,
            open: () => zip.stream(entry),
          });
        } else if (entry.name.toLowerCase().endsWith(".csv")) {
          scanned.ignored.push(`${file.name} › ${entry.name}`);
        } else {
          scanned.documents.push({
            name: entry.name,
            size: entry.size,
            blob: () => zip.blob(entry),
          });
        }
      }
      continue;
    }
    const table = tableFor(file.name);
    if (table) {
      scanned.tables.push({ table, label: file.name, open: async () => file.stream() });
    } else if (file.name.toLowerCase().endsWith(".csv")) {
      scanned.ignored.push(file.name);
    } else if (!isJunk(file.name)) {
      scanned.documents.push({ name: file.name, size: file.size, blob: async () => file });
    }
  }
  return scanned;
}

// ------------------------------------------------------------------ retries

const RETRIES = 4;

function retryable(error: unknown): boolean {
  // A 4xx is an answer -- the request was wrong and sending it again won't
  // change that. Anything else (network, 5xx, a timeout) is worth another go.
  return !(error instanceof ApiError) || error.status >= 500 || error.status === 429;
}

async function withRetry<T>(work: () => Promise<T>, signal?: AbortSignal): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    if (signal?.aborted) throw new DOMException("Stopped", "AbortError");
    try {
      return await work();
    } catch (error) {
      if (attempt >= RETRIES || !retryable(error)) throw error;
      await new Promise((resolve) => setTimeout(resolve, 1000 * 2 ** attempt));
    }
  }
}

// ------------------------------------------------------------------ tables

// Users and degrees first (small lookups), then Applicants, whose Ids decide
// which rows of the child tables are worth sending at all: Ceipal's education
// table covers every applicant it has ever held, not just this backup's.
const TABLE_ORDER: CeipalTableKind[] = [
  "users",
  "degrees",
  "applicants",
  "documents",
  "submissions",
  "submission_notes",
  "notes",
  "education",
];
const FILTERED_BY_APPLICANT: Partial<Record<CeipalTableKind, string>> = {
  education: "applicant id",
  notes: "applicant id",
  submissions: "applicant id",
};

const BATCH_ROWS = 1000;
const BATCH_CHARS = 3_000_000;

export interface StageProgress {
  label: string;
  rowsSent: number;
}

export async function stageTables(
  importId: string,
  tables: TableSource[],
  onProgress: (progress: StageProgress) => void,
  signal?: AbortSignal,
): Promise<void> {
  const applicantIds = new Set<string>();
  const ordered = [...tables].sort(
    (a, b) => TABLE_ORDER.indexOf(a.table) - TABLE_ORDER.indexOf(b.table),
  );

  for (const source of ordered) {
    let headers: string[] | null = null;
    let batch: Record<string, string>[] = [];
    let batchChars = 0;
    let sent = 0;
    const filterHeader = FILTERED_BY_APPLICANT[source.table];
    let filterIndex = -1;
    let idIndex = -1;

    const flush = async () => {
      if (batch.length === 0) return;
      const rows = batch;
      const firstRow = sent + 1;
      batch = [];
      batchChars = 0;
      await withRetry(
        () =>
          stageCeipalRows(importId, {
            kind: source.table,
            source: source.label.slice(0, 255),
            first_row: firstRow,
            headers: headers ?? [],
            rows,
          }),
        signal,
      );
      sent += rows.length;
      onProgress({ label: source.label, rowsSent: sent });
    };

    for await (const record of readCsvRecords(await source.open())) {
      if (signal?.aborted) throw new DOMException("Stopped", "AbortError");
      if (headers === null) {
        headers = record.map((h) => h.trim());
        const lower = headers.map((h) => h.toLowerCase());
        idIndex = lower.indexOf("id");
        if (filterHeader) filterIndex = lower.indexOf(filterHeader);
        continue;
      }
      if (record.length === 1 && record[0] === "") continue;
      if (source.table === "applicants" && idIndex >= 0 && record[idIndex]) {
        applicantIds.add(record[idIndex].trim());
      }
      if (filterIndex >= 0 && !applicantIds.has((record[filterIndex] ?? "").trim())) continue;

      const row: Record<string, string> = {};
      headers.forEach((header, i) => {
        row[header] = record[i] ?? "";
        batchChars += header.length + (record[i]?.length ?? 0) + 6;
      });
      batch.push(row);
      if (batch.length >= BATCH_ROWS || batchChars >= BATCH_CHARS) await flush();
    }
    await flush();
    onProgress({ label: source.label, rowsSent: sent });
  }
}

// ------------------------------------------------------------------ import

export async function runImport(
  importId: string,
  onProgress: (job: CeipalImport) => void,
  signal?: AbortSignal,
): Promise<CeipalImport> {
  for (;;) {
    const job = await withRetry(() => processCeipalImport(importId), signal);
    onProgress(job);
    if (job.status !== "importing" && job.status !== "staging") return job;
  }
}

// ------------------------------------------------------------------ documents

export interface DocumentProgress {
  /** Files in what was picked that this import is waiting for. */
  matched: number;
  sent: number;
  attached: number;
  skipped: number;
  rejected: number;
  problems: CeipalDocumentResult[];
  job: CeipalImport | null;
}

const UPLOAD_FILES = 10;
const UPLOAD_BYTES = 15 * 1024 * 1024;
const UPLOAD_PARALLEL = 3;

async function pendingNames(importId: string, signal?: AbortSignal): Promise<Set<string>> {
  const names = new Set<string>();
  for (let offset = 0; ;) {
    const page = await withRetry(() => pendingCeipalDocuments(importId, offset), signal);
    page.names.forEach((n) => names.add(n.normalize("NFC")));
    if (page.names.length === 0) break;
    offset += page.names.length;
  }
  return names;
}

export async function uploadDocuments(
  importId: string,
  documents: DocumentSource[],
  onProgress: (progress: DocumentProgress) => void,
  signal?: AbortSignal,
): Promise<DocumentProgress> {
  const pending = await pendingNames(importId, signal);
  const seen = new Set<string>();
  const wanted = documents.filter((d) => {
    const name = d.name.normalize("NFC");
    if (!pending.has(name) || seen.has(name)) return false;
    seen.add(name);
    return true;
  });

  const progress: DocumentProgress = {
    matched: wanted.length,
    sent: 0,
    attached: 0,
    skipped: 0,
    rejected: 0,
    problems: [],
    job: null,
  };
  onProgress({ ...progress });

  // Batches by count and size, so one request stays well under 32 MB.
  const batches: DocumentSource[][] = [];
  let current: DocumentSource[] = [];
  let currentBytes = 0;
  for (const doc of wanted) {
    if (
      current.length >= UPLOAD_FILES ||
      (current.length > 0 && currentBytes + doc.size > UPLOAD_BYTES)
    ) {
      batches.push(current);
      current = [];
      currentBytes = 0;
    }
    current.push(doc);
    currentBytes += doc.size;
  }
  if (current.length > 0) batches.push(current);

  let next = 0;
  const worker = async () => {
    while (next < batches.length) {
      const batch = batches[next++];
      const files = await Promise.all(
        batch.map(async (d) => ({ name: d.name, blob: await d.blob() })),
      );
      const response = await withRetry(() => uploadCeipalDocuments(importId, files), signal);
      for (const result of response.results) {
        progress[result.outcome] += 1;
        if (result.outcome === "rejected" && progress.problems.length < 200) {
          progress.problems.push(result);
        }
      }
      progress.sent += batch.length;
      progress.job = response.job;
      onProgress({ ...progress, problems: [...progress.problems] });
    }
  };
  await Promise.all(Array.from({ length: Math.min(UPLOAD_PARALLEL, batches.length) }, worker));
  return progress;
}
