from __future__ import annotations

from pathlib import Path
import json
import yaml

SUPPORTED_EXTENSIONS = {".txt", ".log", ".json", ".yaml", ".yml"}


def _is_supported_file(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in SUPPORTED_EXTENSIONS:
        return True
    # Support files like "<hostname>_check" without extension.
    return suffix == "" and path.name.endswith("_check")


def _read_file(path: Path) -> str:
    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".json":
        try:
            parsed = json.loads(raw)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return raw

    if suffix in {".yaml", ".yml"}:
        try:
            parsed = yaml.safe_load(raw)
            return yaml.safe_dump(parsed, allow_unicode=True, sort_keys=False)
        except yaml.YAMLError:
            return raw

    return raw


def collect_check_results(base_path: str, max_chars_per_file: int = 16000) -> list[dict[str, str]]:
    base = Path(base_path)
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"Input path does not exist or is not a directory: {base_path}")

    collected: list[dict[str, str]] = []
    for file_path in sorted(base.rglob("*")):
        if not file_path.is_file():
            continue
        if not _is_supported_file(file_path):
            continue

        content = _read_file(file_path)
        if len(content) > max_chars_per_file:
            content = content[:max_chars_per_file] + "\n... [TRUNCATED]"

        collected.append({
            "path": str(file_path),
            "content": content,
        })

    return collected
