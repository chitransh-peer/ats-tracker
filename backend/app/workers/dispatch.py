"""Handing work to the background queue, with a fallback for deployments that
have no queue.

The stack assumes a Redis broker and a separate worker process consuming it
(see docker-compose). A managed runtime like Cloud Run can easily have neither:
with no REDIS_URL the broker points at a localhost Redis that does not exist,
and even with one, nothing consumes the queue unless a worker service is also
deployed. In that shape `actor.send(...)` either raises a connection error --
failing the request that triggered it -- or succeeds into a queue no one reads,
which is worse, because it fails silently.

`dispatch` makes the useful cases work either way: it enqueues when a broker is
genuinely available, and otherwise runs the task inline, in the request. Inline
is a real trade-off -- the caller waits for the work -- so it is opt-in per call
site via `allow_inline`, reserved for jobs that are quick and that the user is
entitled to assume happened, above all the transactional email that carries a
credential.
"""

import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def broker_available() -> bool:
    """Whether a real broker is configured.

    The default REDIS_URL points at localhost, which on a managed runtime means
    "nothing is there" rather than a real broker, so it is treated as absent --
    the same reading app/core/rate_limit.py takes.
    """
    settings = get_settings()
    url = settings.redis_url
    return bool(url) and "localhost" not in url and "127.0.0.1" not in url


def dispatch(actor: Any, *args: Any, allow_inline: bool = False, **kwargs: Any) -> None:
    """Queue `actor`, or run it inline when there is no broker to queue it on.

    Never raises: the work here is a side effect of the request that triggered
    it, and a missing queue must not fail the underlying operation -- the same
    contract app/services/mail/service.send_email already keeps.
    """
    if broker_available():
        try:
            actor.send(*args, **kwargs)
            return
        except Exception:
            logger.exception("Could not enqueue %s; falling back to inline execution.", getattr(actor, "actor_name", actor))
    elif not allow_inline:
        # Nothing to queue onto and not safe to run here: say so loudly rather
        # than letting the caller believe the work is under way.
        logger.error(
            "No broker configured; %s was not run. Set REDIS_URL and deploy a worker.",
            getattr(actor, "actor_name", actor),
        )
        return

    if not allow_inline:
        return

    try:
        # .fn is the undecorated function behind the dramatiq actor.
        actor.fn(*args, **kwargs)
    except Exception:
        logger.exception("Inline execution of %s failed.", getattr(actor, "actor_name", actor))
