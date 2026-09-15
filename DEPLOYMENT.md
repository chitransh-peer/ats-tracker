# Deployment plan — recruiter pilot

Target: one organization, a handful of recruiters, zero recurring spend.

Everything below is scoped to the current codebase. Measured figures come from the
running dev stack, not estimates.

---

## 1. The "free" constraint, honestly

A VPS is not free. Two paths actually cost nothing:

| Need     | Free option                                                          | Catch                                                                       |
| -------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Compute  | **Oracle Cloud Always Free** — 4 ARM vCPU, 24 GB RAM, 200 GB block    | Capacity for ARM instances is often unavailable; retry or pick another region |
| Compute  | An existing office machine / on-prem server                          | Needs a static route in from the internet, and someone to keep it powered    |
| Email    | **The existing `peer-consulting.com` mailbox** (already paid for)     | ~2,000 recipients/day cap; not built for bulk outreach                       |
| Email    | **Brevo** free tier — 300 emails/day, forever, no card               | Their branding on the footer of free-plan mail                               |
| Database | Postgres in Compose on the same box                                  | Backups are yours to run (§6)                                                |
| Database | **Neon** / **Supabase** free Postgres                                | Free tiers sleep when idle and cap storage                                   |
| AI       | OpenRouter `:free` model variants, or self-hosted Ollama on the box   | Free OpenRouter models are rate-limited; Ollama on 4 ARM cores is slow       |

### Why the common free tiers won't work

Measured memory on the current stack:

```
worker    1.43 GiB   ← dramatiq forks one process per CPU (16 here)
backend    208 MiB
minio      108 MiB
db          62 MiB
redis        12 MiB
mailpit      17 MiB
          ─────────
total     ~1.85 GiB   (before the frontend, which isn't containerised for prod yet)
```

That rules out AWS `t2.micro`, GCP `e2-micro`, and similar 1 GB tiers. It fits Oracle's
24 GB ARM box with room to spare.

The worker figure is inflated by process count, not real need — see §3.6.

### AI cost is the one thing to watch

`AI_PROVIDER=openrouter` with `OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct` bills
per token. It is the only component that spends money on every résumé parsed and every
application scored. Switch to a `:free` variant or self-host Ollama before the pilot, or
this stops being a zero-spend deployment.

---

## 2. What blocks deploying today

Five things in the repo are development-only and must change first.

### 2.1 The frontend image runs a dev server

`Frontend/Dockerfile` ends in `CMD ["npm", "run", "dev"]`. That is the Next.js dev
server: slow, unminified, and not meant to face the internet. It needs a multi-stage
build that runs `next build` and serves with `next start`.

**`NEXT_PUBLIC_API_BASE_URL` is inlined into the JavaScript bundle at build time**, not
read at runtime. Setting it in the container environment (as `docker-compose.yml` does
today) has no effect on a production build. It must be passed as a build argument, which
means the image is environment-specific.

### 2.2 The backend image ships a compiler and runs as root

`backend/Dockerfile` installs `gcc` and `libpq-dev` and never removes them, and defines
no unprivileged user. Both are straightforward to fix in a multi-stage build.

Neither project has a `.dockerignore`, so `.venv/`, `.next/`, `node_modules/`, and
`.env` are all being copied into build context and image layers. **`.env` in an image
layer means committed secrets** — add these before building anything you push to a
registry.

### 2.3 Compose is wired for development

`docker-compose.yml` bind-mounts source into every service, runs uvicorn with
`--reload`, sets no `restart:` policy, and publishes Postgres, Redis, and MinIO on
`0.0.0.0`. On a public box those three ports must not be exposed. This needs a separate
`docker-compose.prod.yml`.

### 2.4 Migrations and seeding do not run themselves

`app/main.py` has no startup hook. Ten Alembic revisions exist but nothing applies them,
and roles/permissions/the super admin come from `python -m scripts.seed`, which is
manual. Both must be explicit release steps:

```bash
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m scripts.seed
```

`scripts/seed.py` is idempotent, so re-running is safe. Note that seeding is also what
grants the recruiter `template:update` permission added this week — without this step,
recruiters cannot edit email templates.

### 2.5 The default secrets are the literal string "change-me"

`backend/.env.example` ships `JWT_SECRET=change-me-in-production-...` and
`DEFAULT_SUPER_ADMIN_PASSWORD=change-me-in-production`. Anyone who reads the public repo
can forge a token against a deployment that kept them.

---

## 3. Pre-flight checklist

- [ ] **3.1** Production `Frontend/Dockerfile` — multi-stage, `next build` + `next start`, `NEXT_PUBLIC_API_BASE_URL` as build arg. Consider `output: "standalone"` in `next.config.ts` for a much smaller image.
- [ ] **3.2** Production `backend/Dockerfile` — build stage for wheels, slim runtime, non-root `USER`.
- [ ] **3.3** `.dockerignore` in both projects (`.env`, `.venv`, `node_modules`, `.next`, `__pycache__`, `.git`).
- [ ] **3.4** `docker-compose.prod.yml` — no source mounts, no `--reload`, `restart: unless-stopped`, and `db`/`redis`/`minio` bound to `127.0.0.1` only.
- [ ] **3.5** Drop the `mailpit` service from the production file. It is a dev mail catcher that swallows everything sent to it.
- [ ] **3.6** Pin the worker: `dramatiq app.workers.tasks --processes 2 --threads 4`. The default forks per-CPU, and any process that scores an application loads the embeddings model into its own memory. This is where the 1.43 GiB goes.
- [ ] **3.7** Rotate `JWT_SECRET` (`openssl rand -hex 32`) and set a real `DEFAULT_SUPER_ADMIN_PASSWORD`. Rotating `JWT_SECRET` invalidates every existing session, which is what you want on first deploy.
- [ ] **3.8** `APP_ENV=production`, `EXPOSE_PASSWORD_RESET_TOKEN=false`. The token escape hatch is refused when `APP_ENV=production` regardless of the flag, but set both so intent is explicit.
- [ ] **3.9** `CORS_ORIGINS=https://ats.yourdomain.com` and `APP_BASE_URL=https://ats.yourdomain.com`. `APP_BASE_URL` builds the links inside password-reset and invitation email — if it stays `localhost`, every emailed link is dead.
- [ ] **3.10** SMTP credentials set and confirmed (§4).
- [ ] **3.11** MinIO root credentials changed from `ats-minio` / `ats-minio-secret`.
- [ ] **3.12** Postgres password changed from `ats` / `ats`.
- [ ] **3.13** Backups scheduled (§6).

---

## 4. Email setup

The mailer is provider-agnostic SMTP, so both free options are pure configuration.

### Option A — existing company mailbox (no new accounts)

Google Workspace requires an **app password**, not the account password, and 2FA must be
on for the account.

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=ats@peer-consulting.com
SMTP_PASSWORD=<16-char app password>
MAIL_FROM_EMAIL=ats@peer-consulting.com
MAIL_FROM_NAME=Peer Consulting Recruiting
```

Best for internal mail (resets, invitations). I would not push candidate outreach
volume through it.

### Option B — Brevo (free forever, 300/day)

```env
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=<brevo login>
SMTP_PASSWORD=<brevo SMTP key>
MAIL_FROM_EMAIL=no-reply@peer-consulting.com
MAIL_FROM_NAME=Peer Consulting Recruiting
```

### Deliverability — do this regardless of provider

Add **SPF**, **DKIM**, and a **DMARC** record for the sending domain. Without them,
candidate-facing mail from a new sender lands in spam often enough to look like the
product is broken. Both providers walk you through the DNS records.

### Verifying after deploy

Settings → Integrations reads `GET /settings/email-status` and shows the live SMTP host,
from-address, and the base URL links are built from. If it says **Not connected**, the
app is recording outreach but transmitting nothing.

---

## 5. Deploy sequence

```bash
# 0. On the box: install Docker + compose plugin, create a non-root user, enable ufw
#    (allow 22/80/443 only), point DNS A records at the host.

# 1. Clone and configure
git clone <repo> && cd ATS
cp backend/.env.example backend/.env
$EDITOR backend/.env          # everything from §3.7-3.12

# 2. Build (API URL is baked in here, not at runtime)
docker compose -f docker-compose.prod.yml build \
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.ats.yourdomain.com/api/v1

# 3. Data services first, so migrations have something to talk to
docker compose -f docker-compose.prod.yml up -d db redis minio

# 4. Schema, then seed data
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.prod.yml run --rm backend python -m scripts.seed

# 5. Application
docker compose -f docker-compose.prod.yml up -d backend worker frontend caddy

# 6. Smoke test
curl -fsS https://api.ats.yourdomain.com/health          # {"status":"ok"}
```

Then, in the browser:

1. Log in as the super admin, **change the password immediately**.
2. Settings → Integrations shows email **Connected**.
3. Invite a real recruiter; confirm the invitation email arrives and the link resolves.
4. Run a forgot-password on that recruiter and confirm the reset works end to end.
5. Settings → AI preferences shows the provider and model you expect.
6. Post a job, apply through `/careers`, confirm the AI score appears (this exercises the
   worker, MinIO, and the AI provider in one shot).

TLS via Caddy needs about six lines:

```
ats.yourdomain.com     { reverse_proxy frontend:3000 }
api.ats.yourdomain.com { reverse_proxy backend:8000 }
```

Certificates are obtained and renewed automatically.

---

## 6. Backups

Nothing is configured today. Two things hold state: Postgres and MinIO.

```bash
# Nightly, kept 14 days
docker compose exec -T db pg_dump -U ats ats_tracker | gzip > "backup-$(date +%F).sql.gz"
```

Put it in cron, and **copy it off the box** — a backup on the same disk does not survive
losing the disk. Résumés live in MinIO, so `minio_data` needs the same treatment.

Then actually restore one into a scratch database. An untested backup is a guess.

---

## 7. Known gaps to tell the pilot users

Set expectations before they find these:

- **Settings** — pipeline stages are read-only; stage automation, per-org AI model choice, retention windows, and GDPR erasure workflows are unbuilt and labelled as such in the UI.
- **Integrations** — Slack, calendar sync, DocuSign, and job-board posting are not connected.
- **No candidate portal** — candidates apply through `/careers` but cannot log in to track status.
- **Offers** — the approval flow works; there is no e-signature step.
- **Reports** — charts render empty until real data flows through; that is accurate, not broken.

---

## 8. If you outgrow the single box

The migration path, in the order it usually matters:

1. **Managed Postgres** (RDS / Neon paid) — removes the backup burden and gives point-in-time recovery. Do this first.
2. **S3 or Cloudflare R2** in place of MinIO — the storage layer is already S3-compatible (`boto3`), so this is an env-var change.
3. **SES** for email once volume outgrows 300/day.
4. **Separate worker host** when AI scoring starts competing with request latency.
5. Container orchestration (ECS/Fly) only when one box genuinely isn't enough — it buys less than the four items above.
