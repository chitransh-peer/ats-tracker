import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.core.enums import PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.client import ClientContactCreate, ClientCreate, ClientRead, ClientUpdate
from app.services.clients import service as client_service

router = APIRouter(prefix="/clients", tags=["clients"])


def _to_read(db: Session, client) -> ClientRead:
    return ClientRead(
        id=client.id,
        organization_id=client.organization_id,
        name=client.name,
        industry=client.industry,
        status=client.status,
        contacts=client.contacts,
        active_jobs=client_service.active_jobs_count(db, client.id),
    )


@router.get("", response_model=list[ClientRead])
def list_clients(
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CLIENT, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> list[ClientRead]:
    clients = client_service.list_clients(db, current_user.organization_id)
    return [_to_read(db, c) for c in clients]


@router.post("", response_model=ClientRead, status_code=201)
def create_client(
    payload: ClientCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CLIENT, PermissionAction.CREATE)),
    db: Session = Depends(get_db_session),
) -> ClientRead:
    client = client_service.create_client(
        db, organization_id=current_user.organization_id, name=payload.name, industry=payload.industry, status=payload.status
    )
    return _to_read(db, client)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CLIENT, PermissionAction.READ)),
    db: Session = Depends(get_db_session),
) -> ClientRead:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    return _to_read(db, client)


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: uuid.UUID,
    payload: ClientUpdate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CLIENT, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> ClientRead:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    client = client_service.update_client(db, client, **payload.model_dump(exclude_unset=True))
    return _to_read(db, client)


@router.post("/{client_id}/contacts", response_model=ClientRead, status_code=201)
def add_client_contact(
    client_id: uuid.UUID,
    payload: ClientContactCreate,
    current_user: CurrentUser = Depends(require_permission(PermissionResource.CLIENT, PermissionAction.UPDATE)),
    db: Session = Depends(get_db_session),
) -> ClientRead:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    client_service.add_contact(db, client, name=payload.name, email=payload.email, phone=payload.phone, title=payload.title)
    db.refresh(client)
    return _to_read(db, client)
