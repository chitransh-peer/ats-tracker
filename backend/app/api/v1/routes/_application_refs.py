"""Fill in candidate and job names on reads of records hung off an application."""

from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.applications.service import application_labels

T = TypeVar("T", bound=BaseModel)


def with_application_refs(db: Session, rows: list, read_model: type[T]) -> list[T]:
    """`read_model` for each row, with its application's candidate and job
    filled in from one query for the whole list."""
    labels = application_labels(db, [row.application_id for row in rows])
    items = []
    for row in rows:
        label = labels.get(row.application_id, {})
        items.append(
            read_model.model_validate(row).model_copy(
                update={
                    "candidate_id": label.get("candidate_id"),
                    "candidate_name": label.get("candidate_name"),
                    "job_id": label.get("job_id"),
                    "job_title": label.get("job_title"),
                }
            )
        )
    return items
