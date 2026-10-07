/**
 * Ceipal's CSV dialect, read as a stream.
 *
 * Ceipal writes its backup tables the way MySQL's INTO OUTFILE does: every
 * value in double quotes, a quote inside a value escaped with a backslash
 * (\"), a backslash as \\, NULL as an unquoted \N. A standard CSV reader gets
 * these rows wrong -- `"Yuliya \"Julia\" Neporent, CSM"` splits at the comma
 * and shifts every column after it. Doubled quotes ("") are accepted too, so
 * a table re-saved from Excel still reads.
 *
 * \N is passed through as the two characters "\N"; the server treats that as
 * empty.
 */

export class CeipalCsvParser {
  private field = "";
  private record: string[] = [];
  private inQuotes = false;
  /** A backslash was the last character seen. */
  private escaping = false;
  /** Inside quotes, a quote was seen: either the end, or the first of "". */
  private quotePending = false;
  /** The current field began with a quote (so it is not a bare \N). */
  private fieldStarted = false;
  private skipBom = true;

  /** Feed the next chunk of text; returns the records it completed. */
  push(text: string): string[][] {
    const done: string[][] = [];
    let i = 0;
    if (this.skipBom) {
      if (text.charCodeAt(0) === 0xfeff) i = 1;
      if (text.length > 0) this.skipBom = false;
    }
    for (; i < text.length; i++) {
      const c = text[i];

      if (this.escaping) {
        this.escaping = false;
        if (c === "N") this.field += "\\N";
        else if (c === "0") this.field += "";
        else this.field += c;
        continue;
      }

      if (this.quotePending) {
        this.quotePending = false;
        if (c === '"') {
          this.field += '"';
          continue;
        }
        this.inQuotes = false;
        // Fall through: c is the character after the closing quote.
      }

      if (c === "\\") {
        this.escaping = true;
        this.fieldStarted = true;
        continue;
      }

      if (this.inQuotes) {
        if (c === '"') this.quotePending = true;
        else this.field += c;
        continue;
      }

      if (c === '"' && !this.fieldStarted) {
        this.inQuotes = true;
        this.fieldStarted = true;
      } else if (c === ",") {
        this.endField();
      } else if (c === "\n") {
        this.endField();
        done.push(this.record);
        this.record = [];
      } else if (c === "\r") {
        // Part of a CRLF line ending outside quotes.
      } else {
        this.field += c;
        this.fieldStarted = true;
      }
    }
    return done;
  }

  /** Call once the text has ended; returns the last record, if any. */
  end(): string[][] {
    if (this.escaping) this.field += "\\";
    this.escaping = false;
    this.quotePending = false;
    this.inQuotes = false;
    if (this.field !== "" || this.record.length > 0) {
      this.endField();
      const last = this.record;
      this.record = [];
      return [last];
    }
    return [];
  }

  private endField() {
    this.record.push(this.field);
    this.field = "";
    this.fieldStarted = false;
  }
}

/** Every record in a stream of CSV bytes; the first is the header. */
export async function* readCsvRecords(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<string[]> {
  const parser = new CeipalCsvParser();
  const decoder = new TextDecoder("utf-8");
  const reader = stream.getReader();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const record of parser.push(decoder.decode(value, { stream: true }))) yield record;
    }
    for (const record of parser.push(decoder.decode())) yield record;
    for (const record of parser.end()) yield record;
  } finally {
    reader.releaseLock();
  }
}
