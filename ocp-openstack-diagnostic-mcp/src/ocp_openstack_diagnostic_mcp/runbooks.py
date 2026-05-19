from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunbookStore:
    root: Path

    def search(self, query: str, limit: int = 10) -> list[dict[str, str]]:
        needle = query.lower()
        hits = []
        for path in sorted(self.root.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            if needle in path.stem.lower() or needle in text.lower():
                hits.append({"runbook_id": path.stem, "title": _title(text, path.stem), "path": str(path)})
            if len(hits) >= limit:
                break
        return hits

    def get(self, runbook_id: str) -> dict[str, str]:
        safe_id = runbook_id.replace("/", "").replace("\\", "")
        path = self.root / f"{safe_id}.md"
        if not path.exists():
            return {"error": "not_found", "runbook_id": runbook_id}
        text = path.read_text(encoding="utf-8")
        return {"runbook_id": safe_id, "title": _title(text, safe_id), "content": text}


def _title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback

