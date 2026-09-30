"""The database request gate and the report cache."""

import asyncio
import time

import httpx

from app.core.db_gate import DatabaseRequestGate
from app.core.ttl_cache import TTLCache


def _slow_app(release: asyncio.Event):
    async def app(scope, receive, send):
        if scope["path"].endswith("/slow"):
            await release.wait()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    return app


def test_the_gate_admits_only_as_many_api_requests_as_it_has_slots():
    async def scenario():
        release = asyncio.Event()
        gate = DatabaseRequestGate(_slow_app(release), slots=1, wait_timeout=0.2)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gate), base_url="http://t") as client:
            first = asyncio.create_task(client.get("/api/v1/slow"))
            await asyncio.sleep(0.05)
            queued_too_long = await client.get("/api/v1/fast")
            outside_the_api = await client.get("/health")
            release.set()
            return (await first).status_code, queued_too_long, outside_the_api.status_code

    first, queued, health = asyncio.run(scenario())

    assert first == 200
    assert queued.status_code == 503
    assert queued.headers["retry-after"] == "1"
    assert health == 200  # not gated


def test_a_queued_request_goes_through_once_a_slot_frees():
    async def scenario():
        release = asyncio.Event()
        gate = DatabaseRequestGate(_slow_app(release), slots=1, wait_timeout=5)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gate), base_url="http://t") as client:
            first = asyncio.create_task(client.get("/api/v1/slow"))
            await asyncio.sleep(0.05)
            second = asyncio.create_task(client.get("/api/v1/fast"))
            await asyncio.sleep(0.05)
            assert not second.done()
            release.set()
            return (await first).status_code, (await second).status_code

    assert asyncio.run(scenario()) == (200, 200)


def test_the_cache_serves_a_fresh_value_without_recomputing():
    cache = TTLCache(ttl_seconds=60)
    calls = []

    assert cache.get_or_compute("k", lambda: calls.append(1) or "first") == "first"
    assert cache.get_or_compute("k", lambda: calls.append(1) or "second") == "first"
    assert len(calls) == 1


def test_an_expired_value_is_recomputed():
    cache = TTLCache(ttl_seconds=0.01)
    cache.get_or_compute("k", lambda: "old")
    time.sleep(0.02)

    assert cache.get_or_compute("k", lambda: "new") == "new"


def test_while_one_request_refreshes_others_get_the_previous_value():
    cache = TTLCache(ttl_seconds=0.01)
    cache.get_or_compute("k", lambda: "old")
    time.sleep(0.02)
    seen_during_refresh = []

    def refresh():
        seen_during_refresh.append(cache.get_or_compute("k", lambda: "not me"))
        return "new"

    assert cache.get_or_compute("k", refresh) == "new"
    assert seen_during_refresh == ["old"]


def test_a_failed_refresh_does_not_leave_the_key_stuck():
    cache = TTLCache(ttl_seconds=60)

    def boom():
        raise RuntimeError("database down")

    try:
        cache.get_or_compute("k", boom)
    except RuntimeError:
        pass

    assert cache.get_or_compute("k", lambda: "recovered") == "recovered"
