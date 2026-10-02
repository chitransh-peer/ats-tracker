"""A filled-in careers-page application, for tests that post to /apply."""

RESUME_PDF = b"%PDF-1.4\n%mock content for a test\n%%EOF"

# Covers every role kind; answers to questions a job does not ask are ignored.
_ROLE_ANSWERS = (
    '{"design_years": "4", "design_tools": "Figma", "relevant_project": "A checkout redesign",'
    ' "design_systems": "Yes", "worked_with_developers": "Yes", "primary_language": "Python",'
    ' "language_years": "5", "technical_problem": "Cut a slow report from minutes to seconds"}'
)


def application_form(full_name: str, email: str, **overrides) -> dict:
    form = {
        "full_name": full_name,
        "email": email,
        "phone": "+1-555-0100",
        "location": "Austin, TX",
        "current_title": "Designer",
        "total_experience_years": "5",
        "highest_qualification": "B.Des",
        "notice_period": "30 days",
        "expected_ctc": "120000",
        "work_arrangement_ok": "Yes",
        "role_answers": _ROLE_ANSWERS,
    }
    form.update(overrides)
    return form


def resume_file(data: bytes = RESUME_PDF, name: str = "resume.pdf") -> dict:
    return {"resume": (name, data, "application/pdf")}
