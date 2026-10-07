from fastapi import APIRouter

from app.api.v1.routes import (
    ai,
    applications,
    audit,
    auth,
    bench,
    candidates,
    careers,
    ceipal,
    clients,
    hotlists,
    imports,
    interviews,
    jobs,
    offers,
    onboarding,
    pipeline,
    reports,
    roles,
    settings,
    templates,
    users,
    vendors,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(clients.router)
api_router.include_router(vendors.router)
# Before imports: GET /imports/ceipal must not be read as /imports/{job_id}.
api_router.include_router(ceipal.router)
api_router.include_router(imports.router)
api_router.include_router(jobs.router)
api_router.include_router(candidates.router)
api_router.include_router(applications.router)
api_router.include_router(pipeline.router)
api_router.include_router(careers.router)
api_router.include_router(interviews.router)
api_router.include_router(offers.router)
api_router.include_router(onboarding.router)
api_router.include_router(templates.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)
api_router.include_router(ai.router)
api_router.include_router(bench.router)
api_router.include_router(hotlists.router)
