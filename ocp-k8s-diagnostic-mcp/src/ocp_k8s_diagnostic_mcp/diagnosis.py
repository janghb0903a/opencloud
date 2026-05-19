from __future__ import annotations

from typing import Any


def condition_status(items: list[dict[str, Any]], condition_type: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("type") == condition_type:
            return item
    return None


def diagnose_node_data(node: dict[str, Any], events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    ready = condition_status(node.get("conditions", []), "Ready")
    if ready and ready.get("status") != "True":
        findings.append(
            {
                "severity": "critical",
                "reason": "NodeNotReady",
                "evidence": [ready.get("message") or ready.get("reason") or "Ready condition is not True"],
                "recommendation": "Check kubelet health, node pressure conditions, and recent node events.",
            }
        )
    for pressure in ["DiskPressure", "MemoryPressure", "PIDPressure", "NetworkUnavailable"]:
        cond = condition_status(node.get("conditions", []), pressure)
        if cond and cond.get("status") == "True":
            findings.append(
                {
                    "severity": "critical" if pressure == "DiskPressure" else "warning",
                    "reason": pressure,
                    "evidence": [cond.get("message") or cond.get("reason") or f"{pressure} is True"],
                    "recommendation": "Use Kubernetes events and workload placement to identify pressure sources. Node system logs are out of v1.0 scope.",
                }
            )
    for event in events or []:
        if event.get("type") == "Warning":
            findings.append({"severity": "warning", "reason": event.get("reason") or "NodeWarningEvent", "evidence": [event.get("message", "")]})
    return findings or [{"severity": "info", "reason": "NoImmediateNodeIssue", "evidence": ["No critical node condition detected."]}]


def diagnose_pod_data(pod: dict[str, Any], events: list[dict[str, Any]] | None = None, logs: str | None = None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for cs in pod.get("container_statuses", []):
        waiting = ((cs.get("state") or {}).get("waiting") or {})
        reason = waiting.get("reason")
        if reason in {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"}:
            findings.append(
                {
                    "severity": "critical",
                    "reason": reason,
                    "evidence": [waiting.get("message") or f"{cs.get('name')} is waiting: {reason}", f"restart_count={cs.get('restart_count')}"],
                    "recommendation": "Inspect pod events and recent container logs. No workload mutation is available from this MCP server.",
                }
            )
        elif cs.get("restart_count", 0) > 0:
            findings.append(
                {
                    "severity": "warning",
                    "reason": "ContainerRestarts",
                    "evidence": [f"{cs.get('name')} restart_count={cs.get('restart_count')}"],
                }
            )
    for event in events or []:
        if event.get("type") == "Warning":
            findings.append({"severity": "warning", "reason": event.get("reason") or "PodWarningEvent", "evidence": [event.get("message", "")]})
    if logs and any(word in logs.lower() for word in ["exception", "traceback", "panic", "fatal", "error"]):
        findings.append({"severity": "warning", "reason": "ErrorSignalsInLogs", "evidence": ["Recent logs contain error-like text."]})
    return findings or [{"severity": "info", "reason": "NoImmediatePodIssue", "evidence": ["No obvious pod issue detected from status/events/logs."]}]


def summarize_cluster(nodes: list[dict[str, Any]], pods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    not_ready = [n["name"] for n in nodes if (condition_status(n.get("conditions", []), "Ready") or {}).get("status") != "True"]
    if not_ready:
        findings.append({"severity": "critical", "reason": "NodeNotReady", "evidence": not_ready})
    bad_pods = []
    for pod in pods:
        for cs in pod.get("container_statuses", []):
            reason = (((cs.get("state") or {}).get("waiting") or {}).get("reason"))
            if reason in {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"}:
                bad_pods.append(f"{pod.get('namespace')}/{pod.get('name')}:{reason}")
    if bad_pods:
        findings.append({"severity": "critical", "reason": "UnhealthyPods", "evidence": bad_pods[:50]})
    return findings or [{"severity": "info", "reason": "ClusterLooksHealthy", "evidence": ["No critical node or pod status findings detected."]}]

