from __future__ import annotations

import shlex
from typing import Any

from .errors import DiagnosticError


MUTATING_DENYLIST = {
    "create",
    "delete",
    "set",
    "update",
    "reboot",
    "rebuild",
    "resize",
    "migrate",
    "evacuate",
    "attach",
    "detach",
    "reset-state",
    "enable",
    "disable",
    "upload",
    "add",
    "remove",
    "unset",
}


class PolicyGuard:
    def __init__(self, policies: dict[str, Any] | None = None):
        self.policies = policies or {}
        configured = self.policies.get("deny_operations", [])
        self.denylist = {str(item).lower() for item in configured} | MUTATING_DENYLIST
        limits = self.policies.get("limits", {})
        self.max_results = int(limits.get("max_results", 500))
        self.timeout_seconds = int(limits.get("timeout_seconds", 20))
        self.stdout_limit_bytes = int(limits.get("stdout_limit_bytes", 262144))
        self.retries = int(limits.get("retries", 1))

    def ensure_read_only_operation(self, name: str) -> None:
        normalized = name.lower().replace("_", " ").replace(".", " ")
        if any(token in normalized.split() for token in self.denylist):
            raise DiagnosticError("forbidden_operation", f"Operation is forbidden by read-only policy: {name}")

    def ensure_cli_allowed(self, argv: list[str], allowlist: dict[str, Any]) -> None:
        if not argv or argv[0] != "openstack":
            raise DiagnosticError("forbidden_cli_command", "Only openstack CLI allowlisted commands are permitted")
        joined = " ".join(shlex.quote(item) for item in argv)
        for item in allowlist.get("commands", []):
            prefix = item.get("argv_prefix", [])
            if argv[: len(prefix)] == prefix:
                if any(part.lower() in self.denylist for part in argv):
                    break
                return
        raise DiagnosticError("forbidden_cli_command", f"CLI command is not allowlisted: {joined}")

    def clamp_limit(self, value: int | None) -> int:
        if value is None:
            return self.max_results
        return max(1, min(int(value), self.max_results))

