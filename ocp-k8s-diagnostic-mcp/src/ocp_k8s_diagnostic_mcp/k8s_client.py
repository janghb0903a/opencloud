from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kubernetes import client, config

from .config import ClusterConfig
from .errors import DiagnosticError


@dataclass
class K8sClients:
    core: Any
    apps: Any


class KubernetesClientFactory:
    def create(self, cluster: ClusterConfig) -> K8sClients:
        kubeconfig_path = self._resolve_kubeconfig_ref(cluster.kubeconfig_ref)
        try:
            api_client = config.new_client_from_config(config_file=kubeconfig_path, context=cluster.context)
        except Exception as exc:  # pragma: no cover - integration path
            raise DiagnosticError("kubeconfig_load_failed", "Failed to create Kubernetes client", {"cluster_id": cluster.cluster_id}) from exc
        return K8sClients(core=client.CoreV1Api(api_client), apps=client.AppsV1Api(api_client))

    def _resolve_kubeconfig_ref(self, ref: str) -> str:
        if ref.startswith("env:"):
            env_name = ref.split(":", 1)[1]
            value = os.getenv(env_name)
            if not value:
                raise DiagnosticError("missing_kubeconfig_ref", f"Environment variable is not set: {env_name}")
            return value
        if ref.startswith("file:"):
            return ref.split(":", 1)[1]
        path = Path(ref).expanduser()
        if not path.exists():
            raise DiagnosticError("missing_kubeconfig_ref", "kubeconfig_ref path does not exist")
        return str(path)


def _meta(obj: Any) -> dict[str, Any]:
    metadata = getattr(obj, "metadata", None)
    return {
        "name": getattr(metadata, "name", None),
        "namespace": getattr(metadata, "namespace", None),
        "labels": getattr(metadata, "labels", None) or {},
        "creation_timestamp": str(getattr(metadata, "creation_timestamp", "")) if getattr(metadata, "creation_timestamp", None) else None,
    }


def node_to_dict(node: Any) -> dict[str, Any]:
    status = getattr(node, "status", None)
    conditions = []
    for cond in getattr(status, "conditions", []) or []:
        conditions.append({"type": cond.type, "status": cond.status, "reason": cond.reason, "message": cond.message})
    return {
        **_meta(node),
        "conditions": conditions,
        "capacity": getattr(status, "capacity", {}) or {},
        "allocatable": getattr(status, "allocatable", {}) or {},
        "node_info": node_info_to_dict(getattr(status, "node_info", None)),
    }


def node_info_to_dict(node_info: Any) -> dict[str, Any]:
    if not node_info:
        return {}
    fields = [
        "architecture",
        "boot_id",
        "container_runtime_version",
        "kernel_version",
        "kube_proxy_version",
        "kubelet_version",
        "machine_id",
        "operating_system",
        "os_image",
        "system_uuid",
    ]
    return {field: getattr(node_info, field, None) for field in fields if getattr(node_info, field, None)}


def pod_to_dict(pod: Any) -> dict[str, Any]:
    status = getattr(pod, "status", None)
    spec = getattr(pod, "spec", None)
    containers = []
    for container in getattr(spec, "containers", []) or []:
        containers.append({"name": container.name, "image": container.image})
    container_statuses = []
    for cs in getattr(status, "container_statuses", []) or []:
        state = getattr(cs, "state", None)
        waiting = getattr(state, "waiting", None)
        terminated = getattr(state, "terminated", None)
        container_statuses.append(
            {
                "name": cs.name,
                "ready": cs.ready,
                "restart_count": cs.restart_count,
                "state": {
                    "waiting": vars(waiting) if waiting else None,
                    "terminated": vars(terminated) if terminated else None,
                },
            }
        )
    return {
        **_meta(pod),
        "node_name": getattr(spec, "node_name", None),
        "phase": getattr(status, "phase", None),
        "pod_ip": getattr(status, "pod_ip", None),
        "containers": containers,
        "container_statuses": container_statuses,
    }


def event_to_dict(event: Any) -> dict[str, Any]:
    involved = getattr(event, "involved_object", None)
    return {
        **_meta(event),
        "type": getattr(event, "type", None),
        "reason": getattr(event, "reason", None),
        "message": getattr(event, "message", None),
        "count": getattr(event, "count", None),
        "last_timestamp": str(getattr(event, "last_timestamp", "")) if getattr(event, "last_timestamp", None) else None,
        "involved_object": {
            "kind": getattr(involved, "kind", None),
            "name": getattr(involved, "name", None),
            "namespace": getattr(involved, "namespace", None),
        },
    }
