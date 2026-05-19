from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .redaction import redact


class AuditLogger:
    def __init__(self, name: str = "ocp_openstack_diagnostic_mcp.audit"):
        self.logger = logging.getLogger(name)

    def record(self, event: str, **fields: Any) -> None:
        payload = {"ts": datetime.now(UTC).isoformat(), "event": event, **redact(fields)}
        self.logger.info(json.dumps(payload, ensure_ascii=True, sort_keys=True))

    @contextmanager
    def span(self, tool: str, cloud_id: str | None):
        trace_id = str(uuid4())
        start = time.perf_counter()
        self.record("tool_start", trace_id=trace_id, tool=tool, cloud_id=cloud_id)
        try:
            yield trace_id
            self.record("tool_success", trace_id=trace_id, tool=tool, cloud_id=cloud_id, latency_ms=round((time.perf_counter() - start) * 1000, 2))
        except Exception as exc:
            self.record("tool_error", trace_id=trace_id, tool=tool, cloud_id=cloud_id, error_type=type(exc).__name__, latency_ms=round((time.perf_counter() - start) * 1000, 2))
            raise

