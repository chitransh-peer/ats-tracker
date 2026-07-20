import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AIEvaluationStatus, AIRecommendationLabel
from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.models.ai import AIEvaluation, AIEvaluationOverride, ParsedResume, ResumeParseRun
from app.db.models.application import Application
from app.db.models.candidate import Candidate
from app.db.models.job import Job
from app.services.ai.provider import AIProviderError, current_model_name, generate_structured

_SKILL_BUDGET = 80.0
_EXPERIENCE_BUDGET = 20.0

_SEMANTIC_PROMPT = """You are an expert technical recruiter. Compare the candidate profile \
against the job requirements and respond with ONLY a JSON object (no prose, no markdown \
fences) with these exact keys: recommendation_label (one of "strong_fit", "fit", \
"partial_fit", "not_a_fit"), match_score (number 0-100, your own independent estimate), \
strengths (array of short strings), gaps (array of short strings), risk_flags (array of short \
strings), confidence (number 0-100), explanation_text (2-3 sentence summary for a recruiter), \
suggested_interview_questions (array of 2-4 strings).

Job: {job_title}
Job description: {job_description}
Must-have skills: {required_skills}
Nice-to-have skills: {nice_to_have}
Required experience: {experience}

Candidate profile:
Current title: {candidate_title}
Skills: {candidate_skills}
Total experience (years): {candidate_experience}
Location: {candidate_location}
"""


@dataclass
class Criterion:
    type: str
    requirement: str
    weight: float
    candidate_value: str
    status: str
    score: float


@dataclass
class RuleScoreResult:
    total_score: float
    criteria: list[Criterion] = field(default_factory=list)
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)


def _parse_experience_years(experience: str | None) -> float | None:
    if not experience:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", experience)
    return float(match.group(1)) if match else None


def _candidate_skills(candidate: Candidate, parsed_resume: ParsedResume | None) -> list[str]:
    if parsed_resume and parsed_resume.skills:
        return parsed_resume.skills
    return candidate.skills or []


def _candidate_experience_years(candidate: Candidate, parsed_resume: ParsedResume | None) -> float | None:
    if parsed_resume and parsed_resume.total_experience_years is not None:
        return float(parsed_resume.total_experience_years)
    if candidate.total_experience_years is not None:
        return float(candidate.total_experience_years)
    return None


def rule_based_score(job: Job, candidate: Candidate, parsed_resume: ParsedResume | None) -> RuleScoreResult:
    candidate_skill_set = {s.strip().lower() for s in _candidate_skills(candidate, parsed_resume)}
    required = job.required_skills or []
    nice_to_have = job.nice_to_have or []

    criteria: list[Criterion] = []
    matched_skills: list[str] = []
    missing_skills: list[str] = []

    if required and nice_to_have:
        required_budget, nice_budget = _SKILL_BUDGET * 0.75, _SKILL_BUDGET * 0.25
    elif required:
        required_budget, nice_budget = _SKILL_BUDGET, 0.0
    elif nice_to_have:
        required_budget, nice_budget = 0.0, _SKILL_BUDGET
    else:
        required_budget, nice_budget = 0.0, 0.0

    for skill in required:
        weight = required_budget / len(required)
        is_match = skill.strip().lower() in candidate_skill_set
        criteria.append(
            Criterion("Required Skill", skill, round(weight, 2), skill if is_match else "—",
                      "Matched" if is_match else "Missing", weight if is_match else 0.0)
        )
        (matched_skills if is_match else missing_skills).append(skill)

    for skill in nice_to_have:
        weight = nice_budget / len(nice_to_have)
        is_match = skill.strip().lower() in candidate_skill_set
        criteria.append(
            Criterion("Nice to Have", skill, round(weight, 2), skill if is_match else "—",
                      "Matched" if is_match else "Missing", weight if is_match else 0.0)
        )
        (matched_skills if is_match else missing_skills).append(skill)

    required_years = _parse_experience_years(job.experience)
    candidate_years = _candidate_experience_years(candidate, parsed_resume)
    if required_years is not None and candidate_years is not None:
        meets_bar = candidate_years >= required_years
        criteria.append(
            Criterion("Experience", job.experience, _EXPERIENCE_BUDGET, f"{candidate_years} years",
                      "Matched" if meets_bar else "Partial",
                      _EXPERIENCE_BUDGET if meets_bar else _EXPERIENCE_BUDGET * (candidate_years / required_years))
        )

    total_possible = sum(c.weight for c in criteria)
    total_score = round(sum(c.score for c in criteria) / total_possible * 100, 2) if total_possible > 0 else 0.0

    return RuleScoreResult(total_score=total_score, criteria=criteria, matched_skills=matched_skills,
                            missing_skills=missing_skills)


def _recommendation_from_score(score: float) -> str:
    if score >= 75:
        return AIRecommendationLabel.STRONG_FIT.value
    if score >= 55:
        return AIRecommendationLabel.FIT.value
    if score >= 35:
        return AIRecommendationLabel.PARTIAL_FIT.value
    return AIRecommendationLabel.NOT_A_FIT.value


def _load_application(db: Session, organization_id: uuid.UUID, application_id: uuid.UUID) -> Application:
    application = db.get(Application, application_id)
    if application is None or application.organization_id != organization_id:
        raise NotFoundError("Application not found")
    return application


def _latest_parsed_resume(db: Session, candidate_id: uuid.UUID) -> ParsedResume | None:
    return db.scalar(
        select(ParsedResume)
        .join(ResumeParseRun, ResumeParseRun.id == ParsedResume.resume_parse_run_id)
        .where(ResumeParseRun.candidate_id == candidate_id)
        .order_by(ParsedResume.created_at.desc())
        .limit(1)
    )


def create_pending_evaluation(
    db: Session, *, organization_id: uuid.UUID, application_id: uuid.UUID, actor_id: uuid.UUID | None
) -> AIEvaluation:
    application = _load_application(db, organization_id, application_id)
    next_version = (
        db.scalar(
            select(AIEvaluation.version)
            .where(AIEvaluation.application_id == application.id)
            .order_by(AIEvaluation.version.desc())
            .limit(1)
        )
        or 0
    ) + 1

    evaluation = AIEvaluation(
        organization_id=organization_id,
        application_id=application.id,
        version=next_version,
        status=AIEvaluationStatus.PENDING.value,
        created_by=actor_id,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


def evaluate_application(db: Session, evaluation: AIEvaluation) -> AIEvaluation:
    evaluation.status = AIEvaluationStatus.PROCESSING.value
    db.commit()

    application = db.get(Application, evaluation.application_id)
    job = db.get(Job, application.job_id)
    candidate = db.get(Candidate, application.candidate_id)
    parsed_resume = _latest_parsed_resume(db, candidate.id)

    rule_result = rule_based_score(job, candidate, parsed_resume)
    evaluation.rule_score = rule_result.total_score
    evaluation.matched_skills = rule_result.matched_skills
    evaluation.missing_skills = rule_result.missing_skills

    try:
        prompt = _SEMANTIC_PROMPT.format(
            job_title=job.title,
            job_description=job.description or job.summary or "",
            required_skills=", ".join(job.required_skills or []),
            nice_to_have=", ".join(job.nice_to_have or []),
            experience=job.experience or "Not specified",
            candidate_title=candidate.current_title or "Unknown",
            candidate_skills=", ".join(_candidate_skills(candidate, parsed_resume)),
            candidate_experience=_candidate_experience_years(candidate, parsed_resume) or "Unknown",
            candidate_location=candidate.location or "Unknown",
        )
        fields = generate_structured(prompt)

        evaluation.semantic_score = fields.get("match_score")
        evaluation.recommendation_label = fields.get("recommendation_label") or _recommendation_from_score(
            rule_result.total_score
        )
        evaluation.strengths = fields.get("strengths") or []
        evaluation.gaps = fields.get("gaps") or []
        evaluation.risk_flags = fields.get("risk_flags") or []
        evaluation.suggested_interview_questions = fields.get("suggested_interview_questions") or []
        evaluation.confidence = fields.get("confidence")
        evaluation.explanation_text = fields.get("explanation_text")
        evaluation.model_name = current_model_name()
        evaluation.overall_score = round(0.6 * rule_result.total_score + 0.4 * float(evaluation.semantic_score), 2) \
            if evaluation.semantic_score is not None else rule_result.total_score
    except AIProviderError as exc:
        evaluation.error_message = str(exc)
        evaluation.overall_score = rule_result.total_score
        evaluation.recommendation_label = _recommendation_from_score(rule_result.total_score)

    evaluation.status = AIEvaluationStatus.COMPLETED.value
    db.commit()
    db.refresh(evaluation)
    return evaluation


def override_evaluation(
    db: Session, evaluation: AIEvaluation, *, actor_id: uuid.UUID | None, new_recommendation: str, note: str | None
) -> AIEvaluation:
    if evaluation.status != AIEvaluationStatus.COMPLETED.value:
        raise ValidationAppError("Only completed evaluations can be overridden")

    db.add(
        AIEvaluationOverride(
            evaluation_id=evaluation.id,
            overridden_by=actor_id,
            previous_recommendation=evaluation.recommendation_label,
            new_recommendation=new_recommendation,
            note=note,
        )
    )
    evaluation.recommendation_label = new_recommendation
    db.commit()
    db.refresh(evaluation)
    return evaluation


def get_evaluation(db: Session, organization_id: uuid.UUID, evaluation_id: uuid.UUID) -> AIEvaluation:
    evaluation = db.get(AIEvaluation, evaluation_id)
    if evaluation is None or evaluation.organization_id != organization_id:
        raise NotFoundError("AI evaluation not found")
    return evaluation


def get_latest_evaluation(db: Session, organization_id: uuid.UUID, application_id: uuid.UUID) -> AIEvaluation:
    evaluation = db.scalar(
        select(AIEvaluation)
        .where(AIEvaluation.organization_id == organization_id, AIEvaluation.application_id == application_id)
        .order_by(AIEvaluation.version.desc())
        .limit(1)
    )
    if evaluation is None:
        raise NotFoundError("No AI evaluation found for this application")
    return evaluation


def compare_jd_resume(db: Session, organization_id: uuid.UUID, application_id: uuid.UUID) -> dict:
    application = _load_application(db, organization_id, application_id)
    job = db.get(Job, application.job_id)
    candidate = db.get(Candidate, application.candidate_id)
    parsed_resume = _latest_parsed_resume(db, candidate.id)

    rule_result = rule_based_score(job, candidate, parsed_resume)

    return {
        "job_requirements": {
            "title": job.title,
            "required_skills": job.required_skills or [],
            "nice_to_have": job.nice_to_have or [],
            "experience": job.experience,
            "education": job.education,
            "location": job.location,
        },
        "candidate_profile": {
            "full_name": candidate.full_name,
            "skills": _candidate_skills(candidate, parsed_resume),
            "total_experience_years": _candidate_experience_years(candidate, parsed_resume),
            "location": candidate.location,
        },
        "criteria": [
            {
                "type": c.type,
                "requirement": c.requirement,
                "weight": c.weight,
                "candidate_value": c.candidate_value,
                "status": c.status,
                "score": round(c.score, 2),
            }
            for c in rule_result.criteria
        ],
        "total_score": rule_result.total_score,
    }
