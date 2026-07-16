import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import JobStatus
from app.core.exceptions import NotFoundError
from app.db.models.client import Client, ClientContact
from app.db.models.job import Job


def list_clients(db: Session, organization_id: uuid.UUID) -> list[Client]:
    return list(
        db.scalars(
            select(Client).where(Client.organization_id == organization_id).options(selectinload(Client.contacts))
        ).all()
    )


def get_client(db: Session, organization_id: uuid.UUID, client_id: uuid.UUID) -> Client:
    client = db.scalar(
        select(Client)
        .where(Client.id == client_id, Client.organization_id == organization_id)
        .options(selectinload(Client.contacts))
    )
    if client is None:
        raise NotFoundError("Client not found")
    return client


def create_client(db: Session, *, organization_id: uuid.UUID, name: str, industry: str | None, status: str) -> Client:
    client = Client(organization_id=organization_id, name=name, industry=industry, status=status)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def update_client(db: Session, client: Client, **fields) -> Client:
    for key, value in fields.items():
        if value is not None:
            setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return client


def add_contact(
    db: Session, client: Client, *, name: str, email: str | None, phone: str | None, title: str | None
) -> ClientContact:
    contact = ClientContact(client_id=client.id, name=name, email=email, phone=phone, title=title)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def active_jobs_count(db: Session, client_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count(Job.id)).where(Job.client_id == client_id, Job.status == JobStatus.ACTIVE.value)
    ) or 0
