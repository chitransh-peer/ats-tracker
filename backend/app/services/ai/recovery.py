"""Picking up careers-page scoring that never finished.

Scoring a public application runs off the request -- on a worker, or in-process
after the response (app/workers/dispatch.py). Either can be cut short: an
instance scaled away mid-call, a deploy, a crash. What is left behind is an
evaluation or résumé parse sitting in "pending" or "processing" with nothing
coming back for it, and an applicant who never gets a score.

`resume_stalled_work` finds those and runs them again. It is cheap when there is
nothing to do (one indexed query each), so it is simply run after every
careers-page application rather than on a schedule this deployment has no way
to keep.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.enums import AIEvaluationStatus, ResumeParseStatus
from app.db.models.ai import AIEvaluation, ResumeParseRun
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Well past the longest a single parse or evaluation can take (the request
# timeout is 5 minutes), so anything older is not merely still running.
STALLED_AFTER = timedelta(minutes=15)
# Work older than this is not retried but closed out as failed, so a row that
# fails every time cannot be picked up forever. A recruiter can still re-score.
GIVE_UP_AFTER = timedelta(hours=24)
# Per sweep, so one sweep never turns into a long burst of paid LLM calls.
BATCH_SIZE = 5

_OPEN_EVALUATION = (AIEvaluationStatus.PENDING.value, AIEvaluationStatus.PROCESSING.value)
_OPEN_PARSE = (ResumeParseStatus.PENDING.value, ResumeParseStatus.PROCESSING.value)


def _claim(db, model, open_statuses, stalled_column, now):
    """Lock a batch of stalled rows so two instances sweeping at once never
    both re-run the same one, and give up on the ones that are too old."""
    rows = list(
        db.scalars(
            select(model)
            .where(model.status.in_(open_statuses), stalled_column < now - STALLED_AFTER)
            .order_by(stalled_column)
            .limit(BATCH_SIZE)
            .with_for_update(skip_locked=True)
        ).all()
    )
    retry = []
    for row in rows:
        if row.created_at < now - GIVE_UP_AFTER:
            row.status = "failed"
            row.error_message = "Timed out before scoring finished. Re-run the review from the application."
        else:
            # Back to pending: for an evaluation this also moves updated_at on,
            # which is what stops the next sweep claiming it again while it runs.
            row.status = open_statuses[0]
            retry.append(row.id)
    db.commit()
    return retry


def resume_stalled_work() -> None:
    # Imported here: the tasks import the services this module sits beside.
    from app.workers.tasks.ai import evaluate_application_task, parse_resume_task

    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        parse_ids = _claim(db, ResumeParseRun, _OPEN_PARSE, ResumeParseRun.created_at, now)
        evaluation_ids = _claim(db, AIEvaluation, _OPEN_EVALUATION, AIEvaluation.updated_at, now)
    except Exception:
        logger.exception("Could not look for stalled AI work")
        return
    finally:
        db.close()

    if parse_ids or evaluation_ids:
        logger.info("Re-running %d stalled résumé parse(s) and %d evaluation(s)", len(parse_ids), len(evaluation_ids))
    # Parses first, so a re-run evaluation can read the résumé they produce.
    for run_id in parse_ids:
        parse_resume_task.fn(str(run_id))
    for evaluation_id in evaluation_ids:
        evaluate_application_task.fn(str(evaluation_id))
