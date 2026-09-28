"""Careers-page scoring that was cut short is picked up again, and scoring that
has been stuck too long is closed out instead of retried forever."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from app.core.enums import AIEvaluationStatus, RoleName
from app.db.models.ai import AIEvaluation
from app.services.ai.evaluation import create_pending_evaluation
from app.services.ai.recovery import resume_stalled_work


def _stalled_evaluation(db, organization, make_user, make_job, make_candidate, make_application, *, age: timedelta):
    user, _ = make_user(role_names=[RoleName.RECRUITER.value])
    application = make_application(candidate=make_candidate(), job=make_job(actor_id=user.id))
    evaluation = create_pending_evaluation(db, organization_id=organization.id, application_id=application.id, actor_id=None)
    stamp = datetime.now(UTC) - age
    db.execute(update(AIEvaluation).where(AIEvaluation.id == evaluation.id).values(created_at=stamp, updated_at=stamp))
    db.commit()
    return evaluation.id


def _sweep_until_settled(db, evaluation_id) -> AIEvaluation:
    # The sweep works oldest-first in small batches across the whole (shared)
    # test database, so leftovers from earlier runs may be ahead of this one.
    for _ in range(30):
        resume_stalled_work()
        db.expire_all()
        evaluation = db.get(AIEvaluation, evaluation_id)
        if evaluation.status not in (AIEvaluationStatus.PENDING.value, AIEvaluationStatus.PROCESSING.value):
            return evaluation
    raise AssertionError("the stalled evaluation was never picked up")


def test_a_stalled_evaluation_is_run_again(db, organization, make_user, make_job, make_candidate, make_application):
    evaluation_id = _stalled_evaluation(
        db, organization, make_user, make_job, make_candidate, make_application, age=timedelta(minutes=30)
    )

    evaluation = _sweep_until_settled(db, evaluation_id)

    assert evaluation.status == AIEvaluationStatus.COMPLETED.value
    assert evaluation.overall_score is not None


def test_a_long_stuck_evaluation_is_given_up_on(db, organization, make_user, make_job, make_candidate, make_application):
    evaluation_id = _stalled_evaluation(
        db, organization, make_user, make_job, make_candidate, make_application, age=timedelta(days=2)
    )

    evaluation = _sweep_until_settled(db, evaluation_id)

    assert evaluation.status == AIEvaluationStatus.FAILED.value
    assert "Timed out" in evaluation.error_message


def test_fresh_pending_work_is_left_alone(db, organization, make_user, make_job, make_candidate, make_application):
    """Still inside its window, so presumably still running somewhere."""
    evaluation_id = _stalled_evaluation(
        db, organization, make_user, make_job, make_candidate, make_application, age=timedelta(minutes=1)
    )

    resume_stalled_work()
    db.expire_all()

    assert db.get(AIEvaluation, evaluation_id).status == AIEvaluationStatus.PENDING.value
