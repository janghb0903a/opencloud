from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from .rancher import reset_request_bearer_token, set_request_bearer_token
from .service import DiagnosticService


def create_mcp(
    service: DiagnosticService | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    streamable_http_path: str = "/mcp",
) -> FastMCP:
    svc = service or DiagnosticService()
    mcp = FastMCP("ocp-k8s-diagnostic-mcp", host=host, port=port, streamable_http_path=streamable_http_path)

    @mcp.tool(name="k8s.get_nodes")
    def get_nodes(cluster_id: str, ctx: Context | None = None) -> dict:
        """List Kubernetes nodes. Use for Kubernetes cluster_id values: mgmt, test-app-01, dev-app-01, test-genai-01, test-genai-02, test-mgmt-01, test-mgmt-02."""
        return _call_with_request_auth(ctx, lambda: svc.get_nodes(cluster_id))

    @mcp.tool(name="k8s.describe_node")
    def describe_node(cluster_id: str, node_name: str, ctx: Context | None = None) -> dict:
        """Describe one Kubernetes node using API status and events. Call k8s.get_nodes first if node_name is unknown."""
        return _call_with_request_auth(ctx, lambda: svc.describe_node(cluster_id, node_name))

    @mcp.tool(name="k8s.get_pods")
    def get_pods(cluster_id: str, namespace: str | None = None, label_selector: str | None = None, field_selector: str | None = None, limit: int = 200, ctx: Context | None = None) -> dict:
        """List Kubernetes pods without reading secrets. Use when namespace/pod name is unknown before diagnose.pod."""
        return _call_with_request_auth(ctx, lambda: svc.get_pods(cluster_id, namespace=namespace, label_selector=label_selector, field_selector=field_selector, limit=limit))

    @mcp.tool(name="k8s.get_pods_by_node")
    def get_pods_by_node(cluster_id: str, node_name: str, namespace: str | None = None, limit: int = 200, ctx: Context | None = None) -> dict:
        """List pods scheduled on a node."""
        return _call_with_request_auth(ctx, lambda: svc.get_pods_by_node(cluster_id, node_name=node_name, namespace=namespace, limit=limit))

    @mcp.tool(name="k8s.describe_pod")
    def describe_pod(cluster_id: str, namespace: str, pod_name: str, ctx: Context | None = None) -> dict:
        """Describe a pod using Kubernetes API and events."""
        return _call_with_request_auth(ctx, lambda: svc.describe_pod(cluster_id, namespace, pod_name))

    @mcp.tool(name="k8s.get_pod_events")
    def get_pod_events(cluster_id: str, namespace: str, pod_name: str, ctx: Context | None = None) -> dict:
        """Return Kubernetes events for a pod."""
        return _call_with_request_auth(ctx, lambda: svc.get_pod_events(cluster_id, namespace, pod_name))

    @mcp.tool(name="k8s.get_pod_logs")
    def get_pod_logs(cluster_id: str, namespace: str, pod_name: str, container: str | None = None, previous: bool = False, tail_lines: int = 200, since_seconds: int | None = 3600, ctx: Context | None = None) -> dict:
        """Return bounded, redacted Kubernetes pod logs."""
        return _call_with_request_auth(ctx, lambda: svc.get_pod_logs(cluster_id, namespace, pod_name, container, previous, tail_lines, since_seconds))

    @mcp.tool(name="metrics.get_prometheus_status")
    def get_prometheus_status(cluster_id: str, ctx: Context | None = None) -> dict:
        """Check configured Rancher cattle-monitoring-system Prometheus reachability for a Kubernetes cluster_id."""
        return _call_with_request_auth(ctx, lambda: svc.prometheus_status(cluster_id))

    @mcp.tool(name="metrics.query_prometheus")
    def query_prometheus(cluster_id: str, query: str, timeout_seconds: int = 10, ctx: Context | None = None) -> dict:
        """Run a bounded Prometheus instant query. For CPU usage use rate(node_cpu_seconds_total), not count(node_cpu_seconds_total). Empty result is not a tool failure."""
        return _call_with_request_auth(ctx, lambda: svc.query_prometheus(cluster_id, query, timeout_seconds))

    @mcp.tool(name="metrics.query_node")
    def query_node(cluster_id: str, node_name: str, lookback_seconds: int = 3600, ctx: Context | None = None) -> dict:
        """Run standard Kubernetes node metrics for a real node_name from k8s.get_nodes."""
        return _call_with_request_auth(ctx, lambda: svc.query_node(cluster_id, node_name, lookback_seconds))

    @mcp.tool(name="metrics.query_pod")
    def query_pod(cluster_id: str, namespace: str, pod_name: str, lookback_seconds: int = 3600, ctx: Context | None = None) -> dict:
        """Run standard pod metrics queries."""
        return _call_with_request_auth(ctx, lambda: svc.query_pod(cluster_id, namespace, pod_name, lookback_seconds))

    @mcp.tool(name="metrics.query_control_plane")
    def query_control_plane(cluster_id: str, lookback_seconds: int = 3600, ctx: Context | None = None) -> dict:
        """Run standard Kubernetes control-plane metrics queries."""
        return _call_with_request_auth(ctx, lambda: svc.query_control_plane(cluster_id, lookback_seconds))

    @mcp.tool(name="diagnose.cluster")
    def diagnose_cluster(cluster_id: str, ctx: Context | None = None) -> dict:
        """Diagnose Kubernetes cluster health from read-only API/events/logs and Prometheus when available."""
        return _call_with_request_auth(ctx, lambda: svc.diagnose_cluster(cluster_id))

    @mcp.tool(name="diagnose.node")
    def diagnose_node(cluster_id: str, node_name: str, ctx: Context | None = None) -> dict:
        """Diagnose a Kubernetes node. Use only after node_name is known from tool output or the user."""
        return _call_with_request_auth(ctx, lambda: svc.diagnose_node(cluster_id, node_name))

    @mcp.tool(name="diagnose.pod")
    def diagnose_pod(cluster_id: str, namespace: str, pod_name: str, ctx: Context | None = None) -> dict:
        """Diagnose a Kubernetes pod from status, events, and bounded logs. Do not invent namespace or pod_name."""
        return _call_with_request_auth(ctx, lambda: svc.diagnose_pod(cluster_id, namespace, pod_name))

    @mcp.tool(name="openstack_helm.get_summary")
    def openstack_helm_get_summary(cluster_id: str, namespaces: list[str] | None = None, ctx: Context | None = None) -> dict:
        """Summarize openstack-helm workloads for test-mgmt-02 only."""
        return _call_with_request_auth(ctx, lambda: svc.openstack_helm_summary(cluster_id, namespaces))

    @mcp.tool(name="openstack_helm.diagnose_cluster")
    def openstack_helm_diagnose_cluster(cluster_id: str, namespaces: list[str] | None = None, ctx: Context | None = None) -> dict:
        """Diagnose openstack-helm cluster state without Helm release secrets."""
        return _call_with_request_auth(ctx, lambda: svc.openstack_helm_diagnose_cluster(cluster_id, namespaces))

    @mcp.tool(name="runbook.search")
    def runbook_search(query: str, limit: int = 10) -> dict:
        """Search local diagnostic runbooks."""
        return svc.runbook_search(query, limit)

    @mcp.tool(name="runbook.get")
    def runbook_get(runbook_id: str) -> dict:
        """Get a local diagnostic runbook by id."""
        return svc.runbook_get(runbook_id)

    return mcp


def run_stdio() -> None:
    create_mcp().run(transport="stdio")


def run_http(host: str = "0.0.0.0", port: int = 8080, path: str = "/mcp") -> None:
    create_mcp(host=host, port=port, streamable_http_path=path).run(transport="streamable-http")


def create_http_app(host: str = "0.0.0.0", port: int = 8080, path: str = "/mcp") -> FastMCP:
    return create_mcp(host=host, port=port, streamable_http_path=path)


def _call_with_request_auth(ctx: Context | None, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    token_value = set_request_bearer_token(_bearer_from_context(ctx))
    try:
        return fn()
    finally:
        reset_request_bearer_token(token_value)


def _bearer_from_context(ctx: Context | None) -> str | None:
    if ctx is None:
        return None
    try:
        request = ctx.request_context.request
    except ValueError:
        return None
    headers = getattr(request, "headers", None)
    if not headers:
        return None
    authorization = headers.get("authorization")
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return None
    return value.strip()
