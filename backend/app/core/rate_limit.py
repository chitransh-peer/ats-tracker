"""Rate limiting for the handful of endpoints an attacker or a bug can hammer
without ever authenticating: login, password reset, and the public careers
apply form. Everything else is left alone — an authenticated user hitting a
normal endpoint too fast is not the threat model here.

Backed by Redis if REDIS_URL is provided, otherwise falls back to in-memory
storage for serverless deployments like Cloud Run.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

# Usar redis_url si está definida y no es localhost, de lo contrario usar fallback en memoria
settings = get_settings()
storage_uri = getattr(settings, "redis_url", None)

if not storage_uri or "localhost" in storage_uri or "127.0.0.1" in storage_uri:
    storage_uri = "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    default_limits=[],
    # Fail open. Without this, a Redis that is configured but unreachable makes
    # the limiter raise, and because the limit is checked before the endpoint
    # body, the failure surfaces as a 500 on /auth/login -- nobody can sign in
    # at all because the thing counting sign-in attempts is down.
    #
    # The trade is deliberate: while storage is unavailable the limit stops
    # being enforced, so brute-force protection lapses until it recovers. An
    # outage of the whole login flow is the worse of the two, and slowapi logs
    # the swallowed error either way.
    swallow_errors=True,
)