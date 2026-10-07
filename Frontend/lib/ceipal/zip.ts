/**
 * Reading ZIP files straight off the user's disk, without loading them.
 *
 * A Ceipal backup's documents ZIP runs to gigabytes. This reads only the
 * central directory (at the end of the file) and then, per entry, just that
 * entry's bytes via File.slice, inflating them with the browser's own
 * DecompressionStream. Memory use stays at about one file at a time.
 *
 * Handles stored and deflated entries and ZIP64 (archives over 4 GB or with
 * more than 65,535 entries). Not encrypted entries, and not split archives
 * (.z01, .z02...): Ceipal's "parts" are whole ZIPs, each opened on its own.
 */

export interface ZipEntry {
  /** Path inside the archive, e.g. "backup/documents/123_Jane-Doe.pdf". */
  path: string;
  /** Last path segment. */
  name: string;
  compressedSize: number;
  size: number;
  method: number;
  encrypted: boolean;
  localHeaderOffset: number;
}

const EOCD = 0x06054b50;
const ZIP64_LOCATOR = 0x07064b50;
const ZIP64_EOCD = 0x06064b50;
const CENTRAL = 0x02014b50;
const LOCAL = 0x04034b50;

async function bytes(file: Blob, start: number, end: number): Promise<DataView> {
  const buffer = await file.slice(start, end).arrayBuffer();
  return new DataView(buffer);
}

function u64(view: DataView, offset: number): number {
  return Number(view.getBigUint64(offset, true));
}

const utf8 = new TextDecoder("utf-8");

export class ZipReader {
  private constructor(
    readonly file: File,
    readonly entries: ZipEntry[],
  ) {}

  static async open(file: File): Promise<ZipReader> {
    // The end-of-central-directory record is the last 22 bytes, plus a
    // comment of up to 64 KB.
    const tailStart = Math.max(0, file.size - (22 + 0xffff));
    const tail = await bytes(file, tailStart, file.size);
    let eocd = -1;
    for (let i = tail.byteLength - 22; i >= 0; i--) {
      if (tail.getUint32(i, true) === EOCD) {
        eocd = i;
        break;
      }
    }
    if (eocd < 0) throw new Error(`${file.name} is not a ZIP file, or it is damaged.`);

    let count = tail.getUint16(eocd + 10, true);
    let directorySize = tail.getUint32(eocd + 12, true);
    let directoryOffset = tail.getUint32(eocd + 16, true);

    if (count === 0xffff || directorySize === 0xffffffff || directoryOffset === 0xffffffff) {
      const locator = eocd - 20;
      if (locator < 0 || tail.getUint32(locator, true) !== ZIP64_LOCATOR) {
        throw new Error(`${file.name} is a large ZIP whose index could not be read.`);
      }
      const zip64Offset = u64(tail, locator + 8);
      const record = await bytes(file, zip64Offset, zip64Offset + 56);
      if (record.getUint32(0, true) !== ZIP64_EOCD) {
        throw new Error(`${file.name} is a large ZIP whose index could not be read.`);
      }
      count = u64(record, 32);
      directorySize = u64(record, 40);
      directoryOffset = u64(record, 48);
    }

    const directory = await bytes(file, directoryOffset, directoryOffset + directorySize);
    const entries: ZipEntry[] = [];
    let p = 0;
    for (let i = 0; i < count && p + 46 <= directory.byteLength; i++) {
      if (directory.getUint32(p, true) !== CENTRAL) break;
      const flags = directory.getUint16(p + 8, true);
      const method = directory.getUint16(p + 10, true);
      let compressedSize = directory.getUint32(p + 20, true);
      let size = directory.getUint32(p + 24, true);
      const nameLength = directory.getUint16(p + 28, true);
      const extraLength = directory.getUint16(p + 30, true);
      const commentLength = directory.getUint16(p + 32, true);
      let localHeaderOffset = directory.getUint32(p + 42, true);
      const nameBytes = new Uint8Array(directory.buffer, directory.byteOffset + p + 46, nameLength);
      const path = utf8.decode(nameBytes);

      // ZIP64 sizes and offset live in an extra field, present only for the
      // values that overflowed, in this order.
      let e = p + 46 + nameLength;
      const extraEnd = e + extraLength;
      while (e + 4 <= extraEnd) {
        const id = directory.getUint16(e, true);
        const length = directory.getUint16(e + 2, true);
        if (id === 0x0001) {
          let q = e + 4;
          if (size === 0xffffffff) {
            size = u64(directory, q);
            q += 8;
          }
          if (compressedSize === 0xffffffff) {
            compressedSize = u64(directory, q);
            q += 8;
          }
          if (localHeaderOffset === 0xffffffff) {
            localHeaderOffset = u64(directory, q);
          }
        }
        e += 4 + length;
      }

      if (!path.endsWith("/")) {
        entries.push({
          path,
          name: path.replace(/\\/g, "/").split("/").pop() ?? path,
          compressedSize,
          size,
          method,
          encrypted: (flags & 1) === 1,
          localHeaderOffset,
        });
      }
      p += 46 + nameLength + extraLength + commentLength;
    }
    return new ZipReader(file, entries);
  }

  /** One entry's contents, decompressed, as a stream. */
  async stream(entry: ZipEntry): Promise<ReadableStream<Uint8Array>> {
    if (entry.encrypted) throw new Error(`${entry.name} is password-protected.`);
    const header = await bytes(this.file, entry.localHeaderOffset, entry.localHeaderOffset + 30);
    if (header.getUint32(0, true) !== LOCAL) throw new Error(`${entry.name}: damaged ZIP entry.`);
    const start =
      entry.localHeaderOffset + 30 + header.getUint16(26, true) + header.getUint16(28, true);
    const raw = this.file.slice(start, start + entry.compressedSize).stream();
    if (entry.method === 0) return raw;
    if (entry.method === 8) {
      return raw.pipeThrough(new DecompressionStream("deflate-raw"));
    }
    throw new Error(`${entry.name} uses a compression method this browser cannot open.`);
  }

  /** One entry's contents as a Blob (for files small enough to upload whole). */
  async blob(entry: ZipEntry): Promise<Blob> {
    return new Response(await this.stream(entry)).blob();
  }
}
