from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from .redaction import redact


class AuditLogger:
    def __init__(self, name: str = "ocp_k8s_diagnostic_mcp.audit"):
        self.logger = logging.getLogger(name)

    def record(self, event: str, **fields: Any) -> None:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "event": event,
            **redact(fields),
        }
        self.logger.info(json.dumps(payload, ensure_ascii=True, sort_keys=True))

