import logging
import uuid

import dramatiq

from app.core.enums import AIEvaluationStatus, ResumeParseStatus
from app.db.models.ai import AIEvaluation, ResumeParseRun
from app.db.session import SessionLocal
from app.services.ai.evaluation import evaluate_application
from app.services.ai.resume_parsing import parse_resume
from app.workers.broker import broker  # noqa: F401  (ensures the broker is configured)

logger = logging.getLogger(__name__)


def _mark_failed(model, row_id: uuid.UUID, failed_status: str, exc: Exception) -> None:
    """Record an unexpected failure on its own session, so the row reads as
    failed rather than sitting in "processing" forever with nothing retrying it."""
    db = SessionLocal()
    try:
        row = db.get(model, row_id)
        if row is not None:
            row.status = failed_status
            row.error_message = f"Unexpected error: {exc}"[:2000]
            db.commit()
    except Exception:
        logger.exception("Could not record the failure of %s %s", model.__name__, row_id)
    finally:
        db.close()


@dramatiq.actor(max_retries=1)
def parse_resume_task(run_id: str, next_evaluation_id: str | None = None) -> None:
    run_uuid = uuid.UUID(run_id)
    db = SessionLocal()
    try:
        run = db.get(ResumeParseRun, run_uuid)
        if run is not None:
            parse_resume(db, run)
    except Exception as exc:
        db.rollback()
        _mark_failed(ResumeParseRun, run_uuid, ResumeParseStatus.FAILED.value, exc)
        logger.exception("Résumé parse %s failed", run_id)
    finally:
        db.close()
    # Chain evaluation only after parsing finishes, so the evaluator can read the
    # freshly parsed résumé (skills/experience) instead of the empty candidate stub
    # created by a public careers-page application. Runs even if parsing failed:
    # a score from the application fields beats no score at all.
    if next_evaluation_id is not None:
        # Imported here: dispatch imports nothing from tasks, but keep it that way.
        from app.workers.dispatch import dispatch

        # allow_inline: this already runs off the request (in a worker, or after
        # the response), so running the next step here keeps nobody waiting.
        dispatch(evaluate_application_task, next_evaluation_id, allow_inline=True)


@dramatiq.actor(max_retries=1)
def evaluate_application_task(evaluation_id: str) -> None:
    evaluation_uuid = uuid.UUID(evaluation_id)
    db = SessionLocal()
    try:
        evaluation = db.get(AIEvaluation, evaluation_uuid)
        if evaluation is not None:
            evaluate_application(db, evaluation)
    except Exception as exc:
        db.rollback()
        _mark_failed(AIEvaluation, evaluation_uuid, AIEvaluationStatus.FAILED.value, exc)
        logger.exception("AI evaluation %s failed", evaluation_id)
    finally:
        db.close()
