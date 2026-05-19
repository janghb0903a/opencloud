from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from .audit import AuditLogger
from .config import CloudConfig, RuntimeConfig, load_config
from .diagnosis import diagnose_network_data, diagnose_no_valid_host_data, diagnose_powerflex_data, diagnose_server_data, diagnose_volume_data
from .errors import DiagnosticError, error_json
from .k8s_link import linked_k8s, recommend_k8s_tools
from .models import DiagnosticResponse
from .openstack_client import OpenStackClientFactory, RestClient, SafeCliRunner, limited, serialize
from .policy import PolicyGuard
from .redaction import redact
from .registry import CloudRegistry
from .runbooks import RunbookStore


class DiagnosticService:
    def __init__(
        self,
        runtime_config: RuntimeConfig | None = None,
        client_factory: OpenStackClientFactory | None = None,
        rest_factory: Callable[[Any], RestClient] | None = None,
        runbook_root: Path | None = None,
    ):
        self.config = runtime_config or load_config()
        self.registry = CloudRegistry(self.config)
        self.policy = PolicyGuard(self.config.policies)
        self.client_factory = client_factory or OpenStackClientFactory()
        self.rest_factory = rest_factory or (lambda conn: RestClient(conn, timeout_seconds=self.policy.timeout_seconds))
        self.cli = SafeCliRunner(self.policy, self.config.cli_allowlist)
        self.audit = AuditLogger()
        self.runbooks = RunbookStore(runbook_root or _default_runbook_root())

    def _wrap(
        self,
        cloud_id: str,
        tool: str,
        fn: Callable[[CloudConfig, Any], dict[str, Any]],
        *,
        diagnose: bool = False,
        k8s_component: str | None = None,
        k8s_reason: str | None = None,
    ) -> dict[str, Any]:
        try:
            self.policy.ensure_read_only_operation(tool)
            cloud = self.registry.get(cloud_id)
            with self.audit.span(tool, cloud_id) as trace_id:
                conn = self.client_factory.create(cloud)
                result = self._execute_with_retry(fn, cloud, conn)
                data_sources = result.pop("data_sources", ["openstacksdk"])
                limitations = result.pop("limitations", [])
                recommended = result.pop("recommended_next_tools", [])
                if diagnose:
                    recommended = recommended or recommend_k8s_tools(cloud, component=k8s_component, reason=k8s_reason)
                count = _result_count(result)
                self.audit.record("tool_result", trace_id=trace_id, tool=tool, cloud_id=cloud_id, result_count=count)
                return DiagnosticResponse(
                    cloud_id=cloud.cloud_id,
                    context_used={"region_name": cloud.region_name, "interface": cloud.interface, "storage_backend": cloud.storage_backend, "ceph": cloud.ceph},
                    data_sources=data_sources,
                    limitations=limitations,
                    result=redact(result),
                    linked_k8s=linked_k8s(cloud) if diagnose else None,
                    recommended_next_tools=recommended,
                    trace_id=trace_id,
                ).model_dump()
        except DiagnosticError as exc:
            return error_json(exc.code, exc.message, exc.details)
        except Exception as exc:
            return error_json("tool_execution_failed", "Tool execution failed", {"tool": tool, "error_type": type(exc).__name__, "message": str(exc)})

    def _execute_with_retry(self, fn: Callable[[CloudConfig, Any], dict[str, Any]], cloud: CloudConfig, conn: Any) -> dict[str, Any]:
        attempts = max(1, self.policy.retries + 1)
        last_exc: Exception | None = None
        for _ in range(attempts):
            try:
                return fn(cloud, conn)
            except DiagnosticError:
                raise
            except Exception as exc:
                last_exc = exc
        assert last_exc is not None
        raise last_exc

    def cloud_list(self) -> dict[str, Any]:
        return {"result": {"clouds": [{"cloud_id": c.cloud_id, "region_name": c.region_name, "interface": c.interface, "storage_backend": c.storage_backend, "ceph": c.ceph, "linked_k8s": linked_k8s(c)} for c in self.config.clouds.values()]}}

    def cloud_get(self, cloud_id: str) -> dict[str, Any]:
        try:
            cloud = self.registry.get(cloud_id)
            return {"result": {"cloud": {"cloud_id": cloud.cloud_id, "region_name": cloud.region_name, "interface": cloud.interface, "storage_backend": cloud.storage_backend, "ceph": cloud.ceph, "linked_k8s": linked_k8s(cloud)}}}
        except DiagnosticError as exc:
            return error_json(exc.code, exc.message, exc.details)

    def check_auth(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "cloud.check_auth", lambda cloud, conn: {"authenticated": True, "current_project_id": _safe_call(conn, "current_project_id"), "current_user_id": _safe_call(conn, "current_user_id")})

    def get_service_catalog(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "cloud.get_service_catalog", lambda cloud, conn: {"catalog": serialize(getattr(getattr(conn, "session", None), "auth", None).get_access(getattr(conn, "session", None)).service_catalog.catalog if getattr(getattr(conn, "session", None), "auth", None) else [])})

    def get_endpoints(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "cloud.get_endpoints", lambda cloud, conn: {"endpoints": _list_proxy(getattr(conn, "identity", None), "endpoints", self.policy.max_results)})

    def diagnose_api_health(self, cloud_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            checks = {
                "compute": _has_endpoint(conn, "compute"),
                "network": _has_endpoint(conn, "network"),
                "volumev3": _has_endpoint(conn, "volumev3"),
                "image": _has_endpoint(conn, "image"),
                "placement": _has_endpoint(conn, "placement"),
            }
            unhealthy = [svc for svc, ok in checks.items() if not ok]
            findings = [{"severity": "critical", "reason": "MissingServiceEndpoint", "evidence": unhealthy}] if unhealthy else [{"severity": "info", "reason": "ApiCatalogLooksHealthy", "evidence": ["Required endpoints resolved."]}]
            return {"checks": checks, "findings": findings}
        return self._wrap(cloud_id, "cloud.diagnose_api_health", run, diagnose=True, k8s_reason="OpenStack API endpoint issue may be caused by unhealthy API pods.")

    def nova_get_services(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "nova.get_services", lambda cloud, conn: {"services": _list_proxy(conn.compute, "services", self.policy.max_results)})

    def nova_get_hypervisors(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "nova.get_hypervisors", lambda cloud, conn: {"hypervisors": _list_proxy(conn.compute, "hypervisors", self.policy.max_results)})

    def nova_get_hypervisor(self, cloud_id: str, hypervisor_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "nova.get_hypervisor", lambda cloud, conn: {"hypervisor": serialize(conn.compute.get_hypervisor(hypervisor_id))})

    def nova_get_availability_zones(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "nova.get_availability_zones", lambda cloud, conn: {"availability_zones": _list_proxy(conn.compute, "availability_zones", self.policy.max_results)})

    def nova_get_aggregates(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "nova.get_aggregates", lambda cloud, conn: {"aggregates": _list_proxy(conn.compute, "aggregates", self.policy.max_results)})

    def nova_list_servers(self, cloud_id: str, limit: int | None = None) -> dict[str, Any]:
        return self._wrap(cloud_id, "nova.list_servers", lambda cloud, conn: {"servers": _list_proxy(conn.compute, "servers", self.policy.clamp_limit(limit), all_projects=True)})

    def nova_get_server(self, cloud_id: str, server_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "nova.get_server", lambda cloud, conn: {"server": serialize(conn.compute.get_server(server_id))})

    def nova_get_server_actions(self, cloud_id: str, server_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "nova.get_server_actions", lambda cloud, conn: {"actions": _list_from_call(conn.compute, "server_actions", self.policy.max_results, server_id)})

    def nova_get_migrations(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "nova.get_migrations", lambda cloud, conn: {"migrations": _list_proxy(conn.compute, "migrations", self.policy.max_results)})

    def nova_diagnose_server(self, cloud_id: str, server_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            server = serialize(conn.compute.get_server(server_id))
            return {"server": server, "findings": diagnose_server_data(server)}
        return self._wrap(cloud_id, "nova.diagnose_server", run, diagnose=True, k8s_component="nova")

    def nova_diagnose_build_failure(self, cloud_id: str, server_id: str) -> dict[str, Any]:
        return self.nova_diagnose_server(cloud_id, server_id)

    def nova_diagnose_no_valid_host(self, cloud_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            hypervisors = _list_proxy(conn.compute, "hypervisors", self.policy.max_results)
            providers = self._placement_list(conn, "resource_providers")
            return {"findings": diagnose_no_valid_host_data(hypervisors, providers), "hypervisors": hypervisors, "resource_providers_sample": providers[:50]}
        return self._wrap(cloud_id, "nova.diagnose_no_valid_host", run, diagnose=True, k8s_component="nova")

    def nova_diagnose_compute_host(self, cloud_id: str, host: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            services = [s for s in _list_proxy(conn.compute, "services", self.policy.max_results) if host in str(s.get("host", ""))]
            hypervisors = [h for h in _list_proxy(conn.compute, "hypervisors", self.policy.max_results) if host in str(h.get("name") or h.get("hypervisor_hostname", ""))]
            return {"services": services, "hypervisors": hypervisors, "findings": diagnose_no_valid_host_data(hypervisors)}
        return self._wrap(cloud_id, "nova.diagnose_compute_host", run, diagnose=True, k8s_component="nova")

    def nova_diagnose_capacity(self, cloud_id: str) -> dict[str, Any]:
        return self.nova_diagnose_no_valid_host(cloud_id)

    def neutron_get_agents(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "neutron.get_agents", lambda cloud, conn: {"agents": _list_proxy(conn.network, "agents", self.policy.max_results)})

    def neutron_get_networks(self, cloud_id: str, limit: int | None = None) -> dict[str, Any]:
        return self._wrap(cloud_id, "neutron.get_networks", lambda cloud, conn: {"networks": _list_proxy(conn.network, "networks", self.policy.clamp_limit(limit))})

    def neutron_get_subnets(self, cloud_id: str, limit: int | None = None) -> dict[str, Any]:
        return self._wrap(cloud_id, "neutron.get_subnets", lambda cloud, conn: {"subnets": _list_proxy(conn.network, "subnets", self.policy.clamp_limit(limit))})

    def neutron_get_ports(self, cloud_id: str, limit: int | None = None) -> dict[str, Any]:
        return self._wrap(cloud_id, "neutron.get_ports", lambda cloud, conn: {"ports": _list_proxy(conn.network, "ports", self.policy.clamp_limit(limit))})

    def neutron_get_port(self, cloud_id: str, port_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "neutron.get_port", lambda cloud, conn: {"port": serialize(conn.network.get_port(port_id))})

    def neutron_get_routers(self, cloud_id: str, limit: int | None = None) -> dict[str, Any]:
        return self._wrap(cloud_id, "neutron.get_routers", lambda cloud, conn: {"routers": _list_proxy(conn.network, "routers", self.policy.clamp_limit(limit))})

    def neutron_get_floatingips(self, cloud_id: str, limit: int | None = None) -> dict[str, Any]:
        return self._wrap(cloud_id, "neutron.get_floatingips", lambda cloud, conn: {"floatingips": _list_proxy(conn.network, "ips", self.policy.clamp_limit(limit))})

    def neutron_get_security_groups(self, cloud_id: str, limit: int | None = None) -> dict[str, Any]:
        return self._wrap(cloud_id, "neutron.get_security_groups", lambda cloud, conn: {"security_groups": _list_proxy(conn.network, "security_groups", self.policy.clamp_limit(limit))})

    def neutron_diagnose_vm_network(self, cloud_id: str, server_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            ports = _list_proxy(conn.network, "ports", self.policy.max_results, device_id=server_id)
            return {"ports": ports, "findings": diagnose_network_data(ports)}
        return self._wrap(cloud_id, "neutron.diagnose_vm_network", run, diagnose=True, k8s_component="neutron")

    def neutron_diagnose_port(self, cloud_id: str, port_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            port = serialize(conn.network.get_port(port_id))
            return {"port": port, "findings": diagnose_network_data([port])}
        return self._wrap(cloud_id, "neutron.diagnose_port", run, diagnose=True, k8s_component="neutron")

    def neutron_diagnose_router(self, cloud_id: str, router_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            router = serialize(conn.network.get_router(router_id))
            return {"router": router, "findings": diagnose_network_data([], [router])}
        return self._wrap(cloud_id, "neutron.diagnose_router", run, diagnose=True, k8s_component="neutron")

    def neutron_diagnose_floatingip(self, cloud_id: str, floatingip_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "neutron.diagnose_floatingip", lambda cloud, conn: {"floatingip": serialize(conn.network.get_ip(floatingip_id)), "findings": [{"severity": "info", "reason": "FloatingIpRetrieved", "evidence": [floatingip_id]}]}, diagnose=True, k8s_component="neutron")

    def cinder_get_services(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "cinder.get_services", lambda cloud, conn: {"services": _list_proxy(conn.block_storage, "services", self.policy.max_results)})

    def cinder_get_volume(self, cloud_id: str, volume_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "cinder.get_volume", lambda cloud, conn: {"volume": serialize(conn.block_storage.get_volume(volume_id))})

    def cinder_list_volumes(self, cloud_id: str, limit: int | None = None) -> dict[str, Any]:
        return self._wrap(cloud_id, "cinder.list_volumes", lambda cloud, conn: {"volumes": _list_proxy(conn.block_storage, "volumes", self.policy.clamp_limit(limit), all_projects=True)})

    def cinder_get_volume_attachments(self, cloud_id: str, volume_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "cinder.get_volume_attachments", lambda cloud, conn: {"attachments": serialize(getattr(conn.block_storage.get_volume(volume_id), "attachments", []))})

    def cinder_get_volume_types(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "cinder.get_volume_types", lambda cloud, conn: {"volume_types": _list_proxy(conn.block_storage, "types", self.policy.max_results)})

    def cinder_get_pools(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "cinder.get_pools", lambda cloud, conn: {"pools": _list_proxy(conn.block_storage, "backend_pools", self.policy.max_results)})

    def cinder_diagnose_volume(self, cloud_id: str, volume_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            volume = serialize(conn.block_storage.get_volume(volume_id))
            return {"volume": volume, "findings": diagnose_volume_data(volume)}
        return self._wrap(cloud_id, "cinder.diagnose_volume", run, diagnose=True, k8s_component="cinder")

    def cinder_diagnose_attachment(self, cloud_id: str, volume_id: str) -> dict[str, Any]:
        return self.cinder_diagnose_volume(cloud_id, volume_id)

    def cinder_diagnose_backend(self, cloud_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            services = _list_proxy(conn.block_storage, "services", self.policy.max_results)
            pools = _list_proxy(conn.block_storage, "backend_pools", self.policy.max_results)
            return {"services": services, "pools": pools, "findings": diagnose_powerflex_data(services, pools)}
        return self._wrap(cloud_id, "cinder.diagnose_backend", run, diagnose=True, k8s_component="cinder")

    def cinder_diagnose_powerflex(self, cloud_id: str) -> dict[str, Any]:
        return self.cinder_diagnose_backend(cloud_id)

    def glance_list_images(self, cloud_id: str, limit: int | None = None) -> dict[str, Any]:
        return self._wrap(cloud_id, "glance.list_images", lambda cloud, conn: {"images": _list_proxy(conn.image, "images", self.policy.clamp_limit(limit))})

    def glance_get_image(self, cloud_id: str, image_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "glance.get_image", lambda cloud, conn: {"image": serialize(conn.image.get_image(image_id))})

    def glance_diagnose_image(self, cloud_id: str, image_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            image = serialize(conn.image.get_image(image_id))
            status = str(image.get("status", "")).lower()
            findings = [{"severity": "critical", "reason": "ImageNotActive", "evidence": [f"image_status={status}"]}] if status and status != "active" else [{"severity": "info", "reason": "ImageLooksActive", "evidence": [f"image_status={status}"]}]
            return {"image": image, "findings": findings}
        return self._wrap(cloud_id, "glance.diagnose_image", run, diagnose=True, k8s_component="glance")

    def keystone_get_project(self, cloud_id: str, project_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "keystone.get_project", lambda cloud, conn: {"project": serialize(conn.identity.get_project(project_id))})

    def keystone_list_projects(self, cloud_id: str, limit: int | None = None) -> dict[str, Any]:
        return self._wrap(cloud_id, "keystone.list_projects", lambda cloud, conn: {"projects": _list_proxy(conn.identity, "projects", self.policy.clamp_limit(limit))})

    def quota_get_compute_quota(self, cloud_id: str, project_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "quota.get_compute_quota", lambda cloud, conn: {"quota": serialize(conn.compute.get_quota_set(project_id))})

    def quota_get_network_quota(self, cloud_id: str, project_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "quota.get_network_quota", lambda cloud, conn: {"quota": serialize(conn.network.get_quota(project_id))})

    def quota_get_volume_quota(self, cloud_id: str, project_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "quota.get_volume_quota", lambda cloud, conn: {"quota": serialize(conn.block_storage.get_quota_set(project_id))})

    def quota_diagnose_project_quota(self, cloud_id: str, project_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            quotas = {"compute": serialize(conn.compute.get_quota_set(project_id)), "network": serialize(conn.network.get_quota(project_id)), "volume": serialize(conn.block_storage.get_quota_set(project_id))}
            findings = [{"severity": "info", "reason": "QuotaRetrieved", "evidence": [project_id]}]
            return {"quotas": quotas, "findings": findings}
        return self._wrap(cloud_id, "quota.diagnose_project_quota", run, diagnose=True)

    def placement_get_resource_providers(self, cloud_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "placement.get_resource_providers", lambda cloud, conn: {"resource_providers": self._placement_list(conn, "resource_providers"), "data_sources": ["placement_rest_api"]})

    def placement_get_resource_provider(self, cloud_id: str, resource_provider_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "placement.get_resource_provider", lambda cloud, conn: {"resource_provider": self.rest_factory(conn).get("placement", f"/resource_providers/{resource_provider_id}", "1.39"), "data_sources": ["placement_rest_api"]})

    def placement_get_inventories(self, cloud_id: str, resource_provider_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "placement.get_inventories", lambda cloud, conn: {"inventories": self.rest_factory(conn).get("placement", f"/resource_providers/{resource_provider_id}/inventories", "1.39"), "data_sources": ["placement_rest_api"]})

    def placement_get_usages(self, cloud_id: str, resource_provider_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "placement.get_usages", lambda cloud, conn: {"usages": self.rest_factory(conn).get("placement", f"/resource_providers/{resource_provider_id}/usages", "1.39"), "data_sources": ["placement_rest_api"]})

    def placement_get_allocations(self, cloud_id: str, resource_provider_id: str) -> dict[str, Any]:
        return self._wrap(cloud_id, "placement.get_allocations", lambda cloud, conn: {"allocations": self.rest_factory(conn).get("placement", f"/resource_providers/{resource_provider_id}/allocations", "1.39"), "data_sources": ["placement_rest_api"]})

    def placement_diagnose_capacity(self, cloud_id: str) -> dict[str, Any]:
        return self.nova_diagnose_no_valid_host(cloud_id)

    def placement_diagnose_no_valid_host(self, cloud_id: str) -> dict[str, Any]:
        return self.nova_diagnose_no_valid_host(cloud_id)

    def placement_diagnose_allocation_mismatch(self, cloud_id: str, resource_provider_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            rest = self.rest_factory(conn)
            inventories = rest.get("placement", f"/resource_providers/{resource_provider_id}/inventories", "1.39")
            usages = rest.get("placement", f"/resource_providers/{resource_provider_id}/usages", "1.39")
            return {"inventories": inventories, "usages": usages, "findings": [{"severity": "info", "reason": "PlacementInventoryUsageRetrieved", "evidence": [resource_provider_id]}], "data_sources": ["placement_rest_api"]}
        return self._wrap(cloud_id, "placement.diagnose_allocation_mismatch", run, diagnose=True, k8s_component="nova")

    def diagnose_cloud(self, cloud_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            services = _list_proxy(conn.compute, "services", self.policy.max_results)
            cinder_services = _list_proxy(conn.block_storage, "services", self.policy.max_results)
            findings = diagnose_no_valid_host_data([]) + diagnose_powerflex_data(cinder_services, [])
            return {"nova_services": services, "cinder_services": cinder_services, "findings": findings}
        return self._wrap(cloud_id, "diagnose.cloud", run, diagnose=True)

    def diagnose_vm_create_failure(self, cloud_id: str, server_id: str | None = None) -> dict[str, Any]:
        if server_id:
            return self.nova_diagnose_build_failure(cloud_id, server_id)
        return self.nova_diagnose_no_valid_host(cloud_id)

    def diagnose_vm_network(self, cloud_id: str, server_id: str) -> dict[str, Any]:
        return self.neutron_diagnose_vm_network(cloud_id, server_id)

    def diagnose_volume_attachment(self, cloud_id: str, volume_id: str) -> dict[str, Any]:
        return self.cinder_diagnose_attachment(cloud_id, volume_id)

    def diagnose_openstack_helm_correlation(self, cloud_id: str) -> dict[str, Any]:
        def run(cloud: CloudConfig, conn: Any):
            return {
                "correlation": "OpenStack service symptoms should be correlated with openstack-helm pods/events in the linked Kubernetes MCP.",
                "recommended_next_tools": recommend_k8s_tools(cloud, reason="Correlate OpenStack API/service symptoms with openstack-helm workloads."),
            }
        return self._wrap(cloud_id, "diagnose.openstack_helm_correlation", run, diagnose=True)

    def recommend_k8s_diagnostics(self, cloud_id: str, component: str | None = None) -> dict[str, Any]:
        try:
            cloud = self.registry.get(cloud_id)
            return {"result": {"linked_k8s": linked_k8s(cloud), "recommended_next_tools": recommend_k8s_tools(cloud, component=component)}}
        except DiagnosticError as exc:
            return error_json(exc.code, exc.message, exc.details)

    def runbook_search(self, query: str, limit: int = 10) -> dict[str, Any]:
        return {"result": {"matches": self.runbooks.search(query, limit)}, "data_sources": ["local_runbooks"]}

    def runbook_get(self, runbook_id: str) -> dict[str, Any]:
        return {"result": self.runbooks.get(runbook_id), "data_sources": ["local_runbooks"]}

    def _placement_list(self, conn: Any, key: str) -> list[dict[str, Any]]:
        payload = self.rest_factory(conn).get("placement", f"/{key}", "1.39")
        return serialize(payload.get(key, []))[: self.policy.max_results]


def _safe_call(obj: Any, attr: str) -> Any:
    value = getattr(obj, attr, None)
    return value() if callable(value) else value


def _list_proxy(proxy: Any, method: str, limit: int, **kwargs: Any) -> list[dict[str, Any]]:
    if proxy is None:
        return []
    fn = getattr(proxy, method)
    return limited(fn(**kwargs), limit)


def _list_from_call(proxy: Any, method: str, limit: int, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    if proxy is None:
        return []
    return limited(getattr(proxy, method)(*args, **kwargs), limit)


def _has_endpoint(conn: Any, service_type: str) -> bool:
    try:
        return bool(conn.endpoint_for(service_type=service_type))
    except Exception:
        return False


def _result_count(result: dict[str, Any]) -> int:
    for value in result.values():
        if isinstance(value, list):
            return len(value)
    return 1


def _default_runbook_root() -> Path:
    configured = os.getenv("OCP_OPENSTACK_DIAG_RUNBOOK_DIR")
    if configured:
        return Path(configured)
    project_root = Path(__file__).resolve().parents[2]
    if (project_root / "runbooks").exists():
        return project_root / "runbooks"
    return Path.cwd() / "runbooks"
