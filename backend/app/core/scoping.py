"""Row-level visibility scoping for job-scoped and interview-scoped roles.

Resource-level RBAC (`app/core/permissions.py`) answers "can this role do X".
This module answers the finer-grained question a role check alone can't:
"is this specific record theirs". Super Admin, Admin, Executive, and Recruiter
are unscoped (unchanged, org-wide visibility). Hiring Manager and Interviewer
are restricted to records tied to jobs/interviews they own or sit on.
"""

from app.core.enums import RoleName

_UNSCOPED_ROLES = {
    RoleName.SUPER_ADMIN.value,
    RoleName.ADMIN.value,
    RoleName.EXECUTIVE.value,
    RoleName.RECRUITER.value,
}

_SCOPED_ROLES = (RoleName.HIRING_MANAGER.value, RoleName.INTERVIEWER.value)


def scoped_roles(roles: list[str]) -> set[str]:
    """Subset of {"hiring_manager", "interviewer"} restricting this viewer's
    visibility, or an empty set if they hold any org-wide role."""
    if any(role in _UNSCOPED_ROLES for role in roles):
        return set()
    return {role for role in _SCOPED_ROLES if role in roles}
