"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Pager } from "@/components/ui/pager";
import { listCeipalCandidates, type CeipalCandidateRow } from "@/lib/api/ceipal";
import { CandidateDocumentLink } from "@/components/document-preview-dialog";

const PAGE_SIZE = 50;

/**
 * Candidates imported from Ceipal, in Ceipal's own columns: one column per
 * Ceipal header, in Ceipal's order, each value under the header it had there
 * (the server sends both, so they cannot drift apart), and the résumé last.
 */
export function CeipalCandidatesTable({ search }: { search: string }) {
  const [offset, setOffset] = useState(0);
  const [lastSearch, setLastSearch] = useState(search);
  if (search !== lastSearch) {
    setLastSearch(search);
    setOffset(0);
  }

  const { data, isLoading } = useQuery({
    queryKey: ["ceipal-candidates", search, offset],
    queryFn: () => listCeipalCandidates({ search: search || undefined, limit: PAGE_SIZE, offset }),
    placeholderData: (previous) => previous,
  });
  const columns = data?.columns ?? [];
  const rows = data?.rows ?? [];

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm whitespace-nowrap">
          <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="p-3 text-left font-medium sticky left-0 bg-muted z-10">Candidate</th>
              {columns.map((column) => (
                <th key={column} className="p-3 text-left font-medium">
                  {column}
                </th>
              ))}
              <th className="p-3 text-left font-medium">Resume</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading && (
              <tr>
                <td
                  colSpan={columns.length + 2}
                  className="p-6 text-center text-sm text-muted-foreground"
                >
                  Loading Ceipal candidates…
                </td>
              </tr>
            )}
            {!isLoading && rows.length === 0 && (
              <tr>
                <td
                  colSpan={columns.length + 2}
                  className="p-6 text-left text-sm text-muted-foreground"
                >
                  {search
                    ? "No Ceipal candidates match that search."
                    : "No candidates imported from Ceipal yet. Use “Import from Ceipal” above."}
                </td>
              </tr>
            )}
            {rows.map((row) => (
              <tr key={row.candidate_id} className="hover:bg-muted/30">
                <td className="p-3 sticky left-0 bg-background z-10">
                  <Link
                    href={`/candidates/${row.candidate_id}`}
                    className="font-medium hover:underline"
                  >
                    {row.full_name}
                  </Link>
                </td>
                {columns.map((column) => (
                  <td
                    key={column}
                    className="p-3 text-xs max-w-[320px] truncate"
                    title={row.values[column] ?? ""}
                  >
                    <CellValue column={column} value={row.values[column] ?? ""} />
                  </td>
                ))}
                <td className="p-3">
                  <ResumeLink row={row} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pager
        offset={offset}
        limit={PAGE_SIZE}
        total={data?.total ?? 0}
        onOffsetChange={setOffset}
      />
    </>
  );
}

function CellValue({ column, value }: { column: string; value: string }) {
  if (!value) return <span className="text-muted-foreground">—</span>;
  if (/url$/i.test(column) && /^https?:\/\//i.test(value)) {
    return (
      <a
        href={value}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary hover:underline"
      >
        {value}
      </a>
    );
  }
  return <>{value}</>;
}

function ResumeLink({ row }: { row: CeipalCandidateRow }) {
  if (!row.resume) return <span className="text-xs text-muted-foreground">—</span>;
  return (
    <CandidateDocumentLink
      candidateId={row.candidate_id}
      documentId={row.resume.document_id}
      fileName={row.resume.file_name}
      className="gap-1 text-xs max-w-[240px]"
      iconClassName="h-3.5 w-3.5"
    />
  );
}
