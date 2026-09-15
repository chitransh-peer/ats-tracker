import pytest

from app.core.config import get_settings
from app.core.enums import AIEvaluationStatus, CandidateDocumentType, RoleName
from app.core.exceptions import ValidationAppError
from app.db.models.ai import AIEvaluationOverride
from app.services.ai import evaluation as evaluation_service
from app.services.ai import resume_parsing as resume_parsing_service
from app.services.ai.provider import AIProviderError
from app.services.candidates.service import add_document

_W = get_settings().evaluation_skill_weight  # skill vs semantic blend weight


def _blend(skill: float, semantic: float) -> float:
    return _W * skill + (1 - _W) * semantic


def _canned_semantic_response(*_args, **_kwargs):
    return {
        "recommendation_label": "fit",
        "match_score": 70,
        "strengths": ["Strong Python background"],
        "gaps": ["No Kubernetes experience"],
        "risk_flags": [],
        "confidence": 80,
        "explanation_text": "Solid overall match with a couple of gaps.",
        "suggested_interview_questions": ["Describe a recent Python project."],
    }


def test_rule_based_score_weights_required_over_nice_to_have(make_job, make_candidate):
    job = make_job(required_skills=["Python", "SQL"], nice_to_have=["Docker"])
    candidate = make_candidate(skills=["Python", "Docker"])

    result = evaluation_service.rule_based_score(job, candidate, parsed_resume=None)

    assert "Python" in result.matched_skills
    assert "Docker" in result.matched_skills
    assert "SQL" in result.missing_skills
    assert 0 < result.total_score < 100


def test_evaluate_application_falls_back_to_rule_score_when_ai_unavailable(
    db, make_job, make_candidate, make_application, monkeypatch
):
    def _raise(*_args, **_kwargs):
        raise AIProviderError("provider not configured")

    monkeypatch.setattr(evaluation_service, "generate_structured", _raise)
    # Isolate this test from whatever EMBEDDINGS_ENABLED is set to in the env.
    monkeypatch.setattr(evaluation_service, "embedding_similarity", lambda *_a, **_k: None)

    job = make_job(required_skills=["Python"], nice_to_have=[])
    candidate = make_candidate(skills=["Python"])
    application = make_application(candidate=candidate, job=job)

    evaluation = evaluation_service.create_pending_evaluation(
        db, organization_id=application.organization_id, application_id=application.id, actor_id=None
    )
    evaluation = evaluation_service.evaluate_application(db, evaluation)

    assert evaluation.status == AIEvaluationStatus.COMPLETED.value
    assert evaluation.rule_score == 100.0
    assert evaluation.overall_score == 100.0
    assert evaluation.semantic_score is None
    assert evaluation.error_message is not None
    assert evaluation.recommendation_label == "strong_fit"


def test_evaluate_application_blends_semantic_score_when_ai_succeeds(
    db, make_job, make_candidate, make_application, monkeypatch
):
    monkeypatch.setattr(evaluation_service, "generate_structured", _canned_semantic_response)
    # This test asserts the LLM's own match_score is used, so disable embeddings.
    monkeypatch.setattr(evaluation_service, "embedding_similarity", lambda *_a, **_k: None)

    job = make_job(required_skills=["Python"], nice_to_have=[])
    candidate = make_candidate(skills=["Python"])
    application = make_application(candidate=candidate, job=job)

    evaluation = evaluation_service.create_pending_evaluation(
        db, organization_id=application.organization_id, application_id=application.id, actor_id=None
    )
    evaluation = evaluation_service.evaluate_application(db, evaluation)

    assert evaluation.status == AIEvaluationStatus.COMPLETED.value
    assert evaluation.semantic_score == 70
    assert evaluation.overall_score == pytest.approx(_blend(100, 70), abs=0.01)
    assert evaluation.strengths == ["Strong Python background"]
    assert evaluation.error_message is None


def test_embedding_and_llm_scores_are_averaged_when_both_available(
    db, make_job, make_candidate, make_application, monkeypatch
):
    monkeypatch.setattr(evaluation_service, "generate_structured", _canned_semantic_response)
    # Simulate embeddings enabled + a deterministic cosine result of 80.
    monkeypatch.setattr(evaluation_service, "embedding_similarity", lambda *_a, **_k: 80.0)

    job = make_job(required_skills=["Python"], nice_to_have=[])
    candidate = make_candidate(skills=["Python"])
    application = make_application(candidate=candidate, job=job)

    evaluation = evaluation_service.create_pending_evaluation(
        db, organization_id=application.organization_id, application_id=application.id, actor_id=None
    )
    evaluation = evaluation_service.evaluate_application(db, evaluation)

    # Semantic = average of embedding (80) and the LLM's match_score (70) = 75.
    assert evaluation.semantic_score == pytest.approx(75.0, abs=0.01)
    assert evaluation.overall_score == pytest.approx(_blend(100, 75), abs=0.01)
    # Narrative still comes from the LLM.
    assert evaluation.strengths == ["Strong Python background"]


def test_embedding_score_used_even_when_llm_unavailable(db, make_job, make_candidate, make_application, monkeypatch):
    def _raise(*_args, **_kwargs):
        raise AIProviderError("provider not configured")

    monkeypatch.setattr(evaluation_service, "generate_structured", _raise)
    monkeypatch.setattr(evaluation_service, "embedding_similarity", lambda *_a, **_k: 50.0)

    job = make_job(required_skills=["Python"], nice_to_have=[])
    candidate = make_candidate(skills=["Python"])
    application = make_application(candidate=candidate, job=job)

    evaluation = evaluation_service.create_pending_evaluation(
        db, organization_id=application.organization_id, application_id=application.id, actor_id=None
    )
    evaluation = evaluation_service.evaluate_application(db, evaluation)

    assert evaluation.status == AIEvaluationStatus.COMPLETED.value
    assert evaluation.semantic_score == 50.0
    assert evaluation.overall_score == pytest.approx(_blend(100, 50), abs=0.01)
    assert evaluation.error_message is not None  # LLM failure is still recorded


def test_override_preserves_original_recommendation(db, make_job, make_candidate, make_application, monkeypatch):
    monkeypatch.setattr(evaluation_service, "generate_structured", _canned_semantic_response)
    job = make_job(required_skills=["Python"], nice_to_have=[])
    candidate = make_candidate(skills=["Python"])
    application = make_application(candidate=candidate, job=job)
    evaluation = evaluation_service.create_pending_evaluation(
        db, organization_id=application.organization_id, application_id=application.id, actor_id=None
    )
    evaluation = evaluation_service.evaluate_application(db, evaluation)
    original_recommendation = evaluation.recommendation_label

    evaluation = evaluation_service.override_evaluation(
        db, evaluation, actor_id=None, new_recommendation="not_a_fit", note="Recruiter disagrees"
    )

    assert evaluation.recommendation_label == "not_a_fit"
    override = db.query(AIEvaluationOverride).filter_by(evaluation_id=evaluation.id).one()
    assert override.previous_recommendation == original_recommendation
    assert override.new_recommendation == "not_a_fit"
    assert override.note == "Recruiter disagrees"


def test_cannot_override_pending_evaluation(db, make_job, make_candidate, make_application):
    job = make_job()
    candidate = make_candidate()
    application = make_application(candidate=candidate, job=job)
    evaluation = evaluation_service.create_pending_evaluation(
        db, organization_id=application.organization_id, application_id=application.id, actor_id=None
    )

    with pytest.raises(ValidationAppError, match="Only completed evaluations"):
        evaluation_service.override_evaluation(db, evaluation, actor_id=None, new_recommendation="fit", note=None)


def test_parse_resume_stores_structured_fields(db, make_candidate, monkeypatch):
    monkeypatch.setattr(
        resume_parsing_service,
        "generate_structured",
        lambda *_args, **_kwargs: {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "phone": None,
            "location": "Bengaluru",
            "total_experience_years": 5,
            "skills": ["Python", "FastAPI"],
            "education": [{"degree": "B.Tech", "school": "IIT", "year": "2019"}],
            "work_history": [],
        },
    )

    candidate = make_candidate()
    document = add_document(
        db,
        candidate,
        document_type=CandidateDocumentType.RESUME.value,
        file_name="resume.txt",
        content_type="text/plain",
        data=b"Jane Doe resume text",
        uploaded_by=None,
    )

    run = resume_parsing_service.create_pending_run(
        db, organization_id=candidate.organization_id, candidate_id=candidate.id, document_id=document.id
    )
    run = resume_parsing_service.parse_resume(db, run)

    assert run.status == "completed"
    assert run.parsed_resume.full_name == "Jane Doe"
    assert run.parsed_resume.skills == ["Python", "FastAPI"]


def test_only_recruiter_and_above_can_trigger_evaluation(
    client, make_user, make_job, make_candidate, make_application, auth_headers
):
    candidate_role_user, password = make_user(role_names=[RoleName.CANDIDATE.value])
    headers = auth_headers(candidate_role_user.email, password)
    application = make_application(candidate=make_candidate(), job=make_job())

    response = client.post(f"/api/v1/ai/evaluate-application/{application.id}", headers=headers)

    assert response.status_code == 403


def test_compare_jd_resume_endpoint_is_rule_based_only(
    client, make_user, make_job, make_candidate, make_application, auth_headers
):
    user, password = make_user(role_names=[RoleName.RECRUITER.value])
    headers = auth_headers(user.email, password)
    job = make_job(required_skills=["Python"], nice_to_have=[])
    candidate = make_candidate(skills=["Python"])
    application = make_application(candidate=candidate, job=job)

    response = client.get(f"/api/v1/ai/compare/jd-resume/{application.id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_score"] == 100.0
    assert body["criteria"][0]["status"] == "Matched"
