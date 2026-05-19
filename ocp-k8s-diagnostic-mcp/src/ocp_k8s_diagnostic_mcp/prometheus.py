from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from .config import ClusterConfig, RuntimeConfig
from .errors import DiagnosticError
from .policy import PolicyGuard


class PrometheusClient:
    def __init__(self, base_url: str, timeout_seconds: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def status(self) -> dict[str, Any]:
        return self._get("/api/v1/status/runtimeinfo", {})

    def query(self, query: str, timeout_seconds: int = 10) -> dict[str, Any]:
        return self._get("/api/v1/query", {"query": query, "timeout": f"{timeout_seconds}s"})

    def query_range(self, query: str, lookback_seconds: int, step: str = "60s", timeout_seconds: int = 10) -> dict[str, Any]:
        end = datetime.now(UTC)
        start = end - timedelta(seconds=lookback_seconds)
        return self._get(
            "/api/v1/query_range",
            {
                "query": query,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "step": step,
                "timeout": f"{timeout_seconds}s",
            },
        )

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout_seconds) as http:
                resp = http.get(f"{self.base_url}{path}", params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            raise DiagnosticError("prometheus_unavailable", "Prometheus API is unavailable") from exc


class PrometheusFactory:
    def __init__(self, config: RuntimeConfig, policy: PolicyGuard):
        self.config = config
        self.policy = policy

    def create(self, cluster: ClusterConfig) -> PrometheusClient:
        prom_ref = cluster.prometheus_ref or cluster.cluster_id
        raw = (self.config.prometheus.get("prometheus") or {}).get(prom_ref) or {}
        url = raw.get("url")
        if not url:
            raise DiagnosticError("prometheus_not_configured", "Prometheus is not configured for cluster", {"cluster_id": cluster.cluster_id})
        return PrometheusClient(url, self.policy.clamp_timeout_seconds(int(raw.get("timeout_seconds", 10))))


def node_queries(node_name: str) -> dict[str, str]:
    return {
        "cpu_usage": f'100 - (avg by(instance) (rate(node_cpu_seconds_total{{mode="idle",instance=~"{node_name}.*"}}[5m])) * 100)',
        "memory_available": f'node_memory_MemAvailable_bytes{{instance=~"{node_name}.*"}}',
        "filesystem_free": f'node_filesystem_avail_bytes{{instance=~"{node_name}.*",fstype!~"tmpfs|overlay"}}',
    }


def pod_queries(namespace: str, pod_name: str) -> dict[str, str]:
    return {
        "restarts": f'kube_pod_container_status_restarts_total{{namespace="{namespace}",pod="{pod_name}"}}',
        "waiting": f'kube_pod_container_status_waiting_reason{{namespace="{namespace}",pod="{pod_name}"}}',
        "cpu": f'rate(container_cpu_usage_seconds_total{{namespace="{namespace}",pod="{pod_name}",container!=""}}[5m])',
        "memory": f'container_memory_working_set_bytes{{namespace="{namespace}",pod="{pod_name}",container!=""}}',
    }


CONTROL_PLANE_QUERIES = {
    "apiserver_up": 'up{job=~".*apiserver.*"}',
    "etcd_up": 'up{job=~".*etcd.*"}',
    "scheduler_up": 'up{job=~".*scheduler.*"}',
    "controller_manager_up": 'up{job=~".*controller.*manager.*"}',
}

