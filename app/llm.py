"""OpenRouter chat client (OpenAI-compatible) with model fallback."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from app.config import get_settings

settings = get_settings()

_HEADERS = {
    "Authorization": f"Bearer {settings.openrouter_api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": settings.app_url,
    "X-Title": settings.app_name,
}


class LLMError(RuntimeError):
    pass


def _post(payload: dict[str, Any], timeout: float = 120.0) -> dict[str, Any]:
    if not settings.openrouter_api_key:
        raise LLMError("OPENROUTER_API_KEY is not configured. Copy .env.example to .env and set your key.")
    url = f"{settings.openrouter_base_url}/chat/completions"
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, headers=_HEADERS, json=payload)
    if resp.status_code >= 400:
        raise LLMError(f"OpenRouter error {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.5,
    max_tokens: int = 900,
    models: list[str] | None = None,
) -> dict[str, Any]:
    """Return the assistant message dict. Tries each model in the fallback chain."""
    model_list = models or settings.model_list
    last_error: Exception | None = None
    for model in model_list:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            data = _post(payload)
            choice = data["choices"][0]["message"]
            choice["_model"] = model
            return choice
        except (LLMError, KeyError, IndexError) as exc:
            last_error = exc
            continue
    raise LLMError(f"All models failed. Last error: {last_error}")


def chat_stream(
    messages: list[dict[str, Any]],
    temperature: float = 0.6,
    max_tokens: int = 900,
    models: list[str] | None = None,
) -> Iterator[str]:
    """Yield text tokens for a plain (tool-free) completion."""
    model_list = models or settings.model_list
    last_error: Exception | None = None
    for model in model_list:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        try:
            url = f"{settings.openrouter_base_url}/chat/completions"
            with httpx.Client(timeout=120.0) as client:
                with client.stream("POST", url, headers=_HEADERS, json=payload) as resp:
                    if resp.status_code >= 400:
                        resp.read()
                        raise LLMError(f"OpenRouter error {resp.status_code}: {resp.text[:300]}")
                    for line in resp.iter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        chunk = line[len("data:"):].strip()
                        if chunk == "[DONE]":
                            return
                        import json

                        try:
                            obj = json.loads(chunk)
                            delta = obj["choices"][0]["delta"].get("content")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
            return
        except (LLMError, httpx.HTTPError) as exc:
            last_error = exc
            continue
    raise LLMError(f"All models failed. Last error: {last_error}")
