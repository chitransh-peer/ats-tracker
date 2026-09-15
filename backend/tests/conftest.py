import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.rate_limit import limiter
from app.db.models import Base
from app.db.models.organization import Organization, OrganizationSettings
from app.db.session import SessionLocal, engine
from app.main import app
from app.services.applications.service import create_application
from app.services.candidates.service import create_candidate
from app.services.clients.service import create_client
from app.services.jobs.service import create_job
from app.services.pipeline.service import seed_default_stage_template
from app.services.roles.service import seed_roles_and_permissions
from app.services.users.service import create_user


@pytest.fixture(scope="session", autouse=True)
def _disable_rate_limiting():
    """The auth fixtures below log in once per test — 100+ logins in a run,
    easily well past the login endpoint's real 10/minute limit. That limit
    exists for a live attacker, not the test suite, so it is switched off for
    the whole session rather than tuned around."""
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture(scope="session", autouse=True)
def _prepare_schema():
    """Creates any missing tables and seeds the role/permission matrix once per test run.

    Uses the same Postgres instance as local dev (docker compose `db` service) rather
    than a throwaway test database — acceptable for this phase since every test creates
    its own uniquely-named organization/user and never touches pre-existing rows.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_roles_and_permissions(db)
    finally:
        db.close()


@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def organization(db: Session) -> Organization:
    org = Organization(name=f"Test Org {uuid.uuid4().hex[:8]}", slug=f"test-org-{uuid.uuid4().hex[:8]}")
    db.add(org)
    db.flush()
    db.add(OrganizationSettings(organization_id=org.id))
    db.commit()
    seed_default_stage_template(db, org.id)
    return org


@pytest.fixture
def make_user(db: Session, organization: Organization):
    def _make_user(*, role_names: list[str], password: str = "correct-horse-battery-staple"):
        email = f"user-{uuid.uuid4().hex[:10]}@example.com"
        return create_user(
            db,
            organization_id=organization.id,
            email=email,
            full_name="Test User",
            password=password,
            role_names=role_names,
        ), password

    return _make_user


@pytest.fixture
def make_client(db: Session, organization: Organization):
    def _make_client(*, name: str | None = None, status: str = "Active"):
        return create_client(
            db,
            organization_id=organization.id,
            name=name or f"Client {uuid.uuid4().hex[:8]}",
            industry="Technology",
            status=status,
        )

    return _make_client


@pytest.fixture
def make_job(db: Session, organization: Organization):
    def _make_job(*, actor_id=None, title: str = "Senior Backend Engineer", **overrides):
        fields = {
            "title": title,
            "department": "Engineering",
            "client_id": None,
            "hiring_manager_id": None,
            "recruiter_id": None,
            "location": "Remote",
            "workplace": "Remote",
            "employment_type": "Full-time",
            "openings": 1,
            "pay_min": 100000,
            "pay_max": 150000,
            "priority": "Medium",
            "summary": None,
            "description": None,
            "responsibilities": [],
            "required_skills": [],
            "nice_to_have": [],
            "screening_questions": [],
            "experience": None,
            "education": None,
        }
        fields.update(overrides)
        return create_job(db, organization_id=organization.id, actor_id=actor_id, **fields)

    return _make_job


@pytest.fixture
def make_candidate(db: Session, organization: Organization):
    def _make_candidate(*, email: str | None = None, phone: str | None = None, **overrides):
        fields = {
            "full_name": "Test Candidate",
            "location": None,
            "current_company": None,
            "current_title": None,
            "total_experience_years": None,
            "relevant_experience_years": None,
            "notice_period": None,
            "current_ctc": None,
            "expected_ctc": None,
            "skills": [],
            "source": None,
            "linkedin_url": None,
            "work_auth": None,
            "relocation_ok": False,
        }
        fields.update(overrides)
        candidate, _duplicates = create_candidate(
            db,
            organization_id=organization.id,
            actor_id=None,
            email=email or f"candidate-{uuid.uuid4().hex[:10]}@example.com",
            phone=phone,
            education=[],
            tags=[],
            **fields,
        )
        return candidate

    return _make_candidate


@pytest.fixture
def make_application(db: Session, organization: Organization):
    def _make_application(*, candidate, job, source: str | None = None):
        return create_application(
            db, organization_id=organization.id, candidate_id=candidate.id, job_id=job.id, source=source
        )

    return _make_application


@pytest.fixture
def client(db: Session):
    def _override_get_db_session():
        yield db

    app.dependency_overrides[get_db_session] = _override_get_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db_session, None)


@pytest.fixture
def auth_headers(client: TestClient):
    def _headers(email: str, password: str) -> dict[str, str]:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _headers
