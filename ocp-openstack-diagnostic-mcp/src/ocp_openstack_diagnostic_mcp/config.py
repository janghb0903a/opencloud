from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CloudConfig:
    cloud_id: str
    cloud: str
    region_name: str = "RegionOne"
    interface: str = "internal"
    clouds_yaml_ref: str = "env:OS_CLIENT_CONFIG_FILE"
    storage_backend: str | None = None
    ceph: bool = False
    linked_k8s: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeConfig:
    clouds: dict[str, CloudConfig]
    policies: dict[str, Any] = field(default_factory=dict)
    component_k8s_mapping: dict[str, Any] = field(default_factory=dict)
    cli_allowlist: dict[str, Any] = field(default_factory=dict)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_config(config_dir: str | Path | None = None) -> RuntimeConfig:
    root = Path(config_dir or os.getenv("OCP_OPENSTACK_DIAG_CONFIG_DIR", "config"))
    clouds_doc = _load_yaml(root / "clouds.yaml") or _load_yaml(root / "clouds.yaml.example")
    policies = _load_yaml(root / "policies.yaml") or _load_yaml(root / "policies.yaml.example")
    component_map = _load_yaml(root / "component_k8s_mapping.yaml") or _load_yaml(root / "component_k8s_mapping.yaml.example")
    cli_allowlist = _load_yaml(root / "cli_allowlist.yaml") or _load_yaml(root / "cli_allowlist.yaml.example")

    clouds: dict[str, CloudConfig] = {}
    for raw in clouds_doc.get("clouds", []):
        cfg = CloudConfig(
            cloud_id=raw["cloud_id"],
            cloud=raw.get("cloud", raw["cloud_id"]),
            region_name=raw.get("region_name", "RegionOne"),
            interface=raw.get("interface", "internal"),
            clouds_yaml_ref=raw.get("clouds_yaml_ref", "env:OS_CLIENT_CONFIG_FILE"),
            storage_backend=raw.get("storage_backend"),
            ceph=bool(raw.get("ceph", False)),
            linked_k8s=raw.get("linked_k8s", {}),
        )
        clouds[cfg.cloud_id] = cfg
    return RuntimeConfig(clouds=clouds, policies=policies, component_k8s_mapping=component_map, cli_allowlist=cli_allowlist)


def resolve_ref(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("env:"):
        return os.getenv(value.split(":", 1)[1])
    if value.startswith("file:"):
        path = Path(value.split(":", 1)[1]).expanduser()
        return str(path)
    return value

