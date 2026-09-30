"""Let no more requests at the database than there are connections for them.

Endpoints are synchronous: each runs on a worker thread (40 of them), while
the instance holds only `db_pool_size + db_max_overflow` connections (7 by
default). A request takes a connection in one step (the auth dependencies)
and needs a thread again for the next (the endpoint, serializing the
response, closing the session). Under a burst, all 40 threads could end up
blocked waiting for a connection while the requests holding the 7
connections waited for a thread to finish on. Nothing moved until the pool
timed out 15 seconds later, and then every waiting request failed with a
500 at once. A load test of 20 recruiters produced exactly that.

This gate admits only as many API requests as there are connections. The
rest wait here, in the event loop, where waiting costs no thread, so every
admitted request is guaranteed both a connection and a thread and always
finishes. A request that waits longer than `wait_timeout` gets a 503 with
Retry-After rather than hanging.
"""

import asyncio
import json

from starlette.types import ASGIApp, Receive, Scope, Send

_BUSY_BODY = json.dumps({"detail": "The server is busy. Try again in a moment."}).encode()


class DatabaseRequestGate:
    def __init__(self, app: ASGIApp, *, slots: int, wait_timeout: float, path_prefix: str = "/api/") -> None:
        self.app = app
        self.slots = slots
        self.wait_timeout = wait_timeout
        self.path_prefix = path_prefix
        self._loop: asyncio.AbstractEventLoop | None = None
        self._semaphore: asyncio.Semaphore | None = None

    def _gate(self) -> asyncio.Semaphore:
        # One semaphore per event loop: the server runs one, but the test
        # client starts a fresh loop per test and a semaphore cannot move
        # between loops.
        loop = asyncio.get_running_loop()
        if self._loop is not loop:
            self._loop = loop
            self._semaphore = asyncio.Semaphore(self.slots)
        return self._semaphore

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(self.path_prefix):
            await self.app(scope, receive, send)
            return

        gate = self._gate()
        try:
            await asyncio.wait_for(gate.acquire(), timeout=self.wait_timeout)
        except TimeoutError:
            await send(
                {
                    "type": "http.response.start",
                    "status": 503,
                    "headers": [(b"content-type", b"application/json"), (b"retry-after", b"1")],
                }
            )
            await send({"type": "http.response.body", "body": _BUSY_BODY})
            return
        try:
            await self.app(scope, receive, send)
        finally:
            gate.release()
