"""
Explicit role -> permission matrix. This is the single source of truth for
default authorization; it is used to seed the role_permissions table so that
runtime checks always query the database (allowing future per-org overrides)
rather than branching on role name in scattered conditionals.
"""

from app.core.enums import PermissionAction, PermissionResource, RoleName

Permission = tuple[PermissionResource, PermissionAction]

_ALL_RESOURCES = list(PermissionResource)

_MANAGE_ALL: set[Permission] = {(r, PermissionAction.MANAGE) for r in _ALL_RESOURCES}

_ADMIN_RESTRICTED: set[Permission] = {
    (r, a)
    for r in _ALL_RESOURCES
    for a in PermissionAction
    if r != PermissionResource.ORGANIZATION or a != PermissionAction.DELETE
}

_EXECUTIVE_READ_ONLY: set[Permission] = {
    (r, PermissionAction.READ)
    for r in _ALL_RESOURCES
    if r not in {PermissionResource.SETTINGS}
}

_RECRUITER_OPERATIONAL: set[Permission] = {
    (PermissionResource.JOB, PermissionAction.CREATE),
    (PermissionResource.JOB, PermissionAction.READ),
    (PermissionResource.JOB, PermissionAction.UPDATE),
    (PermissionResource.CANDIDATE, PermissionAction.CREATE),
    (PermissionResource.CANDIDATE, PermissionAction.READ),
    (PermissionResource.CANDIDATE, PermissionAction.UPDATE),
    (PermissionResource.APPLICATION, PermissionAction.CREATE),
    (PermissionResource.APPLICATION, PermissionAction.READ),
    (PermissionResource.APPLICATION, PermissionAction.UPDATE),
    (PermissionResource.PIPELINE, PermissionAction.UPDATE),
    (PermissionResource.PIPELINE, PermissionAction.READ),
    (PermissionResource.AI_EVALUATION, PermissionAction.READ),
    (PermissionResource.AI_EVALUATION, PermissionAction.UPDATE),
    (PermissionResource.INTERVIEW, PermissionAction.CREATE),
    (PermissionResource.INTERVIEW, PermissionAction.READ),
    (PermissionResource.INTERVIEW, PermissionAction.UPDATE),
    (PermissionResource.OFFER, PermissionAction.CREATE),
    (PermissionResource.OFFER, PermissionAction.READ),
    (PermissionResource.OFFER, PermissionAction.UPDATE),
    (PermissionResource.TEMPLATE, PermissionAction.READ),
    (PermissionResource.TEMPLATE, PermissionAction.CREATE),
    (PermissionResource.CLIENT, PermissionAction.READ),
    (PermissionResource.VENDOR, PermissionAction.READ),
    (PermissionResource.REPORT, PermissionAction.READ),
}

_HIRING_MANAGER_JOB_SCOPED: set[Permission] = {
    (PermissionResource.JOB, PermissionAction.READ),
    (PermissionResource.CANDIDATE, PermissionAction.READ),
    (PermissionResource.APPLICATION, PermissionAction.READ),
    (PermissionResource.PIPELINE, PermissionAction.READ),
    (PermissionResource.AI_EVALUATION, PermissionAction.READ),
    (PermissionResource.INTERVIEW, PermissionAction.READ),
    (PermissionResource.INTERVIEW, PermissionAction.UPDATE),
    (PermissionResource.OFFER, PermissionAction.READ),
    (PermissionResource.OFFER, PermissionAction.CREATE),
}

_INTERVIEWER_SCOPED: set[Permission] = {
    (PermissionResource.CANDIDATE, PermissionAction.READ),
    (PermissionResource.APPLICATION, PermissionAction.READ),
    (PermissionResource.INTERVIEW, PermissionAction.READ),
    (PermissionResource.INTERVIEW, PermissionAction.UPDATE),
}

_CANDIDATE_SELF_SERVICE: set[Permission] = {
    (PermissionResource.JOB, PermissionAction.READ),
    (PermissionResource.APPLICATION, PermissionAction.CREATE),
    (PermissionResource.APPLICATION, PermissionAction.READ),
}

ROLE_PERMISSIONS: dict[RoleName, set[Permission]] = {
    RoleName.SUPER_ADMIN: _MANAGE_ALL,
    RoleName.ADMIN: _ADMIN_RESTRICTED,
    RoleName.EXECUTIVE: _EXECUTIVE_READ_ONLY,
    RoleName.RECRUITER: _RECRUITER_OPERATIONAL,
    RoleName.HIRING_MANAGER: _HIRING_MANAGER_JOB_SCOPED,
    RoleName.INTERVIEWER: _INTERVIEWER_SCOPED,
    RoleName.CANDIDATE: _CANDIDATE_SELF_SERVICE,
}


def permission_key(resource: PermissionResource, action: PermissionAction) -> str:
    return f"{resource.value}:{action.value}"


def role_grants(role: RoleName, resource: PermissionResource, action: PermissionAction) -> bool:
    granted = ROLE_PERMISSIONS.get(role, set())
    return (resource, action) in granted or (resource, PermissionAction.MANAGE) in granted
