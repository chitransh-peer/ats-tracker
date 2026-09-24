import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_permission
from app.api.v1.routes._documents import document_response
from app.core.enums import PermissionAction, PermissionResource
from app.schemas.auth import CurrentUser
from app.schemas.client import (
    ClientAccountCreate,
    ClientAccountRead,
    ClientAssignmentCreate,
    ClientAssignmentRead,
    ClientContactCreate,
    ClientCreate,
    ClientDocumentRead,
    ClientNoteCreate,
    ClientNoteRead,
    ClientRead,
    ClientUpdate,
)
from app.services.clients import service as client_service

router = APIRouter(prefix="/clients", tags=["clients"])

_READ = require_permission(PermissionResource.CLIENT, PermissionAction.READ)
_CREATE = require_permission(PermissionResource.CLIENT, PermissionAction.CREATE)
_UPDATE = require_permission(PermissionResource.CLIENT, PermissionAction.UPDATE)


def _to_read(db: Session, client) -> ClientRead:
    return ClientRead(
        **{
            column.name: getattr(client, column.name)
            for column in client.__table__.columns
            if column.name not in {"created_by", "updated_by"}
        },
        created_by=client.created_by,
        updated_by=client.updated_by,
        primary_owner_name=client.primary_owner.full_name if client.primary_owner else None,
        ownership_name=client.ownership.full_name if client.ownership else None,
        client_lead_name=client.client_lead.full_name if client.client_lead else None,
        parent_client_name=client.parent_client.name if client.parent_client else None,
        created_by_name=client.created_by_user.full_name if client.created_by_user else None,
        updated_by_name=client.updated_by_user.full_name if client.updated_by_user else None,
        contacts=client.contacts,
        accounts=client.accounts,
        assignments=[
            ClientAssignmentRead(
                id=a.id,
                user_id=a.user_id,
                assignment_role=a.assignment_role,
                user_name=a.user.full_name if a.user else None,
            )
            for a in client.assignments
        ],
        active_jobs=client_service.active_jobs_count(db, client.id),
    )


def _note_read(note) -> ClientNoteRead:
    return ClientNoteRead(
        id=note.id,
        body=note.body,
        note_type=note.note_type,
        priority=note.priority,
        author_id=note.author_id,
        author_name=note.author.full_name if note.author else None,
        created_at=note.created_at,
    )


@router.get("", response_model=list[ClientRead])
def list_clients(
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> list[ClientRead]:
    clients = client_service.list_clients(db, current_user.organization_id)
    return [_to_read(db, c) for c in clients]


@router.post("", response_model=ClientRead, status_code=201)
def create_client(
    payload: ClientCreate,
    current_user: CurrentUser = Depends(_CREATE),
    db: Session = Depends(get_db_session),
) -> ClientRead:
    data = payload.model_dump()
    client = client_service.create_client(
        db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        accounts=data.pop("accounts", []),
        contacts=data.pop("contacts", []),
        notes=data.pop("notes", []),
        assignments=data.pop("assignments", []),
        **data,
    )
    return _to_read(db, client)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: uuid.UUID,
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> ClientRead:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    return _to_read(db, client)


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: uuid.UUID,
    payload: ClientUpdate,
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> ClientRead:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    client_service.update_client(db, client, actor_id=current_user.id, **payload.model_dump(exclude_unset=True))
    return _to_read(db, client_service.get_client(db, current_user.organization_id, client_id))


@router.post("/{client_id}/contacts", response_model=ClientRead, status_code=201)
def add_client_contact(
    client_id: uuid.UUID,
    payload: ClientContactCreate,
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> ClientRead:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    client_service.add_contact(db, client, **payload.model_dump())
    return _to_read(db, client_service.get_client(db, current_user.organization_id, client_id))


@router.post("/{client_id}/accounts", response_model=ClientAccountRead, status_code=201)
def add_client_account(
    client_id: uuid.UUID,
    payload: ClientAccountCreate,
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> ClientAccountRead:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    return client_service.add_account(db, client, **payload.model_dump())


@router.post("/{client_id}/assignments", response_model=ClientAssignmentRead, status_code=201)
def add_client_assignment(
    client_id: uuid.UUID,
    payload: ClientAssignmentCreate,
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> ClientAssignmentRead:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    assignment = client_service.add_assignment(db, client, **payload.model_dump())
    return ClientAssignmentRead(
        id=assignment.id,
        user_id=assignment.user_id,
        assignment_role=assignment.assignment_role,
        user_name=assignment.user.full_name if assignment.user else None,
    )


@router.get("/{client_id}/notes", response_model=list[ClientNoteRead])
def list_client_notes(
    client_id: uuid.UUID,
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> list[ClientNoteRead]:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    return [_note_read(n) for n in client_service.list_notes(db, client)]


@router.post("/{client_id}/notes", response_model=ClientNoteRead, status_code=201)
def add_client_note(
    client_id: uuid.UUID,
    payload: ClientNoteCreate,
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> ClientNoteRead:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    note = client_service.add_note(db, client, author_id=current_user.id, **payload.model_dump())
    return _note_read(note)


@router.get("/{client_id}/documents", response_model=list[ClientDocumentRead])
def list_client_documents(
    client_id: uuid.UUID,
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> list[ClientDocumentRead]:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    return client_service.list_documents(db, client)


@router.get("/{client_id}/documents/{document_id}/download")
def download_client_document(
    client_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(_READ),
    db: Session = Depends(get_db_session),
) -> Response:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    document = client_service.get_document(db, client, document_id)
    return document_response(
        storage_key=document.storage_key,
        file_name=document.file_name,
        content_type=document.content_type,
    )


@router.post("/{client_id}/documents", response_model=ClientDocumentRead, status_code=201)
async def upload_client_document(
    client_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(_UPDATE),
    db: Session = Depends(get_db_session),
) -> ClientDocumentRead:
    client = client_service.get_client(db, current_user.organization_id, client_id)
    data = await file.read()
    return client_service.add_document(
        db,
        client,
        file_name=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        uploaded_by=current_user.id,
    )
