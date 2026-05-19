from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .service import DiagnosticService


def create_mcp(service: DiagnosticService | None = None, host: str = "127.0.0.1", port: int = 8000, path: str = "/mcp") -> FastMCP:
    svc = service or DiagnosticService()
    mcp = FastMCP("ocp-openstack-diagnostic-mcp", host=host, port=port, streamable_http_path=path)

    @mcp.tool(name="cloud.list")
    def cloud_list() -> dict:
        """List configured OpenStack cloud_id values. Use this first if the user says OpenStack but no cloud_id is known."""
        return svc.cloud_list()

    @mcp.tool(name="cloud.get")
    def cloud_get(cloud_id: str) -> dict:
        """Get one configured OpenStack cloud by cloud_id, for example cloud_id=openstack."""
        return svc.cloud_get(cloud_id)

    @mcp.tool(name="cloud.check_auth")
    def cloud_check_auth(cloud_id: str) -> dict:
        """Verify OpenStack authentication for cloud_id without exposing credentials."""
        return svc.check_auth(cloud_id)

    @mcp.tool(name="cloud.get_service_catalog")
    def cloud_get_service_catalog(cloud_id: str) -> dict:
        """Return Keystone service catalog endpoints for OpenStack API routing diagnostics."""
        return svc.get_service_catalog(cloud_id)

    @mcp.tool(name="cloud.get_endpoints")
    def cloud_get_endpoints(cloud_id: str) -> dict:
        """List Keystone endpoints for OpenStack services."""
        return svc.get_endpoints(cloud_id)

    @mcp.tool(name="cloud.diagnose_api_health")
    def cloud_diagnose_api_health(cloud_id: str) -> dict:
        """Diagnose OpenStack API endpoint availability from Keystone catalog and SDK connectivity."""
        return svc.diagnose_api_health(cloud_id)

    @mcp.tool(name="nova.get_services")
    def nova_get_services(cloud_id: str) -> dict:
        """List Nova compute services. Use for OpenStack compute service status."""
        return svc.nova_get_services(cloud_id)

    @mcp.tool(name="nova.get_hypervisors")
    def nova_get_hypervisors(cloud_id: str) -> dict:
        """List OpenStack compute nodes/hypervisors. Use when the user asks for OpenStack nodes."""
        return svc.nova_get_hypervisors(cloud_id)

    @mcp.tool(name="nova.get_hypervisor")
    def nova_get_hypervisor(cloud_id: str, hypervisor_id: str) -> dict:
        """Get one OpenStack hypervisor by id/name returned from nova.get_hypervisors."""
        return svc.nova_get_hypervisor(cloud_id, hypervisor_id)

    @mcp.tool(name="nova.get_availability_zones")
    def nova_get_availability_zones(cloud_id: str) -> dict:
        """List Nova availability zones."""
        return svc.nova_get_availability_zones(cloud_id)

    @mcp.tool(name="nova.get_aggregates")
    def nova_get_aggregates(cloud_id: str) -> dict:
        """List Nova host aggregates."""
        return svc.nova_get_aggregates(cloud_id)

    @mcp.tool(name="nova.list_servers")
    def nova_list_servers(cloud_id: str, limit: int | None = 200) -> dict:
        """List OpenStack VM/server instances. Use when the user asks for VMs or servers."""
        return svc.nova_list_servers(cloud_id, limit)

    @mcp.tool(name="nova.get_server")
    def nova_get_server(cloud_id: str, server_id: str) -> dict:
        """Get one OpenStack VM/server by server_id."""
        return svc.nova_get_server(cloud_id, server_id)

    @mcp.tool(name="nova.get_server_actions")
    def nova_get_server_actions(cloud_id: str, server_id: str) -> dict:
        """List Nova action/event history for one VM/server."""
        return svc.nova_get_server_actions(cloud_id, server_id)

    @mcp.tool(name="nova.get_migrations")
    def nova_get_migrations(cloud_id: str) -> dict:
        """List Nova migrations."""
        return svc.nova_get_migrations(cloud_id)

    @mcp.tool(name="nova.diagnose_server")
    def nova_diagnose_server(cloud_id: str, server_id: str) -> dict:
        """Diagnose one VM/server from Nova status and action data."""
        return svc.nova_diagnose_server(cloud_id, server_id)

    @mcp.tool(name="nova.diagnose_build_failure")
    def nova_diagnose_build_failure(cloud_id: str, server_id: str) -> dict:
        """Diagnose VM build/create failure for a known server_id."""
        return svc.nova_diagnose_build_failure(cloud_id, server_id)

    @mcp.tool(name="nova.diagnose_no_valid_host")
    def nova_diagnose_no_valid_host(cloud_id: str) -> dict:
        """Diagnose NoValidHost and capacity symptoms from Nova hypervisors and Placement."""
        return svc.nova_diagnose_no_valid_host(cloud_id)

    @mcp.tool(name="nova.diagnose_compute_host")
    def nova_diagnose_compute_host(cloud_id: str, host: str) -> dict:
        """Diagnose one OpenStack compute host by hostname fragment."""
        return svc.nova_diagnose_compute_host(cloud_id, host)

    @mcp.tool(name="nova.diagnose_capacity")
    def nova_diagnose_capacity(cloud_id: str) -> dict:
        """Diagnose OpenStack compute capacity using Nova and Placement data."""
        return svc.nova_diagnose_capacity(cloud_id)

    @mcp.tool(name="neutron.get_agents")
    def neutron_get_agents(cloud_id: str) -> dict:
        """List Neutron agents and their status."""
        return svc.neutron_get_agents(cloud_id)

    @mcp.tool(name="neutron.get_networks")
    def neutron_get_networks(cloud_id: str, limit: int | None = 200) -> dict:
        """List Neutron networks."""
        return svc.neutron_get_networks(cloud_id, limit)

    @mcp.tool(name="neutron.get_subnets")
    def neutron_get_subnets(cloud_id: str, limit: int | None = 200) -> dict:
        """List Neutron subnets."""
        return svc.neutron_get_subnets(cloud_id, limit)

    @mcp.tool(name="neutron.get_ports")
    def neutron_get_ports(cloud_id: str, limit: int | None = 200) -> dict:
        """List Neutron ports."""
        return svc.neutron_get_ports(cloud_id, limit)

    @mcp.tool(name="neutron.get_port")
    def neutron_get_port(cloud_id: str, port_id: str) -> dict:
        """Get one Neutron port by port_id."""
        return svc.neutron_get_port(cloud_id, port_id)

    @mcp.tool(name="neutron.get_routers")
    def neutron_get_routers(cloud_id: str, limit: int | None = 200) -> dict:
        return svc.neutron_get_routers(cloud_id, limit)

    @mcp.tool(name="neutron.get_floatingips")
    def neutron_get_floatingips(cloud_id: str, limit: int | None = 200) -> dict:
        return svc.neutron_get_floatingips(cloud_id, limit)

    @mcp.tool(name="neutron.get_security_groups")
    def neutron_get_security_groups(cloud_id: str, limit: int | None = 200) -> dict:
        return svc.neutron_get_security_groups(cloud_id, limit)

    @mcp.tool(name="neutron.diagnose_vm_network")
    def neutron_diagnose_vm_network(cloud_id: str, server_id: str) -> dict:
        """Diagnose VM network issues from Neutron ports for a server_id."""
        return svc.neutron_diagnose_vm_network(cloud_id, server_id)

    @mcp.tool(name="neutron.diagnose_port")
    def neutron_diagnose_port(cloud_id: str, port_id: str) -> dict:
        return svc.neutron_diagnose_port(cloud_id, port_id)

    @mcp.tool(name="neutron.diagnose_router")
    def neutron_diagnose_router(cloud_id: str, router_id: str) -> dict:
        return svc.neutron_diagnose_router(cloud_id, router_id)

    @mcp.tool(name="neutron.diagnose_floatingip")
    def neutron_diagnose_floatingip(cloud_id: str, floatingip_id: str) -> dict:
        return svc.neutron_diagnose_floatingip(cloud_id, floatingip_id)

    @mcp.tool(name="cinder.get_services")
    def cinder_get_services(cloud_id: str) -> dict:
        """List Cinder volume services."""
        return svc.cinder_get_services(cloud_id)

    @mcp.tool(name="cinder.get_volume")
    def cinder_get_volume(cloud_id: str, volume_id: str) -> dict:
        return svc.cinder_get_volume(cloud_id, volume_id)

    @mcp.tool(name="cinder.list_volumes")
    def cinder_list_volumes(cloud_id: str, limit: int | None = 200) -> dict:
        """List Cinder volumes."""
        return svc.cinder_list_volumes(cloud_id, limit)

    @mcp.tool(name="cinder.get_volume_attachments")
    def cinder_get_volume_attachments(cloud_id: str, volume_id: str) -> dict:
        return svc.cinder_get_volume_attachments(cloud_id, volume_id)

    @mcp.tool(name="cinder.get_volume_types")
    def cinder_get_volume_types(cloud_id: str) -> dict:
        return svc.cinder_get_volume_types(cloud_id)

    @mcp.tool(name="cinder.get_pools")
    def cinder_get_pools(cloud_id: str) -> dict:
        return svc.cinder_get_pools(cloud_id)

    @mcp.tool(name="cinder.diagnose_volume")
    def cinder_diagnose_volume(cloud_id: str, volume_id: str) -> dict:
        return svc.cinder_diagnose_volume(cloud_id, volume_id)

    @mcp.tool(name="cinder.diagnose_attachment")
    def cinder_diagnose_attachment(cloud_id: str, volume_id: str) -> dict:
        return svc.cinder_diagnose_attachment(cloud_id, volume_id)

    @mcp.tool(name="cinder.diagnose_backend")
    def cinder_diagnose_backend(cloud_id: str) -> dict:
        return svc.cinder_diagnose_backend(cloud_id)

    @mcp.tool(name="cinder.diagnose_powerflex")
    def cinder_diagnose_powerflex(cloud_id: str) -> dict:
        """Diagnose PowerFlex-backed Cinder backend status."""
        return svc.cinder_diagnose_powerflex(cloud_id)

    @mcp.tool(name="glance.list_images")
    def glance_list_images(cloud_id: str, limit: int | None = 200) -> dict:
        """List Glance images."""
        return svc.glance_list_images(cloud_id, limit)

    @mcp.tool(name="glance.get_image")
    def glance_get_image(cloud_id: str, image_id: str) -> dict:
        return svc.glance_get_image(cloud_id, image_id)

    @mcp.tool(name="glance.diagnose_image")
    def glance_diagnose_image(cloud_id: str, image_id: str) -> dict:
        return svc.glance_diagnose_image(cloud_id, image_id)

    @mcp.tool(name="keystone.get_project")
    def keystone_get_project(cloud_id: str, project_id: str) -> dict:
        return svc.keystone_get_project(cloud_id, project_id)

    @mcp.tool(name="keystone.list_projects")
    def keystone_list_projects(cloud_id: str, limit: int | None = 200) -> dict:
        return svc.keystone_list_projects(cloud_id, limit)

    @mcp.tool(name="quota.get_compute_quota")
    def quota_get_compute_quota(cloud_id: str, project_id: str) -> dict:
        return svc.quota_get_compute_quota(cloud_id, project_id)

    @mcp.tool(name="quota.get_network_quota")
    def quota_get_network_quota(cloud_id: str, project_id: str) -> dict:
        return svc.quota_get_network_quota(cloud_id, project_id)

    @mcp.tool(name="quota.get_volume_quota")
    def quota_get_volume_quota(cloud_id: str, project_id: str) -> dict:
        return svc.quota_get_volume_quota(cloud_id, project_id)

    @mcp.tool(name="quota.diagnose_project_quota")
    def quota_diagnose_project_quota(cloud_id: str, project_id: str) -> dict:
        """Diagnose project quota across compute, network, and volume services."""
        return svc.quota_diagnose_project_quota(cloud_id, project_id)

    @mcp.tool(name="placement.get_resource_providers")
    def placement_get_resource_providers(cloud_id: str) -> dict:
        """List Placement resource providers."""
        return svc.placement_get_resource_providers(cloud_id)

    @mcp.tool(name="placement.get_resource_provider")
    def placement_get_resource_provider(cloud_id: str, resource_provider_id: str) -> dict:
        return svc.placement_get_resource_provider(cloud_id, resource_provider_id)

    @mcp.tool(name="placement.get_inventories")
    def placement_get_inventories(cloud_id: str, resource_provider_id: str) -> dict:
        return svc.placement_get_inventories(cloud_id, resource_provider_id)

    @mcp.tool(name="placement.get_usages")
    def placement_get_usages(cloud_id: str, resource_provider_id: str) -> dict:
        return svc.placement_get_usages(cloud_id, resource_provider_id)

    @mcp.tool(name="placement.get_allocations")
    def placement_get_allocations(cloud_id: str, resource_provider_id: str) -> dict:
        return svc.placement_get_allocations(cloud_id, resource_provider_id)

    @mcp.tool(name="placement.diagnose_capacity")
    def placement_diagnose_capacity(cloud_id: str) -> dict:
        return svc.placement_diagnose_capacity(cloud_id)

    @mcp.tool(name="placement.diagnose_no_valid_host")
    def placement_diagnose_no_valid_host(cloud_id: str) -> dict:
        return svc.placement_diagnose_no_valid_host(cloud_id)

    @mcp.tool(name="placement.diagnose_allocation_mismatch")
    def placement_diagnose_allocation_mismatch(cloud_id: str, resource_provider_id: str) -> dict:
        return svc.placement_diagnose_allocation_mismatch(cloud_id, resource_provider_id)

    @mcp.tool(name="diagnose.cloud")
    def diagnose_cloud(cloud_id: str) -> dict:
        """Run broad read-only OpenStack cloud diagnosis. Use for 'openstack 점검'."""
        return svc.diagnose_cloud(cloud_id)

    @mcp.tool(name="diagnose.vm_create_failure")
    def diagnose_vm_create_failure(cloud_id: str, server_id: str | None = None) -> dict:
        """Diagnose VM creation failure. If server_id is unknown, checks NoValidHost/capacity symptoms."""
        return svc.diagnose_vm_create_failure(cloud_id, server_id)

    @mcp.tool(name="diagnose.vm_network")
    def diagnose_vm_network(cloud_id: str, server_id: str) -> dict:
        return svc.diagnose_vm_network(cloud_id, server_id)

    @mcp.tool(name="diagnose.volume_attachment")
    def diagnose_volume_attachment(cloud_id: str, volume_id: str) -> dict:
        return svc.diagnose_volume_attachment(cloud_id, volume_id)

    @mcp.tool(name="diagnose.openstack_helm_correlation")
    def diagnose_openstack_helm_correlation(cloud_id: str) -> dict:
        return svc.diagnose_openstack_helm_correlation(cloud_id)

    @mcp.tool(name="openstack.recommend_k8s_diagnostics")
    def openstack_recommend_k8s_diagnostics(cloud_id: str, component: str | None = None) -> dict:
        """Recommend Kubernetes MCP tools for OpenStack Helm correlation; does not call Kubernetes directly."""
        return svc.recommend_k8s_diagnostics(cloud_id, component)

    @mcp.tool(name="runbook.search")
    def runbook_search(query: str, limit: int = 10) -> dict:
        return svc.runbook_search(query, limit)

    @mcp.tool(name="runbook.get")
    def runbook_get(runbook_id: str) -> dict:
        return svc.runbook_get(runbook_id)

    return mcp


def run_stdio() -> None:
    create_mcp().run(transport="stdio")


def run_http(host: str = "0.0.0.0", port: int = 8080, path: str = "/mcp") -> None:
    create_mcp(host=host, port=port, path=path).run(transport="streamable-http")
