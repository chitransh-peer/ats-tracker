from fastapi import APIRouter

from app.api.v1.routes import (
    ai,
    applications,
    audit,
    auth,
    candidates,
    careers,
    clients,
    interviews,
    jobs,
    offers,
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
api_router.include_router(jobs.router)
api_router.include_router(candidates.router)
api_router.include_router(applications.router)
api_router.include_router(pipeline.router)
api_router.include_router(careers.router)
api_router.include_router(interviews.router)
api_router.include_router(offers.router)
api_router.include_router(templates.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)
api_router.include_router(ai.router)
