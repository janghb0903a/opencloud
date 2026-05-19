import asyncio
import json
import os
from typing import Any, AsyncGenerator

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
PROMETHEUS_TOKEN = os.getenv("PROMETHEUS_TOKEN", "")
AI_BACKEND_URL = os.getenv("AI_BACKEND_URL", "http://localhost:8001/v1")
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gpt-oss-120b")
AI_API_KEY = os.getenv("AI_API_KEY", "")

METADATA_CACHE: dict[str, Any] = {"metrics": [], "indexed": {}}
CACHE_LOCK = asyncio.Lock()

app = FastAPI(title="Grafana AI Assistant API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3)
    selected_metrics: list[str] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    dashboard_json: str
    model: str


def _build_auth_header(token: str) -> dict[str, str]:
    if not token:
        return {}
    if token.lower().startswith("bearer "):
        return {"Authorization": token}
    return {"Authorization": f"Bearer {token}"}


async def refresh_metadata() -> None:
    headers = _build_auth_header(PROMETHEUS_TOKEN)
    url = f"{PROMETHEUS_URL.rstrip('/')}/api/v1/metadata"

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        body = response.json()

    data = body.get("data", {})
    metric_names = sorted(data.keys())

    async with CACHE_LOCK:
        METADATA_CACHE["metrics"] = metric_names
        METADATA_CACHE["indexed"] = data


@app.on_event("startup")
async def on_startup() -> None:
    try:
        await refresh_metadata()
    except Exception:
        async with CACHE_LOCK:
            METADATA_CACHE["metrics"] = []
            METADATA_CACHE["indexed"] = {}


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "grafana-ai-assistant-backend", "health": "/healthz"}


@app.get("/api/metrics/search")
async def search_metrics(q: str = Query(default="", max_length=100)) -> dict[str, Any]:
    async with CACHE_LOCK:
        metrics = METADATA_CACHE["metrics"]

    if not q:
        return {"items": metrics[:100]}

    ql = q.lower()
    result = [m for m in metrics if ql in m.lower()][:100]
    return {"items": result}


def build_messages(user_prompt: str, selected_metrics: list[str]) -> list[dict[str, str]]:
    selected = selected_metrics[:30]
    selected_context = "\n".join(f"- {m}" for m in selected) if selected else "- (none)"

    system_prompt = (
        "You generate Grafana dashboard JSON only. "
        "Return a single strict JSON object without markdown fences or explanations. "
        "Use Prometheus datasource and include practical panels. "
        "Required root keys: title (string), panels (array), schemaVersion (number), version (number). "
        "Do not wrap output with prose."
    )
    user_context = (
        "User request:\n"
        f"{user_prompt}\n\n"
        "Candidate metrics:\n"
        f"{selected_context}\n\n"
        "Output constraints:\n"
        "1) Strict JSON\n"
        "2) Grafana dashboard schema compatible\n"
        "3) PromQL in panel targets\n"
        "4) Root must include title, panels, schemaVersion, version\n"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_context},
    ]


async def generate_dashboard(prompt: str, selected_metrics: list[str]) -> str:
    headers = {"Content-Type": "application/json"}
    if AI_API_KEY:
        headers["Authorization"] = f"Bearer {AI_API_KEY}"

    payload = {
        "model": AI_MODEL_NAME,
        "messages": build_messages(prompt, selected_metrics),
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{AI_BACKEND_URL.rstrip('/')}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        body = resp.json()

    choices = body.get("choices", [])
    if not choices:
        raise HTTPException(status_code=502, detail="AI backend returned no choices")

    content = choices[0].get("message", {}).get("content", "").strip()
    if not content:
        raise HTTPException(status_code=502, detail="AI backend returned empty content")
    return content


@app.post("/api/dashboard/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest) -> GenerateResponse:
    try:
        dashboard_json = await generate_dashboard(req.prompt, req.selected_metrics)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"AI backend error: {exc}") from exc

    return GenerateResponse(dashboard_json=dashboard_json, model=AI_MODEL_NAME)


async def stream_dashboard(req: GenerateRequest) -> AsyncGenerator[bytes, None]:
    headers = {"Content-Type": "application/json"}
    if AI_API_KEY:
        headers["Authorization"] = f"Bearer {AI_API_KEY}"

    payload = {
        "model": AI_MODEL_NAME,
        "messages": build_messages(req.prompt, req.selected_metrics),
        "temperature": 0.2,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{AI_BACKEND_URL.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    normalized = line[5:].strip() if line.startswith("data:") else line.strip()
                    yield f"data: {normalized}\n\n".encode("utf-8")
        yield b"data: [DONE]\n\n"
    except Exception as exc:
        error_payload = json.dumps({"error": str(exc)})
        yield f"data: {error_payload}\n\n".encode("utf-8")


@app.post("/api/dashboard/stream")
async def generate_stream(req: GenerateRequest) -> StreamingResponse:
    return StreamingResponse(stream_dashboard(req), media_type="text/event-stream")
