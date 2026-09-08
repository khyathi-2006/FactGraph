"""Thin JSON-returning client for an OpenAI-compatible chat completions endpoint."""

from __future__ import annotations

import json
import random
import time
from typing import Any

import httpx

from .config import LLM_BASE_URL, resolve_api_key

TERMINAL_STATUSES = {400, 401, 402, 403}
MAX_ATTEMPTS = 4


class LLMRequestError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(f"LLM request failed with status {status_code}: {message}")
        self.status_code = status_code
        self.message = message


def _extract_json_object(content: str) -> dict[str, Any]:
    """Parse a JSON object from a model reply, tolerating code fences and prose."""

    text = content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"model reply contained no JSON object: {content[:400]}")
    return json.loads(text[start : end + 1])


def request_json_object(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int = 8000,
) -> dict[str, Any]:
    """Call the model and return its reply parsed as a JSON object.

    Retries only rate limits and upstream failures, with bounded backoff.
    """

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": max_output_tokens,
    }
    headers = {
        "Authorization": f"Bearer {resolve_api_key()}",
        "Content-Type": "application/json",
    }

    last_error: LLMRequestError | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = httpx.post(
            f"{LLM_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=180.0,
        )
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            return _extract_json_object(content)

        last_error = LLMRequestError(response.status_code, response.text[:500])
        if response.status_code in TERMINAL_STATUSES or attempt == MAX_ATTEMPTS:
            raise last_error

        retry_after = response.headers.get("Retry-After")
        delay = float(retry_after) if retry_after else min(2**attempt, 20) + random.random()
        time.sleep(delay)

    raise last_error
