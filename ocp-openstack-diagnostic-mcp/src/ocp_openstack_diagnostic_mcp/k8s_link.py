from __future__ import annotations

from typing import Any

from .config import CloudConfig


def linked_k8s(cloud: CloudConfig) -> dict[str, Any] | None:
    if not cloud.linked_k8s:
        return None
    return {
        "mcp_server": cloud.linked_k8s.get("mcp_server", "ocp-k8s-diagnostic-mcp"),
        "cluster_id": cloud.linked_k8s.get("cluster_id"),
        "namespace": cloud.linked_k8s.get("namespace"),
    }


def recommend_k8s_tools(cloud: CloudConfig, component: str | None = None, reason: str | None = None) -> list[dict[str, Any]]:
    link = linked_k8s(cloud)
    if not link:
        return []
    cluster_id = link.get("cluster_id")
    namespace = link.get("namespace") or "openstack-helm"
    recommendations = [
        {
            "mcp_server": link["mcp_server"],
            "tool": "k8s.get_pods",
            "arguments": {"cluster_id": cluster_id, "namespace": namespace},
            "reason": reason or "Check OpenStack control-plane pods before choosing a specific pod diagnosis.",
        }
    ]
    if component:
        recommendations.append(
            {
                "mcp_server": link["mcp_server"],
                "tool": "k8s.get_pods",
                "arguments": {"cluster_id": cluster_id, "namespace": namespace, "label_selector": f"application={component}"},
                "reason": f"Find {component} pods, then call diagnose.pod with the selected pod name.",
            }
        )
    return recommendations

