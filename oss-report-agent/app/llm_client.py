from __future__ import annotations

import requests

from .config import settings


class LLMError(RuntimeError):
    pass


def generate_text(prompt: str, timeout_seconds: int = 180) -> str:
    provider = settings.llm_provider
    if provider == "openai":
        return _generate_with_openai(prompt=prompt, timeout_seconds=timeout_seconds)
    return _generate_with_ollama(prompt=prompt, timeout_seconds=timeout_seconds)


def health_check() -> dict[str, str]:
    provider = settings.llm_provider
    if provider == "openai":
        endpoint = settings.openai_base_url.rstrip("/") + "/v1/models"
        headers = _openai_headers()
    else:
        endpoint = settings.ollama_base_url.rstrip("/") + "/api/tags"
        headers = {}

    try:
        resp = requests.get(endpoint, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        raise LLMError(f"LLM endpoint unreachable ({provider}): {exc}") from exc

    return {
        "status": "ok",
        "provider": provider,
        "endpoint": endpoint,
        "model": settings.selected_model(),
    }


def _generate_with_ollama(prompt: str, timeout_seconds: int) -> str:
    endpoint = settings.ollama_base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    try:
        response = requests.post(endpoint, json=payload, timeout=timeout_seconds)
    except requests.RequestException as exc:
        raise LLMError(f"Failed to call Ollama endpoint {endpoint}: {exc}") from exc

    if response.status_code >= 400:
        raise LLMError(f"Ollama returned HTTP {response.status_code}: {response.text}")

    data = response.json()
    result = data.get("response", "").strip()
    if not result:
        raise LLMError("Ollama returned an empty response body")
    return result


def _generate_with_openai(prompt: str, timeout_seconds: int) -> str:
    endpoint = settings.openai_base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": "You are a precise infrastructure reporting assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers=_openai_headers(),
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        raise LLMError(f"Failed to call OpenAI-compatible endpoint {endpoint}: {exc}") from exc

    if response.status_code >= 400:
        raise LLMError(f"OpenAI-compatible API returned HTTP {response.status_code}: {response.text}")

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise LLMError("OpenAI-compatible API returned no choices")

    message = choices[0].get("message", {})
    content = str(message.get("content", "")).strip()
    if not content:
        raise LLMError("OpenAI-compatible API returned an empty response body")
    return content


def _openai_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.openai_api_key:
        headers["Authorization"] = f"Bearer {settings.openai_api_key}"
    return headers
