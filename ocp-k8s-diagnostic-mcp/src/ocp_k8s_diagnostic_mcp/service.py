from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from .audit import AuditLogger
from .config import RuntimeConfig, load_config
from .diagnosis import diagnose_node_data, diagnose_pod_data, summarize_cluster
from .errors import DiagnosticError, error_json
from .hub import load_hub_endpoints
from .k8s_client import KubernetesClientFactory, event_to_dict, node_to_dict, pod_to_dict
from .models import DiagnosticResponse
from .policy import PolicyGuard
from .prometheus import CONTROL_PLANE_QUERIES, PrometheusFactory, node_queries, pod_queries
from .rancher import RancherAuthorizer
from .redaction import redact
from .registry import ClusterRegistry
from .runbooks import RunbookStore


class DiagnosticService:
    def __init__(
        self,
        runtime_config: RuntimeConfig | None = None,
        k8s_factory: KubernetesClientFactory | None = None,
        prometheus_factory: PrometheusFactory | None = None,
        runbook_root: Path | None = None,
    ):
        self.config = runtime_config or load_config()
        self.registry = ClusterRegistry(self.config)
        self.policy = PolicyGuard(self.config.policies)
        self.k8s_factory = k8s_factory or KubernetesClientFactory()
        self.prometheus_factory = prometheus_factory or PrometheusFactory(self.config, self.policy)
        self.audit = AuditLogger()
        self.runbooks = RunbookStore(runbook_root or _default_runbook_root())
        self.hub_endpoints = load_hub_endpoints(self.config.hub)
        self.rancher_authorizer = RancherAuthorizer.from_config(self.config.rancher)

    def _wrap(self, cluster_id: str, tool: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        self.policy.ensure_allowed_function(tool)
        self.audit.record("tool_start", tool=tool, cluster_id=cluster_id)
        try:
            cluster = self.registry.get(cluster_id)
            self.rancher_authorizer.ensure_cluster_access(cluster)
            result = fn()
            data_sources = result.pop("data_sources", ["kubernetes_api"])
            limitations = result.pop("limitations", [])
            degraded = result.pop("degraded", False)
            errors = result.pop("errors", [])
            payload = DiagnosticResponse(
                cluster_id=cluster.cluster_id,
                context_used={"cluster_type": cluster.type},
                data_sources=data_sources,
                limitations=limitations,
                result=redact(result),
                degraded=degraded,
                errors=errors,
            ).model_dump()
            self.audit.record("tool_success", tool=tool, cluster_id=cluster_id)
            return payload
        except DiagnosticError as exc:
            self.audit.record("tool_error", tool=tool, cluster_id=cluster_id, code=exc.code)
            return error_json(exc.code, exc.message, exc.details)

    def _clients(self, cluster_id: str):
        return self.k8s_factory.create(self.registry.get(cluster_id))

    def get_nodes(self, cluster_id: str) -> dict[str, Any]:
        return self._wrap(cluster_id, "k8s.get_nodes", lambda: {"nodes": [node_to_dict(n) for n in self._clients(cluster_id).core.list_node().items]})

    def describe_node(self, cluster_id: str, node_name: str) -> dict[str, Any]:
        def run():
            core = self._clients(cluster_id).core
            return {"node": node_to_dict(core.read_node(node_name)), "events": self._events_for(core, "Node", node_name, None)}
        return self._wrap(cluster_id, "k8s.describe_node", run)

    def get_pods(self, cluster_id: str, namespace: str | None = None, **kwargs: Any) -> dict[str, Any]:
        def run():
            core = self._clients(cluster_id).core
            if namespace:
                pods = core.list_namespaced_pod(namespace, **_selector_kwargs(kwargs)).items
            else:
                pods = core.list_pod_for_all_namespaces(**_selector_kwargs(kwargs)).items
            return {"pods": [pod_to_dict(p) for p in pods[: int(kwargs.get("limit", 200))]]}
        return self._wrap(cluster_id, "k8s.get_pods", run)

    def get_pods_by_node(self, cluster_id: str, node_name: str, namespace: str | None = None, limit: int = 200) -> dict[str, Any]:
        return self.get_pods(cluster_id, namespace=namespace, field_selector=f"spec.nodeName={node_name}", limit=limit)

    def describe_pod(self, cluster_id: str, namespace: str, pod_name: str) -> dict[str, Any]:
        def run():
            core = self._clients(cluster_id).core
            return {"pod": pod_to_dict(core.read_namespaced_pod(pod_name, namespace)), "events": self._events_for(core, "Pod", pod_name, namespace)}
        return self._wrap(cluster_id, "k8s.describe_pod", run)

    def get_pod_events(self, cluster_id: str, namespace: str, pod_name: str) -> dict[str, Any]:
        def run():
            core = self._clients(cluster_id).core
            return {"events": self._events_for(core, "Pod", pod_name, namespace)}
        return self._wrap(cluster_id, "k8s.get_pod_events", run)

    def get_pod_logs(self, cluster_id: str, namespace: str, pod_name: str, container: str | None = None, previous: bool = False, tail_lines: int = 200, since_seconds: int | None = 3600) -> dict[str, Any]:
        def run():
            core = self._clients(cluster_id).core
            safe_tail = self.policy.clamp_tail_lines(tail_lines)
            logs = core.read_namespaced_pod_log(
                pod_name,
                namespace,
                container=container,
                previous=previous,
                tail_lines=safe_tail,
                since_seconds=since_seconds,
                timestamps=True,
            )
            return {"logs": redact(logs), "tail_lines_used": safe_tail, "data_sources": ["kubernetes_pod_logs"]}
        return self._wrap(cluster_id, "k8s.get_pod_logs", run)

    def prometheus_status(self, cluster_id: str) -> dict[str, Any]:
        return self._prom_wrap(cluster_id, "metrics.get_prometheus_status", lambda prom: {"status": prom.status()})

    def query_prometheus(self, cluster_id: str, query: str, timeout_seconds: int = 10) -> dict[str, Any]:
        try:
            self.policy.inspect_text(query)
        except DiagnosticError as exc:
            return error_json(exc.code, exc.message, exc.details)
        timeout = self.policy.clamp_timeout_seconds(timeout_seconds)
        return self._prom_wrap(cluster_id, "metrics.query_prometheus", lambda prom: {"query": query, "response": prom.query(query, timeout)})

    def query_node(self, cluster_id: str, node_name: str, lookback_seconds: int = 3600) -> dict[str, Any]:
        lookback = self.policy.clamp_lookback_seconds(lookback_seconds)
        return self._prom_wrap(cluster_id, "metrics.query_node", lambda prom: {"metrics": {k: prom.query_range(v, lookback) for k, v in node_queries(node_name).items()}, "lookback_seconds_used": lookback})

    def query_pod(self, cluster_id: str, namespace: str, pod_name: str, lookback_seconds: int = 3600) -> dict[str, Any]:
        lookback = self.policy.clamp_lookback_seconds(lookback_seconds)
        return self._prom_wrap(cluster_id, "metrics.query_pod", lambda prom: {"metrics": {k: prom.query_range(v, lookback) for k, v in pod_queries(namespace, pod_name).items()}, "lookback_seconds_used": lookback})

    def query_control_plane(self, cluster_id: str, lookback_seconds: int = 3600) -> dict[str, Any]:
        lookback = self.policy.clamp_lookback_seconds(lookback_seconds)
        return self._prom_wrap(cluster_id, "metrics.query_control_plane", lambda prom: {"metrics": {k: prom.query_range(v, lookback) for k, v in CONTROL_PLANE_QUERIES.items()}, "lookback_seconds_used": lookback})

    def diagnose_cluster(self, cluster_id: str) -> dict[str, Any]:
        def run():
            core = self._clients(cluster_id).core
            nodes = [node_to_dict(n) for n in core.list_node().items]
            pods = [pod_to_dict(p) for p in core.list_pod_for_all_namespaces(limit=500).items]
            result = {"findings": summarize_cluster(nodes, pods), "node_count": len(nodes), "pod_count_sampled": len(pods), "data_sources": ["kubernetes_api", "kubernetes_events"]}
            try:
                result["prometheus"] = self.prometheus_factory.create(self.registry.get(cluster_id)).status()
            except DiagnosticError as exc:
                result["degraded"] = True
                result["errors"] = [error_json(exc.code, exc.message)["error"]]
                result["limitations"] = ["Prometheus unavailable; diagnosis used Kubernetes API/events/log scope only."]
            return result
        return self._wrap(cluster_id, "diagnose.cluster", run)

    def diagnose_node(self, cluster_id: str, node_name: str) -> dict[str, Any]:
        def run():
            core = self._clients(cluster_id).core
            node = node_to_dict(core.read_node(node_name))
            events = self._events_for(core, "Node", node_name, None)
            return {"findings": diagnose_node_data(node, events), "node": node, "events": events}
        return self._wrap(cluster_id, "diagnose.node", run)

    def diagnose_pod(self, cluster_id: str, namespace: str, pod_name: str) -> dict[str, Any]:
        def run():
            core = self._clients(cluster_id).core
            pod = pod_to_dict(core.read_namespaced_pod(pod_name, namespace))
            events = self._events_for(core, "Pod", pod_name, namespace)
            logs = ""
            try:
                logs = core.read_namespaced_pod_log(pod_name, namespace, tail_lines=self.policy.clamp_tail_lines(200), timestamps=True)
            except Exception:
                pass
            return {"findings": diagnose_pod_data(pod, events, logs), "pod": pod, "events": events, "logs_sampled": bool(logs), "data_sources": ["kubernetes_api", "kubernetes_events", "kubernetes_pod_logs"]}
        return self._wrap(cluster_id, "diagnose.pod", run)

    def openstack_helm_summary(self, cluster_id: str, namespaces: list[str] | None = None) -> dict[str, Any]:
        def run():
            cluster = self.registry.get(cluster_id)
            if not cluster.openstack_helm_enabled:
                raise DiagnosticError("tool_not_enabled", "openstack_helm tools are enabled only for test-mgmt-02", {"cluster_id": cluster_id})
            core = self._clients(cluster_id).core
            ns_list = namespaces or ["openstack", "osh-infra", "ceph"]
            summary = {}
            for ns in ns_list:
                pods = [pod_to_dict(p) for p in core.list_namespaced_pod(ns, limit=300).items]
                pvcs = [getattr(p.metadata, "name", None) for p in core.list_namespaced_persistent_volume_claim(ns).items]
                warnings = [e for e in self._events_for(core, None, None, ns) if e.get("type") == "Warning"]
                summary[ns] = {"pod_count": len(pods), "unhealthy_pods": _unhealthy_pods(pods), "pvc_count": len(pvcs), "warning_events": warnings[:50]}
            return {"summary": summary, "data_sources": ["kubernetes_api", "kubernetes_events"], "limitations": ["Helm release secrets are intentionally not read."]}
        return self._wrap(cluster_id, "openstack_helm.get_summary", run)

    def openstack_helm_diagnose_cluster(self, cluster_id: str, namespaces: list[str] | None = None) -> dict[str, Any]:
        response = self.openstack_helm_summary(cluster_id, namespaces)
        if "error" in response:
            return response
        findings = []
        for ns, summary in response["result"]["summary"].items():
            if summary["unhealthy_pods"]:
                findings.append({"severity": "critical", "reason": "OpenStackHelmUnhealthyPods", "namespace": ns, "evidence": summary["unhealthy_pods"]})
            if summary["warning_events"]:
                findings.append({"severity": "warning", "reason": "OpenStackHelmWarningEvents", "namespace": ns, "evidence": [e.get("message", "") for e in summary["warning_events"][:10]]})
        response["result"]["findings"] = findings or [{"severity": "info", "reason": "OpenStackHelmLooksHealthy", "evidence": ["No unhealthy pods or warning events found in candidate namespaces."]}]
        return response

    def runbook_search(self, query: str, limit: int = 10) -> dict[str, Any]:
        self.audit.record("tool_start", tool="runbook.search")
        return {"result": {"matches": self.runbooks.search(query, limit)}, "data_sources": ["local_runbooks"], "limitations": []}

    def runbook_get(self, runbook_id: str) -> dict[str, Any]:
        self.audit.record("tool_start", tool="runbook.get")
        return {"result": self.runbooks.get(runbook_id), "data_sources": ["local_runbooks"], "limitations": []}

    def _prom_wrap(self, cluster_id: str, tool: str, fn: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
        def run():
            prom = self.prometheus_factory.create(self.registry.get(cluster_id))
            result = fn(prom)
            result["data_sources"] = ["rancher_cattle_monitoring_prometheus"]
            return result
        return self._wrap(cluster_id, tool, run)

    def _events_for(self, core: Any, kind: str | None, name: str | None, namespace: str | None) -> list[dict[str, Any]]:
        field_selector = None
        if kind and name:
            field_selector = f"involvedObject.kind={kind},involvedObject.name={name}"
        if namespace:
            events = core.list_namespaced_event(namespace, field_selector=field_selector).items
        else:
            events = core.list_event_for_all_namespaces(field_selector=field_selector).items
        return [event_to_dict(e) for e in events]


def _selector_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in {"label_selector": kwargs.get("label_selector"), "field_selector": kwargs.get("field_selector"), "limit": kwargs.get("limit")}.items() if v}


def _unhealthy_pods(pods: list[dict[str, Any]]) -> list[str]:
    unhealthy = []
    for pod in pods:
        if pod.get("phase") not in {"Running", "Succeeded"}:
            unhealthy.append(f"{pod.get('namespace')}/{pod.get('name')}:{pod.get('phase')}")
        for cs in pod.get("container_statuses", []):
            waiting = ((cs.get("state") or {}).get("waiting") or {})
            if waiting.get("reason"):
                unhealthy.append(f"{pod.get('namespace')}/{pod.get('name')}:{waiting.get('reason')}")
    return unhealthy[:100]


def _default_runbook_root() -> Path:
    configured = os.getenv("OCP_DIAG_RUNBOOK_DIR")
    if configured:
        return Path(configured)
    project_root = Path(__file__).resolve().parents[2]
    if (project_root / "runbooks").exists():
        return project_root / "runbooks"
    cwd_root = Path.cwd() / "runbooks"
    return cwd_root
