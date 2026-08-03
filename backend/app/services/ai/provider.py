"""Thin wrapper around whichever LLM provider is configured.

Callers must treat any failure from `generate_structured` as non-fatal: the AI
design rule for this project is that the LLM is never the only scoring engine,
so rule-based results must still be usable when the provider is unreachable,
misconfigured, or returns malformed output.
"""

import json
import re

import httpx

from app.core.config import get_settings

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT_SECONDS = 30.0


class AIProviderError(Exception):
    pass


def _strip_code_fence(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text


def _call_openrouter(prompt: str) -> str:
    settings = get_settings()
    if not settings.openrouter_api_key or not settings.openrouter_model:
        raise AIProviderError("OpenRouter is not configured (missing API key or model)")

    try:
        response = httpx.post(
            _OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": settings.openrouter_model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                # Enough room to grade every requirement without rambling.
                "max_tokens": 1400,
                "temperature": 0.2,
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AIProviderError(f"OpenRouter request failed: {exc}") from exc

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise AIProviderError(f"Unexpected OpenRouter response shape: {data}") from exc


def _call_ollama(prompt: str) -> str:
    settings = get_settings()
    try:
        response = httpx.post(
            f"{settings.ollama_base_url}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "format": "json", "stream": False},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AIProviderError(f"Ollama request failed: {exc}") from exc

    data = response.json()
    try:
        return data["response"]
    except KeyError as exc:
        raise AIProviderError(f"Unexpected Ollama response shape: {data}") from exc


def current_model_name() -> str:
    settings = get_settings()
    if settings.ai_provider == "openrouter":
        return settings.openrouter_model or "openrouter"
    return settings.ollama_model


def generate_structured(prompt: str) -> dict:
    """Sends `prompt` to the configured provider and parses the reply as JSON.

    Raises AIProviderError on any failure — network, config, or malformed output.
    """
    settings = get_settings()
    if settings.ai_provider == "openrouter":
        raw_text = _call_openrouter(prompt)
    elif settings.ai_provider == "ollama":
        raw_text = _call_ollama(prompt)
    else:
        raise AIProviderError(f"Unknown AI provider: {settings.ai_provider}")

    try:
        return json.loads(_strip_code_fence(raw_text))
    except json.JSONDecodeError as exc:
        raise AIProviderError(f"Provider returned non-JSON output: {raw_text[:200]}") from exc
