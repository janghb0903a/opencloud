from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorModel(BaseModel):
    error: dict[str, Any]


class DiagnosticResponse(BaseModel):
    cluster_id: str
    context_used: dict[str, Any] = Field(default_factory=dict)
    data_sources: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    degraded: bool = False
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ClusterInput(BaseModel):
    cluster_id: str


class NamespaceInput(ClusterInput):
    namespace: str | None = None


class NodeInput(ClusterInput):
    node_name: str


class PodInput(ClusterInput):
    namespace: str
    pod_name: str


class PodsInput(NamespaceInput):
    node_name: str | None = None
    label_selector: str | None = None
    field_selector: str | None = None
    limit: int = Field(default=200, ge=1, le=500)


class PodLogsInput(PodInput):
    container: str | None = None
    previous: bool = False
    tail_lines: int = Field(default=200, ge=1, le=1000)
    since_seconds: int | None = Field(default=3600, ge=1, le=86400)


class PrometheusQueryInput(ClusterInput):
    query: str
    timeout_seconds: int = Field(default=10, ge=1, le=30)


class PrometheusRangeQueryInput(PrometheusQueryInput):
    start: str | None = None
    end: str | None = None
    step: str = "60s"
    lookback_seconds: int = Field(default=3600, ge=60, le=86400)


class MetricTargetInput(ClusterInput):
    node_name: str | None = None
    namespace: str | None = None
    pod_name: str | None = None
    lookback_seconds: int = Field(default=3600, ge=60, le=86400)


class RunbookSearchInput(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=25)


class RunbookGetInput(BaseModel):
    runbook_id: str


class OpenStackHelmInput(ClusterInput):
    namespaces: list[str] | None = None


class DiagnosisStatus(BaseModel):
    severity: Literal["info", "warning", "critical"]
    reason: str
    evidence: list[str] = Field(default_factory=list)
    recommendation: str | None = None

