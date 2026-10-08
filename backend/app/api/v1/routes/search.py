import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.core.enums import PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.services.candidates import service as candidate_service
from app.services.clients import service as client_service
from app.services.jobs import service as job_service
from app.services.roles.service import roles_grant
from app.services.vendors import service as vendor_service

router = APIRouter(prefix="/search", tags=["search"])


class JobHit(BaseModel):
    id: uuid.UUID
    title: str
    req_id: str
    status: str


class CandidateHit(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str | None
    current_title: str | None


class NamedHit(BaseModel):
    id: uuid.UUID
    name: str


class SearchResults(BaseModel):
    query: str
    jobs: list[JobHit]
    candidates: list[CandidateHit]
    clients: list[NamedHit]
    vendors: list[NamedHit]


@router.get("", response_model=SearchResults)
def global_search(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=5, ge=1, le=20),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SearchResults:
    """The header search box: the first few jobs (by title, req ID or client),
    candidates, clients and vendors matching `q`. Each group is searched only
    when the viewer may read that kind of record, and within their usual
    scope, so search never reveals what the list pages would hide."""
    org = current_user.organization_id
    term = q.strip()

    def can_read(resource: PermissionResource) -> bool:
        return roles_grant(db, current_user.roles, resource, PermissionAction.READ)

    jobs: list[JobHit] = []
    if term and can_read(PermissionResource.JOB):
        jobs = [
            JobHit(id=id_, title=title, req_id=req_id, status=status)
            for id_, title, req_id, status in job_service.job_options(db, org, search=term, limit=limit, viewer=current_user)
        ]

    candidates: list[CandidateHit] = []
    if term and can_read(PermissionResource.CANDIDATE):
        query = candidate_service.build_candidates_query(org, search=term, viewer=current_user).limit(limit)
        candidates = [
            CandidateHit(id=c.id, full_name=c.full_name, email=c.email, current_title=c.current_title)
            for c in db.scalars(query).unique()
        ]

    clients: list[NamedHit] = []
    if term and can_read(PermissionResource.CLIENT):
        clients = [
            NamedHit(id=id_, name=name) for id_, name in client_service.client_options(db, org, search=term, limit=limit)
        ]

    vendors: list[NamedHit] = []
    if term and can_read(PermissionResource.VENDOR):
        query = vendor_service.build_vendors_query(org, search=term).limit(limit)
        vendors = [NamedHit(id=v.id, name=v.name) for v in db.scalars(query).unique()]

    return SearchResults(query=term, jobs=jobs, candidates=candidates, clients=clients, vendors=vendors)
