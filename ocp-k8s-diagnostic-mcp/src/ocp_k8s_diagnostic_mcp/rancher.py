from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

import httpx

from .config import ClusterConfig, resolve_secret_ref
from .errors import DiagnosticError

_request_bearer_token: ContextVar[str | None] = ContextVar("request_bearer_token", default=None)


def set_request_bearer_token(token: str | None):
    return _request_bearer_token.set(token)


def reset_request_bearer_token(token) -> None:
    _request_bearer_token.reset(token)


@dataclass(frozen=True)
class RancherClient:
    url: str
    verify_tls: bool = True
    timeout_seconds: int = 10

    def list_clusters(self, bearer_token: str) -> list[dict[str, Any]]:
        payload = self._get("/v3/clusters", bearer_token)
        return payload.get("data", [])

    def _get(self, path: str, bearer_token: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {bearer_token}"}
        try:
            with httpx.Client(timeout=self.timeout_seconds, verify=self.verify_tls) as http:
                response = http.get(f"{self.url.rstrip('/')}{path}", headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                raise DiagnosticError("rancher_auth_failed", "Rancher rejected the supplied bearer token") from exc
            raise DiagnosticError("rancher_api_error", "Rancher API request failed") from exc
        except Exception as exc:
            raise DiagnosticError("rancher_unavailable", "Rancher API is unavailable") from exc


@dataclass
class RancherAuthorizer:
    enabled: bool
    client: RancherClient | None = None
    token_ref: str | None = None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "RancherAuthorizer":
        raw = config.get("rancher", {}) or {}
        enabled = bool(raw.get("enabled", False))
        if not enabled:
            return cls(enabled=False)
        url = raw.get("url")
        if not url:
            raise DiagnosticError("rancher_config_invalid", "rancher.url is required when Rancher authorization is enabled")
        client = RancherClient(
            url=url,
            verify_tls=bool(raw.get("verify_tls", True)),
            timeout_seconds=int(raw.get("timeout_seconds", 10)),
        )
        return cls(enabled=True, client=client, token_ref=raw.get("user_token_ref", "env:RANCHER_BEARER_TOKEN"))

    def ensure_cluster_access(self, cluster: ClusterConfig) -> None:
        if not self.enabled:
            return
        token = self._token()
        if not token:
            raise DiagnosticError("rancher_token_required", "Rancher bearer token is required")
        assert self.client is not None
        clusters = self.client.list_clusters(token)
        if not _cluster_visible(cluster, clusters):
            raise DiagnosticError("cluster_access_denied", "Rancher authorization denied access to cluster", {"cluster_id": cluster.cluster_id})

    def _token(self) -> str | None:
        return _request_bearer_token.get() or resolve_secret_ref(self.token_ref)


def _cluster_visible(cluster: ClusterConfig, rancher_clusters: list[dict[str, Any]]) -> bool:
    expected_ids = {item for item in [cluster.rancher_cluster_id] if item}
    expected_names = {item for item in [cluster.rancher_cluster_name, cluster.cluster_id] if item}
    for item in rancher_clusters:
        rancher_id = item.get("id")
        rancher_name = item.get("name")
        if rancher_id in expected_ids or rancher_name in expected_names:
            return True
    return False

