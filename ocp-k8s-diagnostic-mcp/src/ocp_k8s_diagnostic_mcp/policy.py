from __future__ import annotations

import re
from typing import Any

from .errors import DiagnosticError

HARDCODED_DENYLIST = {
    "create",
    "update",
    "patch",
    "delete",
    "deletecollection",
    "exec",
    "debug",
    "port-forward",
    "cordon",
    "drain",
    "scale",
    "apply",
    "rollout restart",
    "kubectl",
    "helm",
    "bash",
    "ssh",
}


class PolicyGuard:
    def __init__(self, policies: dict[str, Any] | None = None):
        self.policies = policies or {}
        configured = self.policies.get("deny_functions", []) + self.policies.get("deny_verbs", [])
        self.denylist = {str(item).lower() for item in configured} | HARDCODED_DENYLIST
        limits = self.policies.get("limits", {})
        self.max_log_tail_lines = int(limits.get("max_log_tail_lines", 1000))
        self.max_lookback_seconds = int(limits.get("max_lookback_seconds", 86400))
        self.max_query_timeout_seconds = int(limits.get("max_query_timeout_seconds", 30))

    def ensure_allowed_function(self, function_name: str) -> None:
        if function_name.startswith("openstack_helm."):
            return
        normalized = function_name.lower().replace("_", " ")
        if any(item == normalized or normalized.startswith(f"{item} ") or normalized.endswith(f" {item}") or f" {item} " in normalized for item in self.denylist):
            raise DiagnosticError("forbidden_function", f"Function is forbidden by read-only policy: {function_name}")

    def inspect_text(self, text: str) -> None:
        lower = text.lower()
        for item in self.denylist:
            if re.search(rf"\b{re.escape(item)}\b", lower):
                raise DiagnosticError("forbidden_command", f"Forbidden command or verb found: {item}")

    def clamp_tail_lines(self, tail_lines: int) -> int:
        return max(1, min(tail_lines, self.max_log_tail_lines))

    def clamp_lookback_seconds(self, lookback_seconds: int) -> int:
        return max(60, min(lookback_seconds, self.max_lookback_seconds))

    def clamp_timeout_seconds(self, timeout_seconds: int) -> int:
        return max(1, min(timeout_seconds, self.max_query_timeout_seconds))
