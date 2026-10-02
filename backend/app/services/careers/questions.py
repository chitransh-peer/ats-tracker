"""Role-specific questions on the careers-page application form.

The form's fixed sections (personal details, profile, education, availability)
are the same for every job. This section changes with the JD: a design role is
asked about tools and design systems, a development role about languages and
frameworks, anything else about its most relevant experience. The job's own
screening questions, written by the recruiter, are appended after these.
"""

import re

from app.db.models.job import Job

_DESIGN_WORDS = ("design", "ui/ux", "ux", "ui ", "product designer", "visual", "graphic", "figma")
_DEV_WORDS = (
    "developer",
    "engineer",
    "software",
    "programmer",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "full stack",
    "full-stack",
    "devops",
    "sde",
    "architect",
)


def role_kind(job: Job) -> str:
    """'design', 'developer' or 'general', from the job title first, then its skills."""
    title = f" {(job.title or '').lower()} "
    if any(word in title for word in _DESIGN_WORDS):
        return "design"
    if any(word in title for word in _DEV_WORDS):
        return "developer"
    skills = " ".join(job.required_skills or []).lower()
    if re.search(r"\b(figma|sketch|adobe xd|wireframing|prototyping)\b", skills):
        return "design"
    if re.search(r"\b(python|java|javascript|typescript|react|node|golang|c\+\+|c#|\.net)\b", skills):
        return "developer"
    return "general"


def _q(key: str, label: str, kind: str = "text", required: bool = False, placeholder: str | None = None) -> dict:
    return {"key": key, "label": label, "type": kind, "required": required, "placeholder": placeholder}


def role_questions(job: Job) -> list[dict]:
    kind = role_kind(job)
    if kind == "design":
        questions = [
            _q("design_years", "How many years of experience do you have in UI/UX?", "number", True),
            _q("design_tools", "Which design tools do you use?", "text", True, "e.g. Figma, Sketch, Adobe XD"),
            _q(
                "relevant_project",
                "Share a project that demonstrates your experience relevant to this role.",
                "textarea",
                True,
                "A link and a few lines on your part in it",
            ),
            _q("design_systems", "Have you worked with design systems?", "yesno", True),
            _q("worked_with_developers", "Have you worked with developers?", "yesno", True),
        ]
    elif kind == "developer":
        questions = [
            _q("primary_language", "Primary programming language", "text", True, "e.g. Python, Java, TypeScript"),
            _q("language_years", "Years of experience with that language", "number", True),
            _q("frameworks", "Relevant frameworks", "text", False, "e.g. React, Django, Spring Boot"),
            _q(
                "technical_problem",
                "Describe a technically challenging problem you solved and how you approached it.",
                "textarea",
                True,
            ),
            _q(
                "skills_rating",
                "Which of the required skills for this role have you used in production? "
                f"({', '.join(job.required_skills[:6])})"
                if job.required_skills
                else "Which technologies have you used in production?",
                "textarea",
                False,
            ),
        ]
    else:
        questions = [
            _q(
                "relevant_project",
                "Briefly describe the experience that makes you a good fit for this role.",
                "textarea",
                True,
            ),
        ]

    for index, text in enumerate(job.screening_questions or []):
        if text and text.strip():
            questions.append(_q(f"screening_{index}", text.strip(), "textarea", True))
    return questions


def wants_portfolio_links(job: Job) -> bool:
    """GitHub / Behance / Dribbble are only asked of design and development roles."""
    return role_kind(job) in ("design", "developer")


def wants_sponsorship_question(job: Job) -> bool:
    """Sponsorship is only asked when the JD lists work-authorization requirements."""
    return bool(job.work_authorizations)
