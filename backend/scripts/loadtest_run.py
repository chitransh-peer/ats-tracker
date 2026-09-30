"""Load test: recruiters using the app at once, timed page by page.

Each virtual recruiter signs in, then loops through the pages a recruiter
uses, pausing 1-3 seconds between them. A "page" is every API call that page
makes on load, sent together the way the browser sends them; its time is
from the first request out to the last response in. Afterwards a table shows
each page's median, 95th percentile and slowest time, and the run fails
(exit 1) if any page's 95th percentile is over the target or any call failed.

Sign in as the recruiters scripts/loadtest_seed.py creates:

  LOADTEST_PASSWORD=... python -m scripts.loadtest_run --base-url https://.../api/v1

Options: --users 20 --duration 300 --target-ms 1000 --report report.md
"""

import argparse
import asyncio
import os
import random
import statistics
import sys
import time
from collections import defaultdict

import httpx

from scripts.loadtest_common import RECRUITER_COUNT, RECRUITER_EMAIL

# A browser opens about six connections per host; the calls of one page
# queue behind that many at a time.
_PER_PAGE_CONCURRENCY = 6
_SEARCH_TERMS = ["Sharma", "Patel", "Chen", "Engineer", "Analyst", "Smith", "Corp", "Staffing"]

_REPORTS = [
    "/reports/funnel",
    "/reports/source-effectiveness",
    "/reports/aging-jobs",
    "/reports/hiring-trend",
    "/reports/score-distribution",
    "/reports/offer-metrics",
    "/reports/time-to-fill",
    "/reports/executive-dashboard",
    "/reports/recruiter-performance",
]


def _pages(sample: dict, rng: random.Random) -> dict[str, list[str]]:
    """Page name -> the calls it makes on load, as the frontend makes them."""
    term = rng.choice(_SEARCH_TERMS)
    job = rng.choice(sample["jobs"])
    candidate = rng.choice(sample["candidates"])
    return {
        "Dashboard": [
            "/auth/me",
            "/reports/recruiter-dashboard",
            *_REPORTS,
            "/candidates?limit=6",
            "/interviews?upcoming=true&limit=5",
        ],
        "Candidates": ["/candidates?limit=50&offset=0"],
        "Candidates (search)": [f"/candidates?limit=50&search={term}"],
        "Candidate detail": [
            f"/candidates/{candidate}",
            f"/candidates/{candidate}/notes",
            f"/applications?candidate_id={candidate}",
            f"/interviews?candidate_id={candidate}&limit=200",
            "/pipeline/stages",
        ],
        "Vendors": ["/vendors?limit=50&offset=0", "/vendors/summary"],
        "Vendors (search)": [f"/vendors?limit=50&search={term}"],
        "Clients": ["/clients?limit=50&offset=0", "/clients/summary"],
        "Clients (search)": [f"/clients?limit=50&search={term}"],
        "Jobs": ["/jobs?limit=50&offset=0", "/jobs/summary"],
        "Jobs (search)": [f"/jobs?limit=50&search={term}", "/jobs/summary"],
        "Job detail": [
            f"/jobs/{job}",
            f"/jobs/{job}/submissions",
            f"/jobs/{job}/notes",
            f"/jobs/{job}/documents",
        ],
        "Applications": ["/applications?page_size=50&offset=0", "/pipeline/stages"],
        "Applications (search)": [f"/applications?page_size=50&search={term}", "/pipeline/stages"],
        "Pipeline (all jobs)": ["/pipeline/stages", "/pipeline/board"],
        "Pipeline (one job)": ["/pipeline/stages", f"/pipeline/board?job_id={job}"],
        "Interviews": ["/interviews?limit=50&offset=0", "/interviews/summary"],
        "Offers": ["/offers?limit=50&offset=0", "/offers/summary"],
        "Onboarding": ["/onboarding?limit=20&offset=0", "/onboarding/summary"],
        "Hotlists": [
            "/hotlists?limit=50",
            "/hotlists?limit=1",
            "/hotlists?limit=1&status=Draft",
            "/hotlists?limit=1&status=Sent",
        ],
        "Reports": _REPORTS,
        "Picker search": [f"/jobs/options?search={term}", f"/applications/options?search={term}&status=Active"],
    }


class Results:
    def __init__(self) -> None:
        self.page_ms: dict[str, list[float]] = defaultdict(list)
        self.errors: dict[str, list[str]] = defaultdict(list)
        self.call_ms: dict[str, list[float]] = defaultdict(list)
        self.calls = 0


async def _login(client: httpx.AsyncClient, email: str, password: str) -> str:
    # Sign-in is limited to 10 a minute per address, and every recruiter here
    # signs in from the same one, so a 429 means wait and try again.
    for _attempt in range(20):
        response = await client.post("/auth/login", json={"email": email, "password": password})
        if response.status_code == 429:
            await asyncio.sleep(7)
            continue
        response.raise_for_status()
        return response.json()["access_token"]
    raise RuntimeError(f"Could not sign in as {email}")


async def _load_page(client, headers, name, calls, results: Results) -> None:
    gate = asyncio.Semaphore(_PER_PAGE_CONCURRENCY)

    async def call(path: str) -> None:
        async with gate:
            try:
                sent = time.perf_counter()
                try:
                    response = await client.get(path, headers=headers)
                except (httpx.RemoteProtocolError, httpx.ReadError, httpx.WriteError):
                    # The server closed an idle keep-alive connection just as
                    # it was reused. A browser retries a GET on a fresh one
                    # without telling anyone, so this does the same, once.
                    response = await client.get(path, headers=headers)
                results.call_ms[_call_key(path) if _is_detail(path) else path].append((time.perf_counter() - sent) * 1000)
                results.calls += 1
                if response.status_code >= 400:
                    results.errors[name].append(f"{response.status_code} {path}")
            except httpx.HTTPError as exc:
                results.errors[name].append(f"{type(exc).__name__} {path}")

    started = time.perf_counter()
    await asyncio.gather(*(call(path) for path in calls))
    results.page_ms[name].append((time.perf_counter() - started) * 1000)


async def _recruiter(index, token, sample, deadline, results: Results, base_url: str, seed: int) -> None:
    rng = random.Random(seed)
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=base_url, timeout=30, http2=False) as client:
        while time.monotonic() < deadline:
            pages = _pages(sample, rng)
            name = rng.choice(list(pages))
            await _load_page(client, headers, name, pages[name], results)
            await asyncio.sleep(rng.uniform(1, 3))


def _is_detail(path: str) -> bool:
    """Paths carrying a record id are grouped without it."""
    return any(len(part) == 36 and part.count("-") == 4 for part in path.split("?")[0].split("/"))


def _call_key(path: str) -> str:
    return "/".join("{id}" if len(p) == 36 and p.count("-") == 4 else p for p in path.split("?")[0].split("/"))


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(pct / 100 * len(ordered) + 0.5) - 1))
    return ordered[index]


def _report(results: Results, *, target_ms: float, users: int, duration: int, base_url: str) -> tuple[str, bool]:
    lines = [
        f"Load test: {users} recruiters for {duration}s against {base_url}",
        f"Target: every page's 95th percentile under {target_ms:.0f} ms, and no failed calls.",
        "",
        "| Page | Loads | Median ms | p95 ms | Slowest ms | Failed calls | Result |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    passed = True
    for name in sorted(results.page_ms, key=lambda n: -_percentile(results.page_ms[n], 95)):
        times = results.page_ms[name]
        p95 = _percentile(times, 95)
        failures = len(results.errors[name])
        ok = p95 < target_ms and failures == 0
        passed &= ok
        lines.append(
            f"| {name} | {len(times)} | {statistics.median(times):.0f} | {p95:.0f} | {max(times):.0f} "
            f"| {failures} | {'PASS' if ok else 'FAIL'} |"
        )
    lines += ["", f"{results.calls:,} API calls. Overall: {'PASS' if passed else 'FAIL'}"]
    slowest = sorted(results.call_ms.items(), key=lambda item: -_percentile(item[1], 95))[:12]
    lines += ["", "Slowest API calls (p95, ms):", *[f"- {_percentile(t, 95):.0f}  {path}" for path, t in slowest]]
    failed_calls = [e for errors in results.errors.values() for e in errors]
    if failed_calls:
        lines += ["", "First failed calls:", *[f"- {e}" for e in failed_calls[:10]]]
    return "\n".join(lines), passed


async def main_async(args) -> bool:
    password = os.environ.get("LOADTEST_PASSWORD")
    if not password:
        sys.exit("Set LOADTEST_PASSWORD to the password the load-test recruiters were seeded with.")
    base_url = args.base_url.rstrip("/")

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        print(f"Signing in {args.users} recruiters ...", flush=True)
        tokens = [await _login(client, RECRUITER_EMAIL.format(i % RECRUITER_COUNT + 1), password) for i in range(args.users)]
        headers = {"Authorization": f"Bearer {tokens[0]}"}
        jobs = (await client.get("/jobs?limit=200", headers=headers)).json()
        candidates = (await client.get("/candidates?limit=200", headers=headers)).json()
        sample = {"jobs": [j["id"] for j in jobs], "candidates": [c["id"] for c in candidates]}
        if not sample["jobs"] or not sample["candidates"]:
            sys.exit("The recruiters see no jobs or candidates; seed with scripts.loadtest_seed first.")

    print(f"Running for {args.duration}s ...", flush=True)
    results = Results()
    deadline = time.monotonic() + args.duration
    await asyncio.gather(
        *(_recruiter(i, token, sample, deadline, results, base_url, seed=1000 + i) for i, token in enumerate(tokens))
    )
    report, passed = _report(results, target_ms=args.target_ms, users=args.users, duration=args.duration, base_url=base_url)
    print(report)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(report + "\n")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True, help="the API root, ending in /api/v1")
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--duration", type=int, default=300, help="seconds")
    parser.add_argument("--target-ms", type=float, default=1000)
    parser.add_argument("--report", help="also write the result table to this file")
    passed = asyncio.run(main_async(parser.parse_args()))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
