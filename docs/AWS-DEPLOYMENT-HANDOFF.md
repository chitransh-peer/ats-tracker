# ATS Tracker — AWS deployment handoff

**Audience:** the engineer provisioning and deploying this on AWS.
**Assumes:** you know AWS. It assumes nothing about this codebase.

Everything here was verified against the repo. Resource figures are measured from a
running stack, not estimated.

---

## TL;DR

Five processes, one EC2 box, one RDS instance.

| Runs on | What |
| --- | --- |
| EC2 (Docker Compose) | FastAPI API, **background worker**, Next.js frontend, Redis, Caddy (TLS) |
| RDS | PostgreSQL 16 |
| S3 | Candidate résumés + database backups |
| SES | Password resets, invitations, candidate email |

Budget roughly **$45/month** in `ap-south-1`.

The one thing that catches people: **there is a background worker that must stay
running.** It is not optional — see [Architecture](#architecture).

---

## Deployment readiness

The repository is deployment-ready. What was previously missing is now in place:

| Item | State |
| --- | --- |
| `backend/Dockerfile` | Multi-stage, non-root (uid 10001), no compiler in the runtime layer, healthcheck on `/health` |
| `Frontend/Dockerfile` | Multi-stage, `next build` + standalone `node server.js`, non-root, **fails the build if `NEXT_PUBLIC_API_BASE_URL` is not supplied** |
| `docker-compose.prod.yml` | No source mounts, no `--reload`, `restart: unless-stopped` everywhere, Redis unpublished, worker pinned to 2 processes |
| `.dockerignore` (both projects) | `.env` and local artefacts excluded from build context |
| `deploy/Caddyfile` | TLS for both hostnames, security headers, `/docs` blocked at the proxy |
| S3 client | Works against real S3 with an IAM role and no stored keys |
| `/docs`, `/redoc`, `/openapi.json` | Disabled automatically when `APP_ENV=production` |
| `deploy/aws/01-create-database.sh` | Provisions RDS, subnet group, and a locked-down security group |
| `deploy/aws/02-init-schema.sh` | Applies migrations, seeds, and verifies |

### Verified end to end

Both images were built and run:

| Check | Result |
| --- | --- |
| Backend image builds | Yes — 1.06 GB (was 1.36 GB) |
| Frontend image builds | Yes — **395 MB (was 2.74 GB)** |
| Runs as non-root | Yes — uid 10001 in both |
| No compiler in the runtime layer | Confirmed absent |
| `.env` absent from image | Confirmed, both images |
| Frontend build fails without the API URL | Confirmed, with a readable error |
| Build-arg URL baked into served chunks | Confirmed in the running container |
| `GET /health` through the prod image | `{"status":"ok"}`, container reports healthy |
| Authenticated API through the prod image | Login plus reports, candidates, jobs all 200 |
| `/docs` and `/openapi.json` with `APP_ENV=production` | Both 404 |
| All frontend routes served | 200, including the new detail pages |
| Worker processes a task as non-root | Confirmed — a message reached `sent` |
| Backend test suite | **117 passed** |

Not exercised here, because they need real AWS: the two provisioning scripts
(both pass `bash -n`), SES delivery, and S3 against a real bucket.

## Architecture

```
                 Internet
                    │  443
              ┌─────▼─────┐
              │   Caddy   │  auto-TLS, reverse proxy
              └──┬─────┬──┘
     ats.…com    │     │   api.ats.…com
           ┌─────▼──┐ ┌▼───────┐
           │frontend│ │  api   │  FastAPI / uvicorn
           └────────┘ └─┬────┬─┘
                        │    │
              ┌─────────▼┐  ┌▼──────┐
              │  Redis   │  │  RDS  │  Postgres 16
              └────┬─────┘  └───┬───┘
                   │            │
              ┌────▼────────────▼───┐
              │       worker        │  dramatiq — MUST stay running
              └─────────┬───────────┘
                        │
                 ┌──────▼──────┐
                 │  S3    SES  │
                 └─────────────┘
```

### The worker is load-bearing

`dramatiq` runs four tasks. If the worker is not running, each fails **silently** — the
API returns success and the work never happens:

| Task | Symptom if the worker is down |
| --- | --- |
| `parse_resume_task` | Uploaded résumés are never parsed |
| `evaluate_application_task` | AI match score sits on "pending" forever |
| `send_email_task` | No password reset or invitation email is sent |
| `send_outbound_message_task` | Candidate messages stay at status `logged`, never `sent` |

This is why serverless (Lambda, Vercel, request-scoped App Runner) does not fit without
re-architecting. ECS Fargate is fine — run the worker as its own long-lived task.

### Notes on the API

- Base path is `/api/v1`. Health check is **`GET /health`** — unauthenticated, returns `{"status":"ok"}`.
- All frontend pages are client-rendered shells. **The browser calls the API directly**, so the API must be publicly reachable over HTTPS. An HTTPS page cannot call an HTTP API — the browser blocks it as mixed content.
- Auth is JWT bearer tokens held in `localStorage`, with a refresh endpoint. No server-side sessions, so no sticky sessions are needed and the API scales horizontally.

---

## AWS resources to provision

| # | Resource | Spec | Notes |
| --- | --- | --- | --- |
| 1 | EC2 | **`t4g.medium`** (2 vCPU ARM, 4 GB), 30 GB gp3, Ubuntu 24.04 | See sizing below. ARM — images build natively on Graviton |
| 2 | RDS PostgreSQL | **`db.t4g.micro`**, **Postgres 16**, 20 GB gp3, private subnet | No extensions required — verified across all 10 migrations |
| 3 | S3 bucket | Block all public access, versioning on | Candidate résumés and documents |
| 4 | S3 bucket | Lifecycle expiry ~30 days | Database backups |
| 5 | SES | Domain identity + DKIM, **production access requested** | Sandbox only sends to verified addresses |
| 6 | IAM instance role | `s3:GetObject/PutObject/ListBucket` on bucket 3, `ses:SendRawEmail` | Avoids static keys in `.env` |
| 7 | Security groups | 2 — see below | |
| 8 | Elastic IP | 1 | Free while attached |
| 9 | DNS | 2 A records | Route 53 or existing provider |

**Redis stays as a container on the EC2 box.** It is only a task broker and uses ~12 MB.
ElastiCache would add ~$12/month for no benefit at this scale.

### Sizing evidence

Measured with `docker stats` on the running stack:

```
worker    1.43 GiB   ← dramatiq forks one process per CPU (16 on the dev machine)
api        208 MiB
minio      108 MiB   ← replaced by S3 on AWS
db          62 MiB   ← replaced by RDS on AWS
redis       12 MiB
          ─────────
          ~1.85 GiB
```

The worker figure is process count, not real need. **Pin it** — the dev team should set
`dramatiq app.workers.tasks --processes 2 --threads 4`. Any process that scores an
application loads a ~400 MB ONNX embedding model into its own memory, so process count
multiplies straight into RAM.

Expect ~1.3 GB after pinning. Therefore:

- `t4g.micro` / `t3.micro` (1 GB) — **too small**, including free-tier instances
- `t4g.small` (2 GB) — tight; workable only with `EMBEDDINGS_ENABLED=false`
- **`t4g.medium` (4 GB) — recommended**

---

## Networking

Two security groups:

| Group | Inbound | Source |
| --- | --- | --- |
| `ats-web` (EC2) | 22 | Office/VPN CIDR **only** |
| | 80, 443 | `0.0.0.0/0` |
| `ats-db` (RDS) | 5432 | `ats-web` security group **only** |

**Never expose 5432 or 6379 publicly.** `docker-compose.prod.yml` already handles this:
Redis uses `expose` rather than `ports` so only sibling containers reach it, and Postgres
is not in the file at all (RDS replaces it). Only Caddy publishes ports.

### TLS

Two hostnames, both required:

```
ats.<domain>       → frontend  (port 3000)
api.ats.<domain>   → api       (port 8000)
```

`deploy/Caddyfile` is committed and reads the two hostnames from `APP_DOMAIN` and
`API_DOMAIN`. It also sets HSTS and related headers, and returns 404 for `/docs`,
`/redoc`, and `/openapi.json` as a second line of defence.

**Both hostnames must already resolve to the host before first start**, or the ACME
challenge fails and no certificate is issued.

ALB + ACM works too, and costs ~$18/month more.

---

## Configuration contract

The backend reads **39 environment variables** from `backend/.env`. Most keep their
defaults. These are the ones needing real values.

### You will have these after provisioning

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://<user>:<pass>@<rds-endpoint>:5432/ats_tracker` |
| `STORAGE_BUCKET` | résumé bucket name |
| `STORAGE_REGION` | e.g. `ap-south-1` |
| `SMTP_HOST` | `email-smtp.<region>.amazonaws.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USE_TLS` | `true` |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | SES **SMTP** credentials (not IAM keys) |

> The driver prefix `postgresql+psycopg://` matters — this uses psycopg 3. A plain
> `postgres://` URL will fail.

### Generate these — the committed defaults are literally `change-me`

| Variable | How |
| --- | --- |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `DEFAULT_SUPER_ADMIN_PASSWORD` | A real password. This becomes the first login. |

### Must be right or the deployment misbehaves

| Variable | Value | Consequence if wrong |
| --- | --- | --- |
| `APP_BASE_URL` | `https://ats.<domain>` | Builds links **inside** reset/invitation email. Wrong value = every emailed link is dead. |
| `CORS_ORIGINS` | `https://ats.<domain>` | Wrong value = browser blocks every API call. |
| `APP_ENV` | `production` | Also hard-disables the reset-token escape hatch. |
| `EXPOSE_PASSWORD_RESET_TOKEN` | `false` | If true, returns a live credential-reset token over the API. |
| `MAIL_FROM_EMAIL` | An SES-verified address | Sending fails otherwise. |

### Leave empty on purpose

```
STORAGE_ENDPOINT_URL=      # must be ABSENT for real S3, not blank
STORAGE_ACCESS_KEY=        # empty → falls back to the IAM instance role
STORAGE_SECRET_KEY=
```

This depends on gap #4 being fixed. If it is not, you will need static IAM keys here.

### AI provider — confirm with the dev team

```
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=<key>
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
```

**This bills per token** on every résumé parsed and application scored. It is the only
usage-priced component. Confirm which key and model to use, and whether it should be a
`:free` model variant.

`EMBEDDINGS_ENABLED=true` downloads a ~400 MB model on first use into
`EMBEDDINGS_CACHE_DIR`. **Mount that path as a named Docker volume**, or it re-downloads
every time a container is recreated.

### Frontend — build-time, not runtime

```
NEXT_PUBLIC_API_BASE_URL=https://api.ats.<domain>/api/v1
NEXT_PUBLIC_CAREERS_ORG_SLUG=peer-consulting
```

**Both are inlined into the JavaScript bundle at build time.** Setting them as container
environment variables has no effect on a production build — they must be build args, and
changing either needs a rebuild, not a restart.

`NEXT_PUBLIC_CAREERS_ORG_SLUG` must equal the backend's `DEFAULT_ORG_SLUG`. If they
diverge, the public careers page returns nothing, with no visible error.

---

## Deploy

Two helper scripts live in `deploy/aws/`. Both are idempotent.

### Step 1 — the database (from your workstation)

```bash
export AWS_REGION=ap-south-1
export APP_SECURITY_GROUP_ID=sg-xxxxxxxx      # the EC2 instance's security group
./deploy/aws/01-create-database.sh
```

Creates a DB subnet group, a security group that admits **only** the app's security
group on 5432, and an encrypted `db.t4g.micro` running Postgres 16 with 14-day
automated backups and deletion protection. It generates the master password,
waits for the instance, then prints the exact `DATABASE_URL` line to paste into
`backend/.env`.

Override any default via environment variable: `DB_IDENTIFIER`,
`DB_INSTANCE_CLASS`, `DB_STORAGE_GB`, `DB_BACKUP_RETENTION_DAYS`, and so on.

**Store the printed password immediately** — it is not recoverable from AWS.

### Step 2 — the application (on the EC2 host)

```bash
git clone <repo> && cd ATS
cp backend/.env.example backend/.env
$EDITOR backend/.env                       # the contract above, incl. DATABASE_URL

# Domains used by both the build and the Caddy config
export APP_DOMAIN=ats.<domain>
export API_DOMAIN=api.ats.<domain>
export NEXT_PUBLIC_API_BASE_URL=https://api.ats.<domain>/api/v1

docker compose -f docker-compose.prod.yml build
```

The frontend build **fails fast** if `NEXT_PUBLIC_API_BASE_URL` is unset, rather
than quietly baking in a localhost URL.

### Step 3 — schema and seed

```bash
./deploy/aws/02-init-schema.sh
```

Checks connectivity, applies `alembic upgrade head`, runs `python -m scripts.seed`,
then verifies that tables, roles, permissions, users, organizations, and pipeline
stages are all populated — and fails loudly if any came back empty.

### Step 4 — start and smoke test

```bash
docker compose -f docker-compose.prod.yml up -d
curl -fsS https://api.ats.<domain>/health     # {"status":"ok"}
```

### Why step 3 is not optional

`alembic upgrade head` creates the schema. `python -m scripts.seed` creates roles,
the permission matrix, the default organization, pipeline stages, and the
super-admin user.

**There is no startup hook that does either.** Skip the seed and the app starts
cleanly with no admin account and no pipeline stages — it will look broken with
no error to explain why.

## Verification

Do these in order. Step 6 is the one that matters — it exercises the worker, S3, and the
AI provider together, which is where problems actually surface.

1. `GET /health` returns `{"status":"ok"}`
2. Log in as `DEFAULT_SUPER_ADMIN_EMAIL` — **change the password immediately**
3. **Settings → Integrations** shows email **Connected** (it reads live SMTP config)
4. **Settings → AI preferences** shows the expected provider and model
5. Invite a user; confirm the email arrives **and the link resolves** (proves `APP_BASE_URL`)
6. Post a job → apply via `/careers` with a PDF résumé → confirm an AI score appears within about a minute
7. `docker compose logs worker` shows tasks completing, not retrying

If step 6 stalls at "pending", check the worker logs first — it is almost always the
worker, Redis, or the AI key.

---

## Shipping updates later

```bash
git pull
docker compose -f docker-compose.prod.yml build \
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.ats.<domain>/api/v1
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml up -d
```

Two things to remember:

- **Run `alembic upgrade head` on every deploy.** Migrations are not automatic.
- **Re-run `python -m scripts.seed` when the dev team says to.** New permissions are added
  to a matrix in code and only reach the database through seeding — a restart does not
  apply them. This has already happened once, when a recruiter permission was added.

---

## Backups

Nothing is configured in the repo. Two things hold state: **RDS** and the **résumé S3
bucket**.

- Enable **RDS automated backups**, 7–14 day retention. Highest-value item on this page.
- Enable **S3 versioning** on the résumé bucket.
- Optional belt-and-braces nightly logical dump:

```bash
docker compose -f docker-compose.prod.yml exec -T api \
  pg_dump "$DATABASE_URL" | gzip | aws s3 cp - s3://<backup-bucket>/db-$(date +%F).sql.gz
```

Then **restore one into a scratch database and log in against it.** An untested backup is
a guess.

---

## Ops notes

- **Logs** are structured JSON on stdout — `docker compose logs -f api worker`. Ship to CloudWatch if you want retention.
- **`/docs` and `/openapi.json` are publicly exposed with no authentication.** These are FastAPI defaults and nothing in the code disables them. Decide whether to block them at Caddy or have the dev team disable them when `APP_ENV=production`.
- **Secrets** currently live in `backend/.env` on the box. Fine for a pilot; consider SSM Parameter Store or Secrets Manager if that does not meet policy.
- **Restart policy** — confirm the production compose file sets `restart: unless-stopped` on every service. The dev file sets none.
- **Timezone** — the app stores UTC throughout. Do not change the host timezone.
- **The `model_cache` volume and the non-root user.** The containers run as uid 10001. A *fresh* Docker named volume inherits `appuser` ownership from the image, so a new deployment is fine — verified. But a volume created while a container ran as root stays root-owned, and the app then cannot cache the embeddings model. It degrades quietly to no semantic scoring rather than crashing, so it is easy to miss. If you ever see permission errors on `/app/.model_cache`, stop the services, `docker volume rm <project>_model_cache`, and start again; the model re-downloads on first use.

---

## Known functional gaps

Not bugs — unbuilt. Listed so you do not chase them:

- Pipeline stages are read-only in the UI. Stage automation, per-org AI model selection, data-retention rules, and GDPR erasure are not implemented.
- No Slack, calendar, DocuSign, or job-board integrations.
- Candidates apply through `/careers` but cannot log in to track status.
- Offers have an approval flow but no e-signature step.
- Reports and dashboards render empty until real data flows through. That is correct behaviour, not a failure.

---

## Open questions for the dev team

Worth resolving before provisioning:

1. Confirm the image builds succeed in your environment — see [Deployment readiness](#deployment-readiness).
2. Which AWS region? It determines the SES SMTP host and the RDS endpoint.
3. Which domain and subdomains, and who controls the DNS zone?
4. OpenRouter key and model — or switch to a free model or self-hosted Ollama?
5. Keep `EMBEDDINGS_ENABLED=true`? It is the reason for the 4 GB instance.
6. Should `/docs` be publicly reachable?
