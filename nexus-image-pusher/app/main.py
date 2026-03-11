import json
import os
import re
import subprocess
import tarfile
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

APP_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(APP_DIR / "templates"))

DEFAULT_REGISTRIES = [
    "registry.example.local:5000",
]

REGISTRY_OPTIONS = [
    r.strip() for r in os.getenv("REGISTRY_OPTIONS", ",".join(DEFAULT_REGISTRIES)).split(",") if r.strip()
]
NEXUS_USERNAME = os.getenv("NEXUS_USERNAME", "").strip()
NEXUS_PASSWORD = os.getenv("NEXUS_PASSWORD", "").strip()

jobs: Dict[str, Dict[str, Any]] = {}
jobs_lock = threading.Lock()

app = FastAPI(title="Nexus Image Pusher")


def _validate_metacode(metacode: str) -> None:
    if not re.fullmatch(r"[a-z]{4}", metacode):
        raise HTTPException(status_code=400, detail="메타코드는 소문자 4자리여야 합니다.")


def _set_job(job_id: str, **fields: Any) -> None:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job.update(fields)


def _add_log(job_id: str, line: str) -> None:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        logs = job.setdefault("logs", [])
        logs.append(line.strip())


def _extract_refs_from_archive(archive_path: str) -> List[str]:
    with tarfile.open(archive_path, mode="r:*") as tar:
        try:
            manifest_member = tar.getmember("manifest.json")
        except KeyError as exc:
            raise RuntimeError("manifest.json을 찾을 수 없습니다. docker save 형식인지 확인하세요.") from exc

        f = tar.extractfile(manifest_member)
        if f is None:
            raise RuntimeError("manifest.json을 읽을 수 없습니다.")

        manifest = json.loads(f.read().decode("utf-8"))
        refs: List[str] = []
        for item in manifest:
            refs.extend(item.get("RepoTags") or [])

        refs = [r for r in refs if ":" in r]
        if not refs:
            raise RuntimeError("RepoTags가 없습니다. 태그된 이미지 파일인지 확인하세요.")
        return refs


def _split_ref(ref: str) -> Tuple[str, str]:
    if ":" not in ref:
        raise RuntimeError(f"태그가 없는 이미지입니다: {ref}")
    name, tag = ref.rsplit(":", 1)
    return name, tag


def _dest_ref(source_ref: str, registry: str, metacode: str) -> str:
    name, tag = _split_ref(source_ref)
    parts = name.split("/")
    if parts and ("." in parts[0] or ":" in parts[0] or parts[0] == "localhost"):
        parts = parts[1:]
    if parts and parts[0] == "library":
        parts = parts[1:]

    if not parts:
        raise RuntimeError(f"이미지 경로를 변환할 수 없습니다: {source_ref}")

    rewritten = "/".join(parts)
    return f"{registry}/{metacode}/{rewritten}:{tag}"


def _run_push(job_id: str, archive_path: str, refs: List[str], registry: str, metacode: str) -> None:
    destinations: List[str] = []
    total = len(refs)

    for index, source_ref in enumerate(refs, start=1):
        dest = _dest_ref(source_ref, registry, metacode)
        destinations.append(dest)

        percent = 20 + int((index - 1) / max(total, 1) * 70)
        _set_job(
            job_id,
            status="running",
            progress=percent,
            message=f"[{index}/{total}] push 준비: {source_ref} -> {dest}",
            destinations=destinations,
        )

        cmd = [
            "skopeo",
            "copy",
            "--src-tls-verify=false",
            "--dest-tls-verify=false",
            "--dest-creds",
            f"{NEXUS_USERNAME}:{NEXUS_PASSWORD}",
            f"docker-archive:{archive_path}:{source_ref}",
            f"docker://{dest}",
        ]

        _add_log(job_id, " ".join(cmd))
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        assert proc.stdout is not None
        for line in proc.stdout:
            _add_log(job_id, line)

        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"push 실패: {source_ref} (exit code {rc})")

    _set_job(
        job_id,
        status="completed",
        progress=100,
        message="모든 이미지 push가 완료되었습니다.",
        destinations=destinations,
    )


def _worker(job_id: str, archive_path: str, registry: str, metacode: str) -> None:
    try:
        _set_job(job_id, status="running", progress=10, message="아카이브 분석 중...")
        refs = _extract_refs_from_archive(archive_path)
        _set_job(job_id, progress=20, message="이미지 태그 확인 완료", images=refs)
        _run_push(job_id, archive_path, refs, registry, metacode)
    except Exception as exc:
        _set_job(job_id, status="failed", message=str(exc))
        _add_log(job_id, f"ERROR: {exc}")
    finally:
        try:
            os.remove(archive_path)
        except OSError:
            pass


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        "index.html",
        {
            "request": request,
            "registries": REGISTRY_OPTIONS,
            "default_registry": REGISTRY_OPTIONS[0] if REGISTRY_OPTIONS else "",
        },
    )


@app.post("/api/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    registry: str = Form(...),
    metacode: str = Form(...),
) -> JSONResponse:
    metacode = metacode.strip()
    _validate_metacode(metacode)

    if registry not in REGISTRY_OPTIONS:
        raise HTTPException(status_code=400, detail="허용되지 않은 넥서스 주소입니다.")
    if not NEXUS_USERNAME or not NEXUS_PASSWORD:
        raise HTTPException(status_code=500, detail="NEXUS_USERNAME/NEXUS_PASSWORD 환경 변수가 필요합니다.")

    if not file.filename:
        raise HTTPException(status_code=400, detail="업로드할 파일이 필요합니다.")

    suffix = Path(file.filename).suffix or ".tar"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)
        archive_path = tmp.name

    job_id = str(uuid.uuid4())
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "progress": 5,
            "message": "업로드 완료. 작업 대기 중...",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "images": [],
            "destinations": [],
            "logs": [],
        }

    background_tasks.add_task(_worker, job_id, archive_path, registry, metacode)

    return JSONResponse({"job_id": job_id})


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> JSONResponse:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
        return JSONResponse(job)
