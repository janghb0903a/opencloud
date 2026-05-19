from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import resolve_secret_ref
from .redaction import redact


@dataclass(frozen=True)
class HubEndpoint:
    name: str
    url: str
    auth_type: str = "none"
    token: str | None = None
    username: str | None = None
    password: str | None = None
    headers: dict[str, str] | None = None
    verify_tls: bool = True
    timeout_seconds: int = 10

    def safe_dict(self) -> dict[str, Any]:
        return redact(
            {
                "name": self.name,
                "url": self.url,
                "auth_type": self.auth_type,
                "token": self.token,
                "username": self.username,
                "password": self.password,
                "headers": self.headers or {},
                "verify_tls": self.verify_tls,
                "timeout_seconds": self.timeout_seconds,
            }
        )


def load_hub_endpoints(config: dict[str, Any]) -> list[HubEndpoint]:
    endpoints: list[HubEndpoint] = []
    for raw in config.get("hub", {}).get("endpoints", []):
        auth = raw.get("auth", {}) or {}
        endpoints.append(
            HubEndpoint(
                name=raw["name"],
                url=raw["url"],
                auth_type=auth.get("type", "none"),
                token=resolve_secret_ref(auth.get("token_ref")),
                username=resolve_secret_ref(auth.get("username_ref")) or auth.get("username"),
                password=resolve_secret_ref(auth.get("password_ref")),
                headers={key: resolve_secret_ref(value) or "" for key, value in (raw.get("headers") or {}).items()},
                verify_tls=bool(raw.get("verify_tls", True)),
                timeout_seconds=int(raw.get("timeout_seconds", 10)),
            )
        )
    return endpoints

