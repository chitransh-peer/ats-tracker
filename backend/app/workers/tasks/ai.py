import uuid

import dramatiq

from app.db.models.ai import AIEvaluation, ResumeParseRun
from app.db.session import SessionLocal
from app.services.ai.evaluation import evaluate_application
from app.services.ai.resume_parsing import parse_resume
from app.workers.broker import broker  # noqa: F401  (ensures the broker is configured)


@dramatiq.actor(max_retries=1)
def parse_resume_task(run_id: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(ResumeParseRun, uuid.UUID(run_id))
        if run is not None:
            parse_resume(db, run)
    finally:
        db.close()


@dramatiq.actor(max_retries=1)
def evaluate_application_task(evaluation_id: str) -> None:
    db = SessionLocal()
    try:
        evaluation = db.get(AIEvaluation, uuid.UUID(evaluation_id))
        if evaluation is not None:
            evaluate_application(db, evaluation)
    finally:
        db.close()
