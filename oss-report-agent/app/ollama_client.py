from __future__ import annotations

import requests


class OllamaError(RuntimeError):
    pass


def generate_with_ollama(
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: int = 180,
) -> str:
    endpoint = base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=timeout_seconds)
    except requests.RequestException as exc:
        raise OllamaError(f"Failed to call Ollama endpoint {endpoint}: {exc}") from exc

    if response.status_code >= 400:
        raise OllamaError(f"Ollama returned HTTP {response.status_code}: {response.text}")

    data = response.json()
    result = data.get("response", "").strip()
    if not result:
        raise OllamaError("Ollama returned an empty response body")

    return result
