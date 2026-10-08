"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { apiClient, ApiError, downloadFile } from "@/lib/api/client";
import type { DocumentPreview } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/utils";

/** A candidate document's name as a link that opens it in the preview. */
export function CandidateDocumentLink({
  candidateId,
  documentId,
  fileName,
  className,
  iconClassName = "h-4 w-4",
}: {
  candidateId: string;
  documentId: string;
  fileName: string;
  className?: string;
  iconClassName?: string;
}) {
  const [open, setOpen] = useState(false);
  const base = `/candidates/${candidateId}/documents/${documentId}`;
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={cn("inline-flex items-center gap-1.5 text-primary hover:underline", className)}
        title={fileName}
      >
        <FileText className={cn("shrink-0", iconClassName)} />
        <span className="truncate">{fileName}</span>
      </button>
      {open && (
        <DocumentPreviewDialog
          open
          onOpenChange={setOpen}
          previewPath={`${base}/preview`}
          fileName={fileName}
          onDownload={() => downloadFile(`${base}/download`, fileName)}
        />
      )}
    </>
  );
}

/**
 * Reads a résumé or document inside the app. The server sends page images
 * (PDF) or text (Word), never the file, so a viewer without the download
 * permission can read it but not take a copy; Download is offered only to
 * those the server says may download.
 */
export function DocumentPreviewDialog({
  open,
  onOpenChange,
  previewPath,
  fileName,
  onDownload,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** API path of the document's /preview endpoint. */
  previewPath: string;
  fileName: string;
  onDownload?: () => Promise<void>;
}) {
  const { user } = useAuth();
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const { data, isLoading, error } = useQuery({
    queryKey: ["document-preview", previewPath],
    queryFn: () => apiClient.get<DocumentPreview>(previewPath),
    enabled: open,
    staleTime: 5 * 60_000,
  });

  async function download() {
    if (!onDownload) return;
    setDownloadError(null);
    setDownloading(true);
    try {
      await onDownload();
    } catch (err) {
      setDownloadError(err instanceof ApiError ? err.message : "Could not download that file.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl w-[calc(100vw-2rem)] h-[90vh] flex flex-col gap-3 p-4">
        <DialogHeader className="flex-row items-center justify-between gap-3 space-y-0 pr-8">
          <div className="min-w-0">
            <DialogTitle className="truncate text-base">{fileName}</DialogTitle>
            <DialogDescription className="text-xs">
              {data?.kind === "pages" && data.page_count > 0
                ? `${data.page_count} page${data.page_count === 1 ? "" : "s"}${
                    data.truncated ? ` · first ${data.pages.length} shown` : ""
                  }`
                : "Preview"}
              {data && !data.can_download && " · View only"}
            </DialogDescription>
          </div>
          {data?.can_download && onDownload && (
            <Button size="sm" variant="outline" onClick={download} disabled={downloading}>
              {downloading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Download className="h-4 w-4 mr-1" />
                  Download
                </>
              )}
            </Button>
          )}
        </DialogHeader>
        {downloadError && <div className="text-sm text-destructive">{downloadError}</div>}

        <div className="relative flex-1 min-h-0">
          <div
            className="h-full overflow-y-auto rounded-md border bg-muted/40 select-none"
            onContextMenu={(e) => e.preventDefault()}
          >
            {isLoading ? (
              <div className="flex h-full items-center justify-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading preview…
              </div>
            ) : error ? (
              <div className="p-6 text-sm text-destructive">
                {error instanceof ApiError ? error.message : "Could not load the preview."}
              </div>
            ) : !data ? null : data.kind === "unsupported" ? (
              <div className="p-6 text-sm text-muted-foreground">
                {data.message ?? "Preview isn't available for this file."}
              </div>
            ) : data.kind === "pages" ? (
              <div className="space-y-4 p-4">
                {data.pages.map((page, i) => (
                  // eslint-disable-next-line @next/next/no-img-element -- in-memory data URI
                  <img
                    key={i}
                    src={`data:${page.content_type};base64,${page.data_base64}`}
                    alt={`Page ${i + 1} of ${fileName}`}
                    draggable={false}
                    className="mx-auto block w-full max-w-3xl bg-white shadow-sm"
                  />
                ))}
              </div>
            ) : (
              <article className="mx-auto max-w-3xl space-y-2 bg-background p-6 text-sm leading-relaxed shadow-sm">
                {data.blocks.length === 0 && (
                  <p className="text-muted-foreground">This document has no readable text.</p>
                )}
                {data.blocks.map((block, i) =>
                  block.kind === "heading" ? (
                    <h3 key={i} className="pt-2 text-base font-semibold">
                      {block.text}
                    </h3>
                  ) : block.kind === "table" ? (
                    <table key={i} className="w-full border-collapse text-xs">
                      <tbody>
                        {(block.rows ?? []).map((row, r) => (
                          <tr key={r}>
                            {row.map((cell, c) => (
                              <td key={c} className="border px-2 py-1 align-top">
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p key={i} className="whitespace-pre-wrap">
                      {block.text}
                    </p>
                  ),
                )}
                {data.truncated && (
                  <p className="pt-2 text-xs text-muted-foreground">Preview shortened.</p>
                )}
              </article>
            )}
          </div>
          {/* A faint mark of who is viewing, discouraging screenshots of a
              view-only document. */}
          {data && !data.can_download && user?.email && (
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 overflow-hidden opacity-[0.07]"
            >
              <div className="flex h-full w-full flex-wrap content-start gap-x-16 gap-y-24 p-8 -rotate-12 scale-125 text-sm font-semibold">
                {Array.from({ length: 60 }, (_, i) => (
                  <span key={i}>{user.email}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
