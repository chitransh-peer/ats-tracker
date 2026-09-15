"""Rate limiting for the handful of endpoints an attacker or a bug can hammer
without ever authenticating: login, password reset, and the public careers
apply form. Everything else is left alone — an authenticated user hitting a
normal endpoint too fast is not the threat model here.

Backed by the same Redis instance as the task queue, so limits are shared
across every worker process rather than reset whenever uvicorn reloads or a
new process picks up the request.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=get_settings().redis_url,
    # Applied only where explicitly decorated below — see main.py for why a
    # blanket default was deliberately not set.
    default_limits=[],
)
