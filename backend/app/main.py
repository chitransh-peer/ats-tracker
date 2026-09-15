from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import limiter

settings = get_settings()
configure_logging(settings.app_env)

if settings.sentry_dsn:
    # Deferred import: sentry_sdk is a real dependency either way (it's in
    # requirements.txt), but importing it only when actually configured keeps
    # "no DSN set" behaving as a true no-op rather than a library that's
    # merely quiet.
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            traces_sample_rate=settings.sentry_traces_sample_rate,
            # A stack trace is only useful with the request that triggered it —
            # PII scrubbing is Sentry's job at ingest, not something to disable here.
            send_default_pii=False,
        )
    except Exception:
        # Observability is a nice-to-have; it must never be the reason the API
        # itself fails to start. Logged rather than raised, and loud enough in
        # the startup log that a broken DSN doesn't go unnoticed.
        import logging

        logging.getLogger(__name__).exception(
            "Sentry initialization failed — continuing without error tracking."
        )

# The interactive docs publish the full API surface to anyone who can reach the
# host, so they are withheld in production. Set EXPOSE_API_DOCS=true to override
# (e.g. behind a VPN or an authenticating proxy).
_docs_enabled = settings.app_env != "production" or settings.expose_api_docs

app = FastAPI(
    title="ATS Tracker API",
    version="0.1.0",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(api_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
