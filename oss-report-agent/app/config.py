from __future__ import annotations

from dataclasses import dataclass
import os
from datetime import datetime


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama").lower()
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "http://localhost:8000")
    openai_model: str = os.getenv("OPENAI_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    check_input_path: str = os.getenv("CHECK_INPUT_PATH", "")
    check_path_pattern: str = os.getenv("CHECK_PATH_PATTERN", "/tmp/check_{date}")
    output_dir: str = os.getenv("OUTPUT_DIR", "/tmp/reports")
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "180"))

    def resolve_input_path(self, explicit_path: str | None = None) -> str:
        if explicit_path:
            return explicit_path
        if self.check_input_path:
            return self.check_input_path
        today = datetime.now().strftime("%Y%m%d")
        return self.check_path_pattern.format(date=today)

    def selected_model(self) -> str:
        if self.llm_provider == "openai":
            return self.openai_model
        return self.ollama_model


settings = Settings()
