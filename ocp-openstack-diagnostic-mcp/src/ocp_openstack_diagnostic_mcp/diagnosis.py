from __future__ import annotations

from typing import Any


def diagnose_server_data(server: dict[str, Any]) -> list[dict[str, Any]]:
    status = str(server.get("status", "")).upper()
    fault = server.get("fault") or {}
    findings: list[dict[str, Any]] = []
    if status == "ERROR":
        message = fault.get("message") or fault.get("details") or "Server is in ERROR state"
        findings.append({"severity": "critical", "reason": "ServerError", "evidence": [message], "recommendation": "Inspect server actions, Nova compute service health, placement allocation, and related Kubernetes pods."})
    if status == "BUILD":
        findings.append({"severity": "warning", "reason": "ServerStillBuilding", "evidence": ["Server is still in BUILD state."]})
    return findings or [{"severity": "info", "reason": "NoImmediateServerIssue", "evidence": [f"server_status={status or 'unknown'}"]}]


def diagnose_no_valid_host_data(hypervisors: list[dict[str, Any]], providers: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    disabled = [h.get("name") or h.get("hypervisor_hostname") for h in hypervisors if str(h.get("status", "")).lower() == "disabled" or str(h.get("state", "")).lower() != "up"]
    findings: list[dict[str, Any]] = []
    if disabled:
        findings.append({"severity": "critical", "reason": "ComputeServiceUnavailable", "evidence": disabled[:20], "recommendation": "Check nova-compute services and related openstack-helm pods."})
    if providers == []:
        findings.append({"severity": "critical", "reason": "NoPlacementResourceProviders", "evidence": ["Placement returned no resource providers."]})
    return findings or [{"severity": "info", "reason": "NoObviousNoValidHostSignal", "evidence": ["No disabled hypervisors found in sampled data."]}]


def diagnose_network_data(ports: list[dict[str, Any]], routers: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    down_ports = [p.get("id") for p in ports if str(p.get("status", "")).upper() in {"DOWN", "ERROR"}]
    findings: list[dict[str, Any]] = []
    if down_ports:
        findings.append({"severity": "warning", "reason": "PortsDownOrError", "evidence": down_ports[:25], "recommendation": "Check Neutron agents, port binding, security groups, and DHCP/L3 pods."})
    router_down = [r.get("id") for r in routers or [] if str(r.get("status", "")).upper() in {"DOWN", "ERROR"}]
    if router_down:
        findings.append({"severity": "warning", "reason": "RoutersDownOrError", "evidence": router_down[:25]})
    return findings or [{"severity": "info", "reason": "NoImmediateNetworkIssue", "evidence": ["No DOWN/ERROR ports or routers detected in sampled data."]}]


def diagnose_volume_data(volume: dict[str, Any]) -> list[dict[str, Any]]:
    status = str(volume.get("status", "")).lower()
    attach_status = str(volume.get("attach_status", "")).lower()
    findings = []
    if status in {"error", "error_extending", "error_restoring", "error_managing"}:
        findings.append({"severity": "critical", "reason": "VolumeError", "evidence": [f"volume_status={status}"], "recommendation": "Check cinder-volume service, backend pool, and storage backend events."})
    if attach_status in {"error", "detached"} and volume.get("attachments"):
        findings.append({"severity": "critical", "reason": "VolumeAttachmentFailed", "evidence": [f"attach_status={attach_status}"]})
    return findings or [{"severity": "info", "reason": "NoImmediateVolumeIssue", "evidence": [f"volume_status={status or 'unknown'}"]}]


def diagnose_powerflex_data(services: list[dict[str, Any]], pools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings = []
    down = [s.get("host") or s.get("binary") for s in services if str(s.get("state", "")).lower() == "down" or str(s.get("status", "")).lower() == "disabled"]
    if down:
        findings.append({"severity": "critical", "reason": "CinderServiceDown", "evidence": down[:20], "recommendation": "Check cinder-volume PowerFlex backend pods and storage connectivity."})
    bad_pools = [p.get("name") for p in pools if _pool_free_percent(p) is not None and _pool_free_percent(p) < 5]
    if bad_pools:
        findings.append({"severity": "critical", "reason": "PowerFlexPoolLowCapacity", "evidence": bad_pools[:20]})
    return findings or [{"severity": "info", "reason": "PowerFlexNoImmediateIssue", "evidence": ["No down cinder services or critically low pools detected."]}]


def _pool_free_percent(pool: dict[str, Any]) -> float | None:
    total = pool.get("total_capacity_gb") or pool.get("capabilities", {}).get("total_capacity_gb")
    free = pool.get("free_capacity_gb") or pool.get("capabilities", {}).get("free_capacity_gb")
    try:
        total_f = float(total)
        free_f = float(free)
    except (TypeError, ValueError):
        return None
    if total_f <= 0:
        return None
    return free_f / total_f * 100

