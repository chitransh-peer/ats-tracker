import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ClientStatus, JobStatus
from app.core.exceptions import NotFoundError
from app.db.models.client import (
    Client,
    ClientAccount,
    ClientAssignment,
    ClientContact,
    ClientDocument,
    ClientNote,
)
from app.db.models.job import Job
from app.services.storage import service as storage_service

_LOAD_OPTIONS = (
    selectinload(Client.contacts),
    selectinload(Client.accounts),
    selectinload(Client.assignments).selectinload(ClientAssignment.user),
    selectinload(Client.primary_owner),
    selectinload(Client.ownership),
    selectinload(Client.client_lead),
    selectinload(Client.parent_client),
    selectinload(Client.created_by_user),
    selectinload(Client.updated_by_user),
)


def _generate_client_code(db: Session, organization_id: uuid.UUID) -> str:
    count = db.scalar(select(func.count(Client.id)).where(Client.organization_id == organization_id)) or 0
    year = datetime.now(UTC).year
    while True:
        count += 1
        code = f"CLI-{year}{count:04d}"
        exists = db.scalar(select(Client.id).where(Client.organization_id == organization_id, Client.client_code == code))
        if exists is None:
            return code


def _search_filter(search: str | None):
    """Case-insensitive "contains" across the fields the list's search box
    promises. Backed by trigram indexes, so it stays fast at 10,000+ clients."""
    if not search or not search.strip():
        return None
    like = f"%{search.strip()}%"
    return or_(Client.name.ilike(like), Client.client_code.ilike(like), Client.industry.ilike(like))


def build_clients_query(organization_id: uuid.UUID, *, search: str | None = None, status: str | None = None) -> Select:
    """Filtered, ordered client query for one page of the list; the caller
    pages it (app/core/pagination.py)."""
    query = select(Client).where(Client.organization_id == organization_id)
    condition = _search_filter(search)
    if condition is not None:
        query = query.where(condition)
    if status:
        query = query.where(Client.status == status)
    return query.options(*_LOAD_OPTIONS).order_by(Client.created_at.desc(), Client.id)


def list_clients(db: Session, organization_id: uuid.UUID) -> list[Client]:
    return list(db.scalars(build_clients_query(organization_id)).all())


def client_summary(db: Session, organization_id: uuid.UUID) -> dict:
    """The list page's headline counts, computed by the database rather than
    by loading every client to count them in the browser."""
    row = db.execute(
        select(
            func.count(Client.id),
            func.count(Client.id).filter(Client.status == ClientStatus.ACTIVE.value),
            func.count(Client.id).filter(Client.status == ClientStatus.PROSPECT.value),
        ).where(Client.organization_id == organization_id)
    ).one()
    open_jobs = (
        db.scalar(
            select(func.count(Job.id)).where(
                Job.organization_id == organization_id,
                Job.client_id.is_not(None),
                Job.status == JobStatus.ACTIVE.value,
            )
        )
        or 0
    )
    return {"total": row[0], "active": row[1], "prospects": row[2], "open_jobs": open_jobs}


def client_options(
    db: Session,
    organization_id: uuid.UUID,
    *,
    search: str | None = None,
    ids: list[uuid.UUID] | None = None,
    limit: int = 20,
) -> list[tuple[uuid.UUID, str]]:
    """(id, name) pairs for a type-to-search picker: the first `limit` matches
    for `search`, or the named `ids` so a picker can label its current value."""
    query = select(Client.id, Client.name).where(Client.organization_id == organization_id)
    if ids:
        query = query.where(Client.id.in_(ids))
    else:
        condition = _search_filter(search)
        if condition is not None:
            query = query.where(condition)
    return [(r.id, r.name) for r in db.execute(query.order_by(Client.name).limit(limit)).all()]


def active_jobs_counts(db: Session, client_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """`active_jobs_count` for a whole page of clients in one query."""
    if not client_ids:
        return {}
    rows = db.execute(
        select(Job.client_id, func.count(Job.id))
        .where(Job.client_id.in_(client_ids), Job.status == JobStatus.ACTIVE.value)
        .group_by(Job.client_id)
    ).all()
    return dict(rows)


def get_client(db: Session, organization_id: uuid.UUID, client_id: uuid.UUID) -> Client:
    client = db.scalar(
        select(Client).where(Client.id == client_id, Client.organization_id == organization_id).options(*_LOAD_OPTIONS)
    )
    if client is None:
        raise NotFoundError("Client not found")
    return client


def create_client(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
    accounts: list[dict] | None = None,
    contacts: list[dict] | None = None,
    notes: list[dict] | None = None,
    assignments: list[dict] | None = None,
    **fields,
) -> Client:
    client = Client(
        organization_id=organization_id,
        client_code=_generate_client_code(db, organization_id),
        created_by=actor_id,
        updated_by=actor_id,
        **fields,
    )
    db.add(client)
    db.flush()

    for account in accounts or []:
        db.add(ClientAccount(client_id=client.id, **account))
    for contact in contacts or []:
        db.add(ClientContact(client_id=client.id, **contact))
    for note in notes or []:
        db.add(ClientNote(client_id=client.id, author_id=actor_id, **note))
    for assignment in assignments or []:
        db.add(ClientAssignment(client_id=client.id, **assignment))

    db.commit()
    return get_client(db, organization_id, client.id)


def update_client(db: Session, client: Client, *, actor_id: uuid.UUID | None = None, **fields) -> Client:
    for key, value in fields.items():
        if value is not None:
            setattr(client, key, value)
    if actor_id is not None:
        client.updated_by = actor_id
    db.commit()
    db.refresh(client)
    return client


def add_contact(db: Session, client: Client, **fields) -> ClientContact:
    contact = ClientContact(client_id=client.id, **fields)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def add_account(db: Session, client: Client, **fields) -> ClientAccount:
    account = ClientAccount(client_id=client.id, **fields)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def add_assignment(db: Session, client: Client, **fields) -> ClientAssignment:
    assignment = ClientAssignment(client_id=client.id, **fields)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def add_note(db: Session, client: Client, *, author_id: uuid.UUID | None, **fields) -> ClientNote:
    note = ClientNote(client_id=client.id, author_id=author_id, **fields)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notes(db: Session, client: Client) -> list[ClientNote]:
    return list(
        db.scalars(
            select(ClientNote)
            .where(ClientNote.client_id == client.id)
            .options(selectinload(ClientNote.author))
            .order_by(ClientNote.created_at.desc())
        ).all()
    )


def add_document(
    db: Session,
    client: Client,
    *,
    file_name: str,
    content_type: str,
    data: bytes,
    uploaded_by: uuid.UUID | None,
) -> ClientDocument:
    key = f"clients/{client.id}/{uuid.uuid4()}-{file_name}"
    storage_service.upload_bytes(key, data, content_type)
    document = ClientDocument(
        client_id=client.id,
        file_name=file_name,
        content_type=content_type,
        size_bytes=len(data),
        storage_key=key,
        uploaded_by=uploaded_by,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document(db: Session, client: Client, document_id: uuid.UUID) -> ClientDocument:
    """Fetch one document, scoped to the client it belongs to, so a document id
    cannot be used to reach a file hanging off a record the caller cannot see."""
    document = db.scalar(
        select(ClientDocument).where(
            ClientDocument.id == document_id,
            ClientDocument.client_id == client.id,
        )
    )
    if document is None:
        raise NotFoundError("Document not found")
    return document


def list_documents(db: Session, client: Client) -> list[ClientDocument]:
    return list(
        db.scalars(
            select(ClientDocument).where(ClientDocument.client_id == client.id).order_by(ClientDocument.created_at.desc())
        ).all()
    )


def active_jobs_count(db: Session, client_id: uuid.UUID) -> int:
    return db.scalar(select(func.count(Job.id)).where(Job.client_id == client_id, Job.status == JobStatus.ACTIVE.value)) or 0
