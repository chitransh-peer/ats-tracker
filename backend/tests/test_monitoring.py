"""Error tracking wiring and the health check an uptime monitor would poll.

The Sentry setup is the more fragile of the two: it's optional (a no-op with
no DSN configured), but importing `sentry_sdk` at all was enough to crash this
app once already — its Starlette integration unconditionally imports Jinja2
regardless of whether the app renders any templates. These tests exist
because "should be a no-op" is exactly the kind of claim that quietly stops
being true when a dependency changes.
"""

import subprocess
import sys


def _run_probe(code: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Runs `code` in a fresh interpreter.

    A fresh process is required because `sentry_sdk.init` mutates global
    state — re-running it in the same interpreter as the rest of the test
    suite would leak a client into every other test.
    """
    import os

    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=full_env, timeout=30
    )


def test_app_boots_without_a_sentry_dsn_configured():
    result = _run_probe(
        "import app.main; print('OK')", env={"SENTRY_DSN": ""}
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_app_boots_with_a_sentry_dsn_configured():
    """Regression test: sentry_sdk's Starlette integration used to crash here
    with `ImportError: jinja2 must be installed`, because this is a pure JSON
    API that has no reason to depend on a template engine. Fixed by adding
    jinja2 as a dependency and by wrapping sentry_sdk.init so a future
    integration failure degrades to "no monitoring" instead of "no API"."""
    result = _run_probe(
        "import app.main; import sentry_sdk; print('CLIENT_ACTIVE', sentry_sdk.get_client().is_active())",
        env={"SENTRY_DSN": "https://public@o0.ingest.sentry.io/0"},
    )
    assert result.returncode == 0, result.stderr
    assert "CLIENT_ACTIVE True" in result.stdout


def test_health_endpoint_requires_no_authentication(client):
    """This is what an uptime monitor polls — it must never depend on a
    valid token, or a rotated secret takes down the health check along with
    everything else."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
