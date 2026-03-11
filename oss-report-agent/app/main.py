from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Lock, Thread
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from .config import settings
from .llm_client import LLMError, health_check
from .service import run_generation


app = FastAPI(title="Open Source Cloud Report Agent", version="0.3.0")


class GenerateRequest(BaseModel):
    input_path: str | None = None
    output_path: str | None = None


class GenerateResponse(BaseModel):
    report_path: str


class GenerateAsyncResponse(BaseModel):
    job_id: str
    status: str


class GenerateJobStatusResponse(BaseModel):
    job_id: str
    status: str
    report_path: str | None = None
    error: str | None = None


_JOBS: dict[str, dict[str, str | None]] = {}
_JOBS_LOCK = Lock()


def _get_report_dir() -> Path:
    return Path(settings.output_dir)


def _resolve_report_file(report_name: str) -> Path:
    if "/" in report_name or "\\" in report_name or report_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid report name")
    report_dir = _get_report_dir().resolve()
    candidate = (report_dir / report_name).resolve()
    if report_dir not in candidate.parents and candidate != report_dir:
        raise HTTPException(status_code=400, detail="Invalid report path")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    return candidate


def _set_job(job_id: str, status: str, report_path: str | None = None, error: str | None = None) -> None:
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "status": status,
            "report_path": report_path,
            "error": error,
        }


def _run_job(job_id: str, input_path: str | None, output_path: str | None) -> None:
    try:
        _set_job(job_id, "running")
        report_path = run_generation(input_path=input_path, output_path=output_path)
        _set_job(job_id, "completed", report_path=report_path)
    except Exception as exc:
        _set_job(job_id, "failed", error=str(exc))


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>OSS Report Agent</title>
    <style>
      :root {
        --bg: #f5f7fb;
        --card: #ffffff;
        --text: #1f2937;
        --muted: #6b7280;
        --line: #d1d5db;
        --brand: #0f766e;
        --brand-2: #115e59;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: "Segoe UI", sans-serif;
        background: radial-gradient(circle at 10% 10%, #e6fffa 0%, var(--bg) 40%);
        color: var(--text);
      }
      .wrap {
        max-width: 980px;
        margin: 32px auto;
        padding: 0 16px;
      }
      .card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
      }
      h1, h2 { margin: 0 0 12px; }
      .desc { color: var(--muted); margin-bottom: 16px; }
      .row { display: grid; gap: 10px; grid-template-columns: 1fr 1fr; }
      @media (max-width: 840px) { .row { grid-template-columns: 1fr; } }
      label { font-weight: 600; font-size: 14px; display: block; margin-bottom: 6px; }
      input {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 10px 12px;
        font-size: 14px;
      }
      button {
        background: var(--brand);
        color: white;
        border: 0;
        border-radius: 10px;
        padding: 10px 16px;
        font-weight: 700;
        cursor: pointer;
      }
      button:hover { background: var(--brand-2); }
      .actions { margin-top: 14px; display: flex; gap: 8px; }
      .status {
        margin-top: 12px;
        font-size: 14px;
        color: var(--muted);
        white-space: pre-wrap;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
      }
      th, td {
        border-bottom: 1px solid var(--line);
        text-align: left;
        padding: 10px 8px;
      }
      a { color: #0c4a6e; text-decoration: none; }
      a:hover { text-decoration: underline; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>Open Source Cloud Report Agent</h1>
        <p class="desc">Generate monthly check reports from uploaded check files and download markdown results.</p>
        <div class="row">
          <div>
            <label for="inputPath">Input Path (optional)</label>
            <input id="inputPath" placeholder="Leave empty to use CHECK_INPUT_PATH or CHECK_PATH_PATTERN" />
          </div>
          <div>
            <label for="outputPath">Output File Path (optional)</label>
            <input id="outputPath" placeholder="/input/checks/reports/monthly_report.md" />
          </div>
        </div>
        <div class="actions">
          <button id="genBtn">Generate Report</button>
          <button id="refreshBtn" type="button">Refresh List</button>
        </div>
        <div id="status" class="status"></div>
      </div>

      <div class="card">
        <h2>Generated Reports</h2>
        <table>
          <thead>
            <tr>
              <th>File</th>
              <th>Modified</th>
              <th>Size (bytes)</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody id="reportBody"></tbody>
        </table>
      </div>
    </div>
    <script>
      const statusEl = document.getElementById("status");
      const bodyEl = document.getElementById("reportBody");

      async function refreshReports() {
        bodyEl.innerHTML = "";
        const res = await fetch("/api/reports");
        const data = await res.json();
        if (!data.reports || data.reports.length === 0) {
          bodyEl.innerHTML = "<tr><td colspan='4'>No reports found.</td></tr>";
          return;
        }
        for (const r of data.reports) {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${r.name}</td>
            <td>${r.modified}</td>
            <td>${r.size}</td>
            <td>
              <a href="/api/reports/${encodeURIComponent(r.name)}" target="_blank">View</a>
              |
              <a href="/api/reports/${encodeURIComponent(r.name)}/download">Download</a>
            </td>
          `;
          bodyEl.appendChild(tr);
        }
      }

      async function generateReport() {
        const inputPath = document.getElementById("inputPath").value || null;
        const outputPath = document.getElementById("outputPath").value || null;
        statusEl.textContent = "Submitting job...";
        try {
          const res = await fetch("/generate/async", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ input_path: inputPath, output_path: outputPath }),
          });

          const ct = (res.headers.get("content-type") || "").toLowerCase();
          if (!ct.includes("application/json")) {
            const bodyText = await res.text();
            statusEl.textContent =
              "Failed: non-JSON response (likely ingress/proxy timeout). " +
              "HTTP " + res.status + " " + bodyText.slice(0, 200);
            return;
          }

          const data = await res.json();
          if (!res.ok) {
            statusEl.textContent = "Failed: " + (data.detail || "unknown error");
            return;
          }

          await pollJobStatus(data.job_id);
        } catch (err) {
          statusEl.textContent = "Request failed: " + err;
        }
      }

      async function pollJobStatus(jobId) {
        const started = Date.now();
        const timeoutMs = 15 * 60 * 1000;
        while (Date.now() - started < timeoutMs) {
          const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
          const data = await res.json();
          if (!res.ok) {
            statusEl.textContent = "Failed: " + (data.detail || "job status error");
            return;
          }
          if (data.status === "completed") {
            statusEl.textContent = "Completed: " + data.report_path;
            await refreshReports();
            return;
          }
          if (data.status === "failed") {
            statusEl.textContent = "Failed: " + (data.error || "unknown error");
            return;
          }
          statusEl.textContent = "Generating report... (" + data.status + ")";
          await new Promise((r) => setTimeout(r, 2000));
        }
        statusEl.textContent = "Failed: job polling timed out";
      }

      document.getElementById("genBtn").addEventListener("click", generateReport);
      document.getElementById("refreshBtn").addEventListener("click", refreshReports);
      refreshReports();
    </script>
  </body>
</html>
"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ollama")
def health_ollama() -> dict[str, str]:
    if settings.llm_provider != "ollama":
        raise HTTPException(status_code=400, detail="LLM_PROVIDER is not 'ollama'")
    try:
        return health_check()
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/health/llm")
def health_llm() -> dict[str, str]:
    try:
        return health_check()
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/reports")
def list_reports() -> dict[str, object]:
    report_dir = _get_report_dir()
    if not report_dir.exists():
        return {"output_dir": str(report_dir), "reports": []}

    reports = []
    for path in sorted(report_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = path.stat()
        reports.append(
            {
                "name": path.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return {"output_dir": str(report_dir), "reports": reports}


@app.get("/api/reports/{report_name}", response_class=HTMLResponse)
def view_report(report_name: str) -> str:
    path = _resolve_report_file(report_name)
    content = path.read_text(encoding="utf-8", errors="ignore")
    escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<pre style='white-space:pre-wrap;font-family:Consolas,monospace'>{escaped}</pre>"


@app.get("/api/reports/{report_name}/download")
def download_report(report_name: str) -> FileResponse:
    path = _resolve_report_file(report_name)
    return FileResponse(path=str(path), media_type="text/markdown", filename=path.name)


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    try:
        output = run_generation(input_path=req.input_path, output_path=req.output_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return GenerateResponse(report_path=output)


@app.post("/generate/async", response_model=GenerateAsyncResponse)
def generate_async(req: GenerateRequest) -> GenerateAsyncResponse:
    job_id = str(uuid4())
    _set_job(job_id, "queued")
    thread = Thread(target=_run_job, args=(job_id, req.input_path, req.output_path), daemon=True)
    thread.start()
    return GenerateAsyncResponse(job_id=job_id, status="queued")


@app.get("/api/jobs/{job_id}", response_model=GenerateJobStatusResponse)
def get_job_status(job_id: str) -> GenerateJobStatusResponse:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return GenerateJobStatusResponse(
        job_id=job_id,
        status=str(job["status"]),
        report_path=job["report_path"],
        error=job["error"],
    )
