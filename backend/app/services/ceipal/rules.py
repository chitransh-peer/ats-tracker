"""What being a Ceipal candidate means elsewhere in the app.

Kept apart from the import service so the AI services can ask without
pulling the importer in.
"""

from app.core.exceptions import ValidationAppError

CEIPAL_ORIGIN = "ceipal"

NOT_SCORED_MESSAGE = (
    "This candidate was imported from Ceipal, where they are already verified. AI review does not run for Ceipal candidates."
)


def is_ceipal(candidate) -> bool:
    return candidate is not None and candidate.origin == CEIPAL_ORIGIN


def ensure_ai_allowed(candidate) -> None:
    """Candidates from Ceipal are never scored or parsed by AI. Every way
    into AI for a candidate goes through this."""
    if is_ceipal(candidate):
        raise ValidationAppError(NOT_SCORED_MESSAGE)
