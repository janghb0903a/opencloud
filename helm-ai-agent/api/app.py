from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import yaml
from llm_backend import build_user_prompt, call_llm
from builder import write_chart
from schemas import ChartResponse
import asyncio, os

# 동시성 제한(폭주 방지)
sem = asyncio.Semaphore(int(os.getenv("API_MAX_CONCURRENCY", "3")))
app = FastAPI(title="AI Manifest → Helm (Bedrock)")

class ConvertBody(BaseModel):
    chart_name: str
    manifest_yaml: str
    defaults: Optional[dict] = {"ingress": {"enabled": False}}

@app.post("/api/convert")
async def convert(body: ConvertBody):
    try:
        list(yaml.safe_load_all(body.manifest_yaml))
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Invalid YAML: {e}"})
    prompt = build_user_prompt(body.chart_name, body.manifest_yaml, body.defaults or {})
    async with sem:
        try:
            raw = call_llm(prompt)
            resp = ChartResponse(**raw)
            zpath = write_chart(resp)
            return FileResponse(zpath, filename=f"{resp.chart_name}.zip", media_type="application/zip")
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
