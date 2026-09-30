# Load test

Checks that the app stays fast at production volume with a full team working at once.

**Target:** with 20 recruiters working at the same time, against 100,000 candidates, 50,000 vendors, 10,000 clients and 120,000 applications, every page's 95th percentile load time is under 1 second and no API call fails.

## What it measures

Each simulated recruiter signs in, then opens pages at random with a 1–3 second pause between them, for as long as you choose. A page is every API call that page makes when it opens, sent together as the browser sends them (six at a time). Its time runs from the first request going out to the last response coming back. It does not include downloading the page's JavaScript, which comes from the frontend service and is cached after the first visit.

The 21 pages covered are the dashboard, the candidates, vendors, clients, jobs and applications lists (each plain and searched), candidate detail, job detail, the pipeline for all jobs and for one job, interviews, offers, onboarding, hotlists, reports, and the job and application pickers.

The result is a table showing each page's median, 95th percentile and slowest load, plus the slowest individual API calls. The run fails if any page misses the target.

## On the live setup (GitHub Actions)

The data goes into a separate organization called **Load Test**, whose recruiters can see only that organization. Nobody using the real organization sees any of it, and cleanup removes all of it.

1. Add a repository secret `LOADTEST_PASSWORD` (12+ characters). The test recruiters are created with this password.
2. Deploy the backend from a commit that includes `backend/scripts/loadtest_*.py`.
3. **Actions → Load test → Run workflow**, then run these steps in order:
   - `seed`: creates the data. It runs as a one-off Cloud Run Job, because the database is reachable only from inside Cloud Run. It takes a few minutes.
   - `run`: the test itself. Defaults are 20 users for 300 seconds. The result table appears on the run's summary page.
   - `cleanup`: deletes the Load Test organization and everything in it, then removes the job.

The seeded rows (about 700,000 in all) share the production database until cleanup. They take some disk space, and the database does a little more work while the test runs.

## Locally

```sh
cd backend
python -m scripts.loadtest_seed                  # LOADTEST_PASSWORD set; --scale 0.1 for a tenth
uvicorn app.main:app --port 8765 --no-proxy-headers
python -m scripts.loadtest_run --base-url http://127.0.0.1:8765/api/v1 --duration 300
python -m scripts.loadtest_seed --delete
```

## Latest result (local, 30 Sep 2026)

This run used one server process and Postgres 16 on a Windows laptop, at the full volume above, with 20 users for 300 seconds. It made 8,703 API calls with none failing.

The slowest pages at the 95th percentile were Reports at 184 ms, the pipeline for all jobs at 181 ms and the dashboard at 171 ms. Every other page came in under 135 ms. **PASS.** A handful of single page loads took 2–3 s. They happened at the same moments in every run, which fits a server warming up, not a steady-state cost.

The first run failed: 40 calls failed and pages stalled for 16–18 seconds. That exposed a thread-and-connection deadlock under concurrent load. `backend/app/core/db_gate.py` describes it and fixes it. A local run is not the live setup (Cloud Run has 1 vCPU per instance and Cloud SQL is a separate machine), so the live run is still the one that counts.
