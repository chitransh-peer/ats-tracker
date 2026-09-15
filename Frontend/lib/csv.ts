function escapeCell(value: unknown): string {
  if (value == null) return "";
  const text = String(value);
  // Quote whenever the value could otherwise break the row/column structure.
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/**
 * Serialize `rows` to CSV using `columns` as both the header and the key order,
 * then trigger a browser download.
 */
export function downloadCsv<T extends object>(
  filename: string,
  columns: (keyof T & string)[],
  rows: T[],
): void {
  const lines = [
    columns.join(","),
    ...rows.map((row) => columns.map((col) => escapeCell(row[col])).join(",")),
  ];
  // The BOM keeps Excel from mangling non-ASCII names.
  const blob = new Blob(["﻿" + lines.join("\r\n")], {
    type: "text/csv;charset=utf-8;",
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
