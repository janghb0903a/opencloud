from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CLUSTERS = ["mgmt", "test-app-01", "dev-app-01", "test-genai-01", "test-genai-02", "test-mgmt-01", "test-mgmt-02"]


@dataclass(frozen=True)
class ClusterConfig:
    cluster_id: str
    kubeconfig_ref: str
    context: str | None = None
    type: str = "kubernetes"
    prometheus_ref: str | None = None
    rancher_cluster_id: str | None = None
    rancher_cluster_name: str | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def openstack_helm_enabled(self) -> bool:
        return self.cluster_id == "test-mgmt-02" or self.type == "openstack-helm"


@dataclass(frozen=True)
class RuntimeConfig:
    clusters: dict[str, ClusterConfig]
    policies: dict[str, Any]
    prometheus: dict[str, Any]
    hub: dict[str, Any] = field(default_factory=dict)
    rancher: dict[str, Any] = field(default_factory=dict)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_config(config_dir: str | Path | None = None) -> RuntimeConfig:
    root = Path(config_dir or os.getenv("OCP_DIAG_CONFIG_DIR", "config"))
    clusters_doc = _load_yaml(root / "clusters.yaml") or _load_yaml(root / "clusters.yaml.example")
    policies = _load_yaml(root / "policies.yaml") or _load_yaml(root / "policies.yaml.example")
    prometheus = _load_yaml(root / "prometheus.yaml") or _load_yaml(root / "prometheus.yaml.example")
    hub = _load_yaml(root / "hub.yaml") or _load_yaml(root / "hub.yaml.example")
    rancher = _load_yaml(root / "rancher.yaml") or _load_yaml(root / "rancher.yaml.example")

    clusters: dict[str, ClusterConfig] = {}
    for raw in clusters_doc.get("clusters", []):
        cfg = ClusterConfig(
            cluster_id=raw["cluster_id"],
            kubeconfig_ref=raw["kubeconfig_ref"],
            context=raw.get("context"),
            type=raw.get("type", "kubernetes"),
            prometheus_ref=raw.get("prometheus_ref"),
            rancher_cluster_id=raw.get("rancher_cluster_id"),
            rancher_cluster_name=raw.get("rancher_cluster_name"),
            tags=raw.get("tags", []),
        )
        clusters[cfg.cluster_id] = cfg
    if not clusters:
        for cluster_id in DEFAULT_CLUSTERS:
            clusters[cluster_id] = ClusterConfig(cluster_id=cluster_id, kubeconfig_ref=f"env:KUBECONFIG_{cluster_id.upper().replace('-', '_')}")
    return RuntimeConfig(clusters=clusters, policies=policies, prometheus=prometheus, hub=hub, rancher=rancher)


def resolve_secret_ref(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("env:"):
        return os.getenv(value.split(":", 1)[1])
    if value.startswith("file:"):
        path = Path(value.split(":", 1)[1]).expanduser()
        return path.read_text(encoding="utf-8").strip() if path.exists() else None
    return value
