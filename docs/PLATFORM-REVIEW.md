# Platform review — enhancement recommendations

A pass over the whole application: security, functionality, UI/UX, and
operations. Each finding says what I actually observed in the code, why it
matters, and what I would do.

Ordered by **what I would fix first**, not by category.

---

## Priority 1 — fix before real candidate data goes in

### 1.1 No endpoint returns a page — every list returns every row

**Observed:** 39 list endpoints across 16 route modules use
`response_model=list[...]` with no `limit`, `offset`, or cursor. `GET /candidates`
returns the entire candidate table. So do jobs, applications, audit logs, and the
new talent bench.

**Why it matters:** this is the single thing most likely to break the pilot. At
200 candidates nobody notices; at 5,000 the candidates page takes seconds and
ships megabytes to the browser on every visit. The audit log grows fastest of
all and is the one nobody thinks about until it times out.

**What I'd do:** add `limit`/`offset` with a sane default (50) and a hard
maximum, plus a total count in the response. Start with `candidates`,
`applications`, `audit-logs`, and `talent-bench`. Server-side search and
sorting has to come with it, because the current pages filter client-side over
the full array — which only works because the full array is present.

### 1.2 No rate limiting anywhere, including the public careers page

**Observed:** no rate-limiting middleware in the codebase. `POST /careers/{slug}/apply`
is unauthenticated, accepts a file upload, and has no CAPTCHA, no throttle, and
no size cap.

**Why it matters:** three concrete abuses. Someone can flood your database with
junk applications; each one triggers résumé parsing and an AI evaluation, so
they also spend your OpenRouter budget; and `POST /auth/login` can be brute-forced
without limit.

**What I'd do:** `slowapi` in front of the app. Strict limits on
`/auth/login`, `/auth/forgot-password`, and the public apply endpoint (say 5/minute
per IP); generous limits elsewhere. Add a CAPTCHA to the careers form before the
job board is publicised.

### 1.3 Résumé uploads are neither size- nor type-checked

**Observed:** `candidates.py` passes `file.content_type or "application/octet-stream"`
straight through to storage. No extension allowlist, no magic-byte check, no
size limit. The only upload limit in the codebase is the 5 MB cap I added to the
hotlist recipient import.

**Why it matters:** a 2 GB upload will happily fill the disk, and a file named
`resume.pdf` that is actually an HTML document with a script in it gets stored
and served back. Content-type comes from the client and cannot be trusted.

**What I'd do:** cap at ~10 MB, allowlist PDF/DOC/DOCX, and verify the magic
bytes rather than the declared type. Serve downloads with
`Content-Disposition: attachment` and a strict `Content-Type` so nothing renders
inline.

### 1.4 Tokens live in `localStorage`

**Observed:** `client.ts` stores the access and refresh tokens in
`localStorage`.

**Why it matters:** any XSS anywhere in the app — or in any dependency — can
read both tokens and exfiltrate a full session, including the long-lived refresh
token. `httpOnly` cookies are unreadable from JavaScript, which is the entire
point.

**What I'd do:** move the refresh token to an `httpOnly`, `Secure`, `SameSite=Lax`
cookie and keep only the short-lived access token in memory. This is a real piece
of work — it needs CSRF protection on state-changing requests once cookies are in
play — so it is a deliberate project, not a patch. Given a recruiting database of
personal data, I would schedule it.

### 1.5 Password policy is length-only

**Observed:** `Field(min_length=8)` on invite acceptance and password reset.
Nothing else — no complexity, no breach check, no rejection of `password123`.

**What I'd do:** raise the floor to 12 characters and check candidate passwords
against the Have I Been Pwned k-anonymity API (it never sees the password). Cheap
to add, and far more effective than complexity rules that push people toward
`Password1!`.

---

## Priority 2 — functionality gaps recruiters will hit in week one

### 2.1 No bulk actions anywhere

Every action is one row at a time. A recruiter screening 60 applicants cannot
reject 20 of them in one gesture, and cannot add 15 consultants to the bench
without 15 dialogs. Multi-select with bulk reject / bulk stage-move / bulk
add-to-bench is the highest-value UX work on this list.

### 2.2 No candidate or job import

Onboarding a new client means typing in their requisitions by hand, and there is
no way to bring an existing candidate spreadsheet in. The Excel machinery now
exists for hotlist recipients — the parsing, alias-matching, and per-row error
reporting are all reusable for a candidate importer.

### 2.3 Résumé content is not searchable

Candidate search covers name, email, and title. Parsed résumé text is stored in
`parsed_resumes.raw_text` but never indexed, so "who has mentioned Kafka?" is
unanswerable. Postgres full-text search over that column with a GIN index would
cover it without new infrastructure.

### 2.4 No saved views or filter persistence

Filters reset on every navigation. Recruiters work the same three or four slices
of the pipeline all day. Saved views — even just per-user, stored server-side —
would remove a lot of repeated clicking.

### 2.5 Interview scheduling has no calendar awareness

Interviews are a date/time field with no conflict detection, no invitation to the
panel, and no timezone display. A panel member gets no notification at all: the
system knows about the interview and never tells them. Given the mail
infrastructure is now in place, sending panel invitations is a small change with
a large effect.

### 2.6 Nothing tells anyone anything happened

There are no in-app notifications. Feedback requests, approval requests, and
stage changes are invisible unless someone happens to look. An activity feed plus
a digest email would close the loop.

---

## Priority 3 — UI/UX

### 3.1 Errors and successes are inconsistent

Some pages show inline red text, some show nothing, and destructive actions use
`window.confirm`. `sonner` is already a dependency but no `<Toaster />` is
mounted anywhere. Mounting it and standardising on toasts for success plus inline
messages for validation would make the app feel considerably more finished — and
replacing `window.confirm` with the existing `AlertDialog` component would stop
destructive actions looking like a browser popup.

### 3.2 Tables don't work on a laptop screen

The bench, jobs, and candidates grids have many columns and only some scroll
horizontally. Column visibility toggles, sticky first column, and remembered
column order would help. The reference product in your screenshot has exactly
these affordances, which is not a coincidence.

### 3.3 No empty-state guidance

Several pages show "No X found" with no next step. An empty state should say what
the thing is and offer the action — the hotlist page's empty state is the pattern
to copy.

### 3.4 Loading states are inconsistent

Some pages render skeletons, others a bare "Loading…". Skeletons that match the
eventual layout make the app feel faster than a spinner does.

### 3.5 Accessibility has not been looked at

Colour is doing work alone in several places — bench age, score pills, status
dots. Icon-only buttons in the hotlist recipient list have `title` but not all
have `aria-label`. Keyboard focus is visible, which is a good start. Worth one
deliberate pass: axe DevTools on each page would find most of it in an hour.

### 3.6 No dark mode

The token system is in place but there is no dark palette or toggle. Recruiters
stare at this all day; it comes up.

---

## Priority 4 — operations and data integrity

### 4.1 Soft deletes are inconsistent

Candidates and bench profiles soft-delete. Jobs, applications, hotlists, and
templates hard-delete. Deleting a hotlist destroys its send history, which is the
record of who you contacted — that is exactly the sort of thing someone asks
about six months later.

### 4.2 No optimistic concurrency

Two recruiters editing the same candidate silently overwrite each other; last
write wins with no warning. A version column checked on update, returning 409 on
conflict, would at least surface it.

### 4.3 The AI provider has no cost controls

Every résumé upload and application triggers a paid API call. There is no
per-organization budget, no monthly cap, no spend visibility, and no circuit
breaker if the provider starts erroring. At pilot volume this is pennies; it
scales linearly with use and nobody is watching it.

### 4.4 No monitoring or error tracking

Logs are structured JSON on stdout and nothing aggregates them. A failed
background job is invisible unless someone reads container logs. Sentry (or
equivalent) plus an uptime check on `/health` is an afternoon's work and is what
turns "a recruiter said it was broken" into an actionable report.

### 4.5 Test coverage is uneven

141 tests, concentrated on permissions, scoping, and the new bench/hotlist work —
genuinely the right places. But there are **no frontend tests at all**, and the
AI evaluation logic is only lightly covered. A handful of Playwright tests over
the critical paths (log in, post a job, apply, score, offer) would catch the
regressions that matter.

### 4.6 Two backend caveats worth knowing

- `conftest.py` has a session-wide autouse fixture that requires Postgres, so pure unit tests cannot run without a database. Making it opt-in would let logic tests run in milliseconds.
- Tests run against the same database as local development. Every test creates its own organization so they don't collide, but a `--create-db` style isolated test database would be safer.

---

## What is genuinely good, and worth protecting

Not everything needs changing, and it is worth being explicit about what already
works well:

- **The permission model.** Resource-plus-action pairs stored in the database, checked server-side on every request, with row-level scoping on top. This is better than most products at this stage, and it is the hardest thing to retrofit.
- **Multi-tenancy is consistent.** Every table carries `organization_id` and every query filters on it.
- **The audit trail is genuinely comprehensive** — 50+ recorded action types covering everything consequential.
- **Background work is correctly separated.** Résumé parsing, AI scoring, and email all run in the worker rather than blocking requests.
- **The AI is advisory, never automatic.** Nothing is auto-rejected, overrides are recorded, and the original output is preserved. That is the right ethical and legal posture for hiring software.
- **The UI is honest about what isn't built.** Unbuilt features say so rather than presenting dead controls. That is rarer than it should be, and it is why the pilot users will trust the parts that do work.

---

## If I had two weeks

1. **Pagination** on candidates, applications, audit logs, bench (1.1) — the one that stops the pilot scaling.
2. **Rate limiting plus upload validation** (1.2, 1.3) — small, and closes the open door on the public endpoint.
3. **Bulk actions** on applications and the bench (2.1) — the biggest day-to-day time saver.
4. **Toasts and consistent errors** (3.1) — cheap, and makes everything feel finished.
5. **Sentry and an uptime check** (4.4) — so you find out about problems before the recruiters tell you.

Then, as a scheduled project rather than a patch: **move tokens out of
`localStorage`** (1.4).
