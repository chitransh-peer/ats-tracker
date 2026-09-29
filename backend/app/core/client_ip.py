"""The caller's real IP address, as far as it can be trusted.

Behind Cloud Run the socket peer is Google's front end, so the client address
only survives in X-Forwarded-For. That header is a list the client can start
itself: whatever it sends arrives first, and each proxy *appends* the address
it saw. Only the entries our own proxies added are trustworthy, so the client
is read that many hops from the right -- never from the left, where a caller
can put any address it likes and walk past every per-IP rate limit.

`trusted_proxy_hops` is how many proxies we run behind: 0 locally (no proxy,
use the socket peer), 1 on Cloud Run's own URL, 2 if a load balancer is added
in front of it.
"""

from starlette.requests import Request

from app.core.config import get_settings


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    hops = get_settings().trusted_proxy_hops
    if hops <= 0:
        return peer

    forwarded = request.headers.get("x-forwarded-for", "")
    entries = [entry.strip() for entry in forwarded.split(",") if entry.strip()]
    if len(entries) < hops:
        # Fewer entries than proxies we expect: the request did not come the
        # way we think it did, so none of the header can be relied on.
        return peer
    return entries[-hops]
