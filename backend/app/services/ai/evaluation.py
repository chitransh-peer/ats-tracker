import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import AIEvaluationStatus, AIRecommendationLabel
from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.models.ai import AIEvaluation, AIEvaluationOverride, ParsedResume, ResumeParseRun
from app.db.models.application import Application
from app.db.models.candidate import Candidate
from app.db.models.job import Job
from app.services.ai.embeddings import embedding_similarity
from app.services.ai.provider import AIProviderError, current_model_name, generate_structured

_SKILL_BUDGET = 80.0
_EXPERIENCE_BUDGET = 20.0

_SEMANTIC_PROMPT = """You are an expert technical recruiter. Compare the candidate profile \
against the job requirements and respond with ONLY a JSON object (no prose, no markdown \
fences) with these exact keys: recommendation_label (one of "strong_fit", "fit", \
"partial_fit", "not_a_fit"), match_score (number 0-100, your own independent estimate), \
strengths (array of short strings), gaps (array of short strings), risk_flags (array of short \
strings), confidence (number 0-100), explanation_text (2-3 sentence summary for a recruiter), \
suggested_interview_questions (array of 2-4 strings), criteria (array with ONE object per \
must-have skill and per nice-to-have skill listed below; each object has keys: requirement \
(copy the skill text exactly), score (number 0-100), comment (one short phrase citing \
evidence from the résumé)). SCORING RULES for each requirement's score: 90-100 = direct, \
explicit experience with the exact tool/skill; 60-89 = strong adjacent, transferable, or \
domain-equivalent experience even if the exact term is absent (e.g. E911/public-safety comms \
counts strongly toward NG911; dispatch/AVTEC counts toward CAD); 30-59 = some related \
foundation but a clear gap; 0-29 = no related experience at all. Reward transferable \
experience the way an expert recruiter would — do not require exact keyword matches.), \
general_competencies (array of 3-6 objects capturing broad role fit BEYOND the listed skills — \
e.g. "Overall QA experience", "Test automation", "Domain/industry experience", "Documentation & \
reporting"; each object has keys: competency (short name), score (0-100 by the same scoring \
rules), comment (evidence from the résumé)).

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

Candidate résumé (verbatim extract — treat this as the primary source of truth \
and infer skills/experience from it even if the fields above are blank):
{candidate_resume}
"""

# Cap résumé text fed to the LLM. Kept generous because truncating too early
# hides later-page evidence (a candidate's most relevant experience is often
# below the fold), which makes the model under-credit real matches.
_RESUME_CHAR_LIMIT = 12000


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


def _skill_present(skill: str, candidate_skill_set: set[str], raw_text: str) -> bool:
    """True if the skill is in the structured skill list OR evidenced in the
    résumé text. The résumé-text fallback rescues scoring when the LLM skill
    extraction returns nothing (which is common), so a strong résumé is no longer
    graded as all-"Missing"."""
    s = skill.strip().lower()
    if not s:
        return False
    if s in candidate_skill_set:
        return True
    if not raw_text:
        return False
    if s in raw_text:
        return True
    # Multi-word skills (e.g. "Computer Aided Dispatch (CAD)") rarely appear
    # verbatim; credit them when all meaningful tokens appear as whole words.
    tokens = [t for t in re.split(r"[^a-z0-9]+", s) if len(t) >= 3]
    if tokens and all(re.search(rf"\b{re.escape(t)}\b", raw_text) for t in tokens):
        return True
    return False


def rule_based_score(job: Job, candidate: Candidate, parsed_resume: ParsedResume | None) -> RuleScoreResult:
    candidate_skill_set = {s.strip().lower() for s in _candidate_skills(candidate, parsed_resume)}
    raw_text = (parsed_resume.raw_text or "").lower() if parsed_resume and parsed_resume.raw_text else ""
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
        is_match = _skill_present(skill, candidate_skill_set, raw_text)
        criteria.append(
            Criterion(
                "Required Skill",
                skill,
                round(weight, 2),
                skill if is_match else "—",
                "Matched" if is_match else "Missing",
                weight if is_match else 0.0,
            )
        )
        (matched_skills if is_match else missing_skills).append(skill)

    for skill in nice_to_have:
        weight = nice_budget / len(nice_to_have)
        is_match = _skill_present(skill, candidate_skill_set, raw_text)
        criteria.append(
            Criterion(
                "Nice to Have",
                skill,
                round(weight, 2),
                skill if is_match else "—",
                "Matched" if is_match else "Missing",
                weight if is_match else 0.0,
            )
        )
        (matched_skills if is_match else missing_skills).append(skill)

    required_years = _parse_experience_years(job.experience)
    candidate_years = _candidate_experience_years(candidate, parsed_resume)
    if required_years is not None and candidate_years is not None:
        meets_bar = candidate_years >= required_years
        criteria.append(
            Criterion(
                "Experience",
                job.experience,
                _EXPERIENCE_BUDGET,
                f"{candidate_years} years",
                "Matched" if meets_bar else "Partial",
                _EXPERIENCE_BUDGET if meets_bar else _EXPERIENCE_BUDGET * (candidate_years / required_years),
            )
        )

    total_possible = sum(c.weight for c in criteria)
    total_score = round(sum(c.score for c in criteria) / total_possible * 100, 2) if total_possible > 0 else 0.0

    return RuleScoreResult(
        total_score=total_score, criteria=criteria, matched_skills=matched_skills, missing_skills=missing_skills
    )


def _job_text(job: Job) -> str:
    return " ".join(
        part
        for part in [
            job.title,
            job.summary,
            job.description,
            ", ".join(job.required_skills or []),
            ", ".join(job.nice_to_have or []),
            job.experience,
        ]
        if part
    )


def _candidate_text(candidate: Candidate, parsed_resume: ParsedResume | None) -> str:
    parts = [candidate.current_title, ", ".join(_candidate_skills(candidate, parsed_resume))]
    if parsed_resume and parsed_resume.raw_text:
        parts.append(parsed_resume.raw_text)
    return " ".join(part for part in parts if part)


# Weight given to each general role competency row (comparable to a required skill),
# so broad role fit meaningfully contributes alongside the JD's specific skills.
_COMPETENCY_WEIGHT = 15.0


def _status_from_pct(pct: float) -> str:
    return "Matched" if pct >= 70 else "Partial" if pct >= 30 else "Missing"


def _build_display_criteria(rule_result: "RuleScoreResult", llm_criteria: list, general_competencies: list) -> list[dict]:
    """Build the graded comparison rows: the JD's per-requirement grades (partial
    credit + evidence) plus broad general-competency rows that credit role fit
    beyond the listed skills, mirroring how an expert recruiter (or ChatGPT) reads
    a résumé. Falls back to the deterministic rule values when the LLM didn't grade."""
    graded = {str(c.get("requirement", "")).strip().lower(): c for c in (llm_criteria or []) if isinstance(c, dict)}
    rows: list[dict] = []
    for c in rule_result.criteria:
        row = {
            "type": c.type,
            "requirement": c.requirement,
            "weight": round(c.weight, 2),
            "candidate_value": c.candidate_value,
            "status": c.status,
            "score": round(c.score, 2),
        }
        g = graded.get(c.requirement.strip().lower())
        if g is not None and isinstance(g.get("score"), int | float):
            pct = max(0.0, min(100.0, float(g["score"])))
            row["score"] = round(c.weight * pct / 100, 2)
            row["status"] = _status_from_pct(pct)
            if g.get("comment"):
                row["candidate_value"] = str(g["comment"])
        rows.append(row)

    for gc in general_competencies or []:
        if not isinstance(gc, dict) or not isinstance(gc.get("score"), int | float):
            continue
        pct = max(0.0, min(100.0, float(gc["score"])))
        rows.append(
            {
                "type": "Competency",
                "requirement": str(gc.get("competency", "")).strip() or "Competency",
                "weight": _COMPETENCY_WEIGHT,
                "candidate_value": str(gc.get("comment", "")),
                "status": _status_from_pct(pct),
                "score": round(_COMPETENCY_WEIGHT * pct / 100, 2),
            }
        )
    return rows


def _score_from_criteria(rows: list[dict]) -> float:
    """Weighted total (0-100) across all graded rows — this is both the table's
    total and the skill/fit component of the overall score, so the two agree."""
    total_weight = sum(r["weight"] for r in rows)
    total_score = sum(r["score"] for r in rows)
    return round(total_score / total_weight * 100, 2) if total_weight > 0 else 0.0


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


def latest_scores(
    db: Session, organization_id: uuid.UUID, application_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[float | None, str | None]]:
    """Latest AI overall_score + recommendation per application, for list columns."""
    if not application_ids:
        return {}
    rows = db.execute(
        select(
            AIEvaluation.application_id,
            AIEvaluation.overall_score,
            AIEvaluation.recommendation_label,
            AIEvaluation.version,
        )
        .where(
            AIEvaluation.organization_id == organization_id,
            AIEvaluation.application_id.in_(application_ids),
        )
        .order_by(AIEvaluation.application_id, AIEvaluation.version.desc())
    ).all()
    result: dict[uuid.UUID, tuple[float | None, str | None]] = {}
    for row in rows:
        if row.application_id not in result:
            score = float(row.overall_score) if row.overall_score is not None else None
            result[row.application_id] = (score, row.recommendation_label)
    return result


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

    # Deterministic local semantic signal. Returns None when embeddings are
    # disabled/unavailable, in which case the LLM's match_score is used instead.
    embed_score = embedding_similarity(_job_text(job), _candidate_text(candidate, parsed_resume))

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
            candidate_resume=(parsed_resume.raw_text or "").strip()[:_RESUME_CHAR_LIMIT]
            if parsed_resume and parsed_resume.raw_text
            else "No résumé text available.",
        )
        fields = generate_structured(prompt)

        # Semantic signal combines two views when both exist: the deterministic
        # embedding similarity and the LLM's résumé-informed match_score. Averaging
        # keeps the reproducible backbone while crediting the LLM's holistic read
        # (it now sees the full résumé), which is what closes the gap with tools
        # like ChatGPT on strong-but-differently-worded résumés.
        raw_match = fields.get("match_score")
        llm_score = float(raw_match) if isinstance(raw_match, int | float) else None
        if embed_score is not None and llm_score is not None:
            evaluation.semantic_score = round((embed_score + llm_score) / 2, 2)
        elif embed_score is not None:
            evaluation.semantic_score = embed_score
        else:
            evaluation.semantic_score = llm_score
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

        # Skill/fit component: prefer the LLM's per-requirement graded score
        # (partial credit) over the binary text-match rule score when available.
        rows = _build_display_criteria(rule_result, fields.get("criteria") or [], fields.get("general_competencies") or [])
        evaluation.criteria = rows
        skill_component = _score_from_criteria(rows) if rows else rule_result.total_score
        w = get_settings().evaluation_skill_weight
        evaluation.overall_score = (
            round(w * skill_component + (1 - w) * float(evaluation.semantic_score), 2)
            if evaluation.semantic_score is not None
            else skill_component
        )
    except AIProviderError as exc:
        # The LLM narrative is unavailable, but a local embedding score can still
        # give a semantic signal on top of the rule score.
        evaluation.error_message = str(exc)
        evaluation.criteria = _build_display_criteria(rule_result, [], [])
        if embed_score is not None:
            w = get_settings().evaluation_skill_weight
            evaluation.semantic_score = embed_score
            evaluation.overall_score = round(w * rule_result.total_score + (1 - w) * embed_score, 2)
            evaluation.recommendation_label = _recommendation_from_score(evaluation.overall_score)
        else:
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
