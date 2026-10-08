// Time zones an interview can be scheduled in. Mirrors INTERVIEW_TIMEZONES in
// backend/app/schemas/interview.py.
export const INTERVIEW_TIMEZONES = [
  { value: "America/New_York", label: "Eastern Time (US)" },
  { value: "America/Chicago", label: "Central Time (US)" },
  { value: "America/Denver", label: "Mountain Time (US)" },
  { value: "America/Phoenix", label: "Arizona (US)" },
  { value: "America/Los_Angeles", label: "Pacific Time (US)" },
  { value: "America/Anchorage", label: "Alaska (US)" },
  { value: "Pacific/Honolulu", label: "Hawaii (US)" },
  { value: "America/Toronto", label: "Eastern Time (Canada)" },
  { value: "America/Vancouver", label: "Pacific Time (Canada)" },
  { value: "Asia/Kolkata", label: "India Standard Time" },
  { value: "Europe/London", label: "UK Time" },
  { value: "Australia/Sydney", label: "Sydney" },
  { value: "UTC", label: "UTC" },
] as const;

const SUPPORTED = new Set<string>(INTERVIEW_TIMEZONES.map((z) => z.value));

/** The viewer's own zone when it is one we offer, else US Eastern. */
export function defaultTimezone(): string {
  try {
    const own = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (own === "Asia/Calcutta") return "Asia/Kolkata";
    if (SUPPORTED.has(own)) return own;
  } catch {
    // Fall through to the default.
  }
  return "America/New_York";
}

export function timezoneLabel(zone: string | null | undefined): string {
  return INTERVIEW_TIMEZONES.find((z) => z.value === zone)?.label ?? zone ?? "";
}

/** Milliseconds `zone` is ahead of UTC at the instant `utcMs`. */
function offsetMs(utcMs: number, zone: string): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: zone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(new Date(utcMs));
  const get = (type: string) => Number(parts.find((p) => p.type === type)?.value);
  const asUtc = Date.UTC(
    get("year"),
    get("month") - 1,
    get("day"),
    get("hour"),
    get("minute"),
    get("second"),
  );
  return asUtc - (utcMs - (utcMs % 1000));
}

/**
 * The UTC instant of a wall-clock time ("2026-10-08T09:30", as a
 * datetime-local input gives it) in `zone`, so 9:30 IST means 9:30 in India
 * whatever zone the scheduler's own browser is in.
 */
export function zonedToUtcIso(local: string, zone: string): string {
  const [date, time = "00:00"] = local.split("T");
  const [y, m, d] = date.split("-").map(Number);
  const [hh, mm] = time.split(":").map(Number);
  const wall = Date.UTC(y, m - 1, d, hh, mm);
  // Two passes settle the offset across a daylight-saving change.
  let utc = wall - offsetMs(wall, zone);
  utc = wall - offsetMs(utc, zone);
  return new Date(utc).toISOString();
}

/** "Thu, Oct 8, 9:30 AM IST" — an instant shown in a given zone. */
export function formatInZone(iso: string, zone: string): string {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: zone,
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(iso));
}

/** The same instant in the viewer's own zone, or null when that is `zone`. */
export function formatForViewer(iso: string, zone: string | null | undefined): string | null {
  let own: string;
  try {
    own = Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return null;
  }
  if (!zone || own === zone || (own === "Asia/Calcutta" && zone === "Asia/Kolkata")) return null;
  return formatInZone(iso, own);
}
