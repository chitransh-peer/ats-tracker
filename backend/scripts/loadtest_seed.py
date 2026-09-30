"""Fill a separate "Load Test" organization with production-scale data.

Creates, in an organization of its own so no real record is touched:
  20 recruiters (loadtest-recruiter-01..20@loadtest.invalid)
  100,000 candidates, 50,000 vendors, 10,000 clients
  2,000 jobs, 120,000 applications with stage history,
  20,000 interviews, 5,000 offers, 1,000 onboarding cases,
  50,000 AI evaluations and 500 hotlists

Usage:
  LOADTEST_PASSWORD=... python -m scripts.loadtest_seed           # seed (skips if seeded)
  python -m scripts.loadtest_seed --delete                          # remove it all again
  python -m scripts.loadtest_seed --scale 0.1                       # a tenth of the volume

Everything hangs off the organization row, and every foreign key to it
cascades, so --delete is a single DELETE.
"""

import argparse
import os
import random
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.core.enums import JobStatus, RoleName
from app.core.security import hash_password
from app.db.models.ai import AIEvaluation
from app.db.models.application import Application, ApplicationStageHistory
from app.db.models.candidate import Candidate
from app.db.models.client import Client
from app.db.models.hotlist import Hotlist
from app.db.models.interview import Interview
from app.db.models.job import Job
from app.db.models.offer import Offer
from app.db.models.onboarding import OnboardingCase
from app.db.models.organization import Organization, OrganizationSettings
from app.db.models.user import User
from app.db.models.vendor import Vendor
from app.db.session import SessionLocal
from app.services.pipeline.service import seed_default_stage_template
from app.services.roles.service import seed_roles_and_permissions
from app.services.users.service import _assign_roles
from scripts.loadtest_common import ORG_SLUG, RECRUITER_COUNT, RECRUITER_EMAIL

VOLUMES = {
    "candidates": 100_000,
    "vendors": 50_000,
    "clients": 10_000,
    "jobs": 2_000,
    "applications": 120_000,
    "interviews": 20_000,
    "offers": 5_000,
    "onboarding": 1_000,
    "evaluations": 50_000,
    "hotlists": 500,
}

_BATCH = 5_000
_FIRST = ["Aarav", "Maya", "Liam", "Priya", "Noah", "Sara", "Ethan", "Ananya", "Lucas", "Zoe", "Omar", "Isha"]
_LAST = ["Sharma", "Smith", "Patel", "Garcia", "Chen", "Khan", "Nguyen", "Brown", "Iyer", "Lopez", "Kim"]
_TITLES = ["Backend Engineer", "Data Analyst", "Project Manager", "QA Engineer", "DevOps Engineer", "Java Developer"]
_SKILLS = ["Python", "Java", "SQL", "AWS", "React", "Kubernetes", "Terraform", "Go", "Spark", "Salesforce"]
_STATES = ["TX", "CA", "NY", "NJ", "IL", "WA", "GA", "FL"]


def _insert(db: Session, model, rows: list[dict], label: str) -> None:
    started = time.monotonic()
    for start in range(0, len(rows), _BATCH):
        db.execute(insert(model), rows[start : start + _BATCH])
    db.commit()
    print(f"  {label}: {len(rows):,} in {time.monotonic() - started:.1f}s", flush=True)


def _name(rng: random.Random) -> str:
    return f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"


def seed(db: Session, *, password: str, scale: float) -> None:
    if db.scalar(select(Organization.id).where(Organization.slug == ORG_SLUG)) is not None:
        print("The load-test organization already exists; delete it first to reseed.")
        return

    volume = {key: max(1, int(count * scale)) for key, count in VOLUMES.items()}
    rng = random.Random(20260930)
    now = datetime.now(UTC)
    print(f"Seeding organization '{ORG_SLUG}' ...", flush=True)

    seed_roles_and_permissions(db)
    org = Organization(name="Load Test", slug=ORG_SLUG)
    db.add(org)
    db.flush()
    db.add(OrganizationSettings(organization_id=org.id))
    db.commit()
    stages = sorted(seed_default_stage_template(db, org.id).stages, key=lambda s: s.sort_order)
    template_id = stages[0].template_id

    hashed = hash_password(password)
    recruiters = []
    for i in range(1, RECRUITER_COUNT + 1):
        user = User(
            organization_id=org.id, email=RECRUITER_EMAIL.format(i), full_name=f"Recruiter {i:02d}", hashed_password=hashed
        )
        db.add(user)
        db.flush()
        _assign_roles(db, user, [RoleName.RECRUITER.value])
        recruiters.append(user.id)
    db.commit()
    print(f"  recruiters: {RECRUITER_COUNT}", flush=True)

    def created(days: int = 700) -> datetime:
        return now - timedelta(days=rng.randint(0, days), minutes=rng.randint(0, 1440))

    candidate_ids = [uuid.uuid4() for _ in range(volume["candidates"])]
    _insert(
        db,
        Candidate,
        [
            {
                "id": cid,
                "organization_id": org.id,
                "full_name": _name(rng),
                "email": f"candidate{i}@loadtest.invalid",
                "phone": f"+1555{i:07d}",
                "location": rng.choice(_STATES),
                "current_title": rng.choice(_TITLES),
                "skills": rng.sample(_SKILLS, 3),
                "created_at": created(),
            }
            for i, cid in enumerate(candidate_ids)
        ],
        "candidates",
    )
    _insert(
        db,
        Vendor,
        [
            {
                "organization_id": org.id,
                "name": f"Vendor {i} {rng.choice(_LAST)} Staffing",
                "state": rng.choice(_STATES),
                "country": "USA",
                "created_at": created(),
            }
            for i in range(volume["vendors"])
        ],
        "vendors",
    )
    client_ids = [uuid.uuid4() for _ in range(volume["clients"])]
    _insert(
        db,
        Client,
        [
            {
                "id": cid,
                "organization_id": org.id,
                "client_code": f"LT{i:06d}",
                "name": f"Client {i} {rng.choice(_LAST)} Corp",
                "industry": "Technology",
                "created_at": created(),
            }
            for i, cid in enumerate(client_ids)
        ],
        "clients",
    )

    job_ids = [uuid.uuid4() for _ in range(volume["jobs"])]
    job_posted: dict[uuid.UUID, datetime] = {}
    job_rows = []
    for i, jid in enumerate(job_ids):
        posted = created(400)
        job_posted[jid] = posted
        job_rows.append(
            {
                "id": jid,
                "organization_id": org.id,
                "req_id": f"LT-{i:05d}",
                "slug": f"loadtest-job-{i}",
                "title": f"{rng.choice(_TITLES)} {i}",
                "client_id": rng.choice(client_ids),
                "recruiter_id": rng.choice(recruiters),
                "recruitment_manager_id": rng.choice(recruiters),
                "assigned_to_ids": rng.sample(recruiters, 2),
                "stage_template_id": template_id,
                "workplace": "Remote",
                "employment_type": "Contract",
                "status": rng.choice([JobStatus.ACTIVE.value] * 3 + [JobStatus.DRAFT.value, JobStatus.CLOSED.value]),
                "required_skills": rng.sample(_SKILLS, 3),
                "pay_min": 60,
                "pay_max": 90,
                "posted_at": posted,
                "created_at": posted,
                "created_by": rng.choice(recruiters),
            }
        )
    _insert(db, Job, job_rows, "jobs")

    pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()
    while len(pairs) < volume["applications"]:
        pairs.add((rng.choice(candidate_ids), rng.choice(job_ids)))
    application_rows, history_rows = [], []
    for candidate_id, job_id in pairs:
        aid = uuid.uuid4()
        applied = job_posted[job_id] + timedelta(days=rng.randint(0, 30))
        reached = min(int(rng.expovariate(0.45)), len(stages) - 1)
        status = "Hired" if stages[reached].name == "Hired" else rng.choice(["Active"] * 6 + ["Rejected", "On Hold"])
        application_rows.append(
            {
                "id": aid,
                "organization_id": org.id,
                "candidate_id": candidate_id,
                "job_id": job_id,
                "current_stage_id": stages[reached].id,
                "status": status,
                "source": rng.choice(["LinkedIn", "Referral", "Careers Page", "vendor:Vendor 1 Smith Staffing"]),
                "applied_at": applied,
            }
        )
        for step in range(reached + 1):
            history_rows.append(
                {
                    "application_id": aid,
                    "from_stage_id": stages[step - 1].id if step else None,
                    "to_stage_id": stages[step].id,
                    "created_at": applied + timedelta(days=step * 3),
                }
            )
    _insert(db, Application, application_rows, "applications")
    _insert(db, ApplicationStageHistory, history_rows, "stage history")

    application_ids = [row["id"] for row in application_rows]
    _insert(
        db,
        Interview,
        [
            {
                "organization_id": org.id,
                "application_id": rng.choice(application_ids),
                "round_name": rng.choice(["Screen", "Technical", "Manager"]),
                "mode": rng.choice(["Video", "Phone", "Onsite"]),
                "scheduled_at": now + timedelta(days=rng.randint(-300, 60), hours=rng.randint(0, 23)),
                "status": rng.choice(["Scheduled", "Completed", "Completed"]),
            }
            for _ in range(volume["interviews"])
        ],
        "interviews",
    )
    _insert(
        db,
        Offer,
        [
            {
                "organization_id": org.id,
                "application_id": rng.choice(application_ids),
                "base_salary": rng.randint(80_000, 180_000),
                "status": rng.choice(["Draft", "Approval Pending", "Sent", "Accepted", "Declined"]),
                "created_at": created(365),
            }
            for _ in range(volume["offers"])
        ],
        "offers",
    )
    _insert(
        db,
        OnboardingCase,
        [
            {"organization_id": org.id, "application_id": aid, "status": "In Progress"}
            for aid in rng.sample(application_ids, volume["onboarding"])
        ],
        "onboarding cases",
    )
    _insert(
        db,
        AIEvaluation,
        [
            {
                "organization_id": org.id,
                "application_id": aid,
                "version": 1,
                "status": "completed",
                "overall_score": round(rng.uniform(10, 99), 2),
                "recommendation_label": rng.choice(["strong_fit", "fit", "partial_fit", "not_a_fit"]),
            }
            for aid in rng.sample(application_ids, volume["evaluations"])
        ],
        "AI evaluations",
    )
    _insert(
        db,
        Hotlist,
        [
            {"organization_id": org.id, "name": f"Bench hotlist {i}", "subject": "Available consultants"}
            for i in range(volume["hotlists"])
        ],
        "hotlists",
    )
    print("Done.", flush=True)


def delete_all(db: Session) -> None:
    org_id = db.scalar(select(Organization.id).where(Organization.slug == ORG_SLUG))
    if org_id is None:
        print("No load-test organization to delete.")
        return
    started = time.monotonic()
    db.execute(delete(Organization).where(Organization.id == org_id))
    db.commit()
    print(f"Deleted the load-test organization and everything in it in {time.monotonic() - started:.1f}s.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--delete", action="store_true", help="remove the load-test organization")
    parser.add_argument("--scale", type=float, default=1.0, help="fraction of the full volume to create")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.delete:
            delete_all(db)
            return
        password = os.environ.get("LOADTEST_PASSWORD")
        if not password or len(password) < 12:
            sys.exit("Set LOADTEST_PASSWORD (12+ characters) for the load-test recruiters.")
        seed(db, password=password, scale=args.scale)
    finally:
        db.close()


if __name__ == "__main__":
    main()
