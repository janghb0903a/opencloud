from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .collector import collect_check_results
from .config import settings
from .llm_client import generate_text
from .report_builder import build_prompt, wrap_report


def run_generation(input_path: str | None = None, output_path: str | None = None) -> str:
    resolved_input = settings.resolve_input_path(input_path)
    collected = collect_check_results(resolved_input)

    if not collected:
        raise RuntimeError(f"No supported check output files found in: {resolved_input}")

    prompt = build_prompt(collected=collected, input_path=resolved_input)
    llm_result = generate_text(
        prompt=prompt,
        timeout_seconds=settings.request_timeout_seconds,
    )
    report = wrap_report(llm_result, input_path=resolved_input, model=settings.selected_model())

    target = Path(output_path) if output_path else _default_output_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report, encoding="utf-8")

    return str(target)


def _default_output_path() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(settings.output_dir) / f"cloud_report_{ts}.md"
