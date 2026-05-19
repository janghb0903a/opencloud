from __future__ import annotations

from types import SimpleNamespace

import pytest

from ocp_openstack_diagnostic_mcp.config import CloudConfig, RuntimeConfig
from ocp_openstack_diagnostic_mcp.service import DiagnosticService


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


class FakeProxy:
    def __init__(self, **resources):
        self.resources = resources

    def __getattr__(self, name):
        if name.startswith("get_"):
            key = name[4:]

            def get_item(item_id):
                items = self.resources.get(f"{key}s", []) or self.resources.get(key, [])
                for item in items:
                    if item.get("id") == item_id:
                        return item
                return {"id": item_id, "status": "unknown"}

            return get_item

        def list_items(**kwargs):
            return iter(self.resources.get(name, []))

        return list_items


class FakeConn:
    def __init__(self):
        self.compute = FakeProxy(
            services=[{"binary": "nova-compute", "host": "compute-1", "state": "up", "status": "enabled"}],
            hypervisors=[{"id": "hv1", "name": "compute-1", "state": "up", "status": "enabled"}],
            servers=[{"id": "vm-error", "status": "ERROR", "fault": {"message": "NoValidHost"}}],
            availability_zones=[{"name": "nova", "state": "available"}],
            aggregates=[],
            migrations=[],
            server_actions=[{"action": "create", "message": "NoValidHost"}],
        )
        self.network = FakeProxy(
            agents=[{"id": "agent1", "alive": True}],
            networks=[{"id": "net1", "status": "ACTIVE"}],
            subnets=[{"id": "subnet1"}],
            ports=[{"id": "port-down", "device_id": "vm-error", "status": "DOWN"}],
            routers=[{"id": "router1", "status": "ACTIVE"}],
            ips=[{"id": "fip1", "status": "DOWN"}],
            security_groups=[{"id": "sg1"}],
        )
        self.block_storage = FakeProxy(
            services=[{"binary": "cinder-volume", "host": "powerflex@backend", "state": "down", "status": "enabled"}],
            volumes=[{"id": "vol-error", "status": "error", "attach_status": "error", "attachments": [{"server_id": "vm-error"}]}],
            types=[{"id": "type1", "name": "powerflex"}],
            backend_pools=[{"name": "powerflex", "total_capacity_gb": 100, "free_capacity_gb": 1}],
        )
        self.image = FakeProxy(images=[{"id": "img1", "status": "active"}])
        self.identity = FakeProxy(projects=[{"id": "proj1", "name": "demo"}], endpoints=[{"id": "ep1"}])

    def endpoint_for(self, service_type):
        return f"https://openstack.example.internal/{service_type}"

    def authorize(self):
        return "secret-token"

    def current_project_id(self):
        return "proj1"

    def current_user_id(self):
        return "user1"


class FakeFactory:
    def __init__(self, conn=None):
        self.conn = conn or FakeConn()

    def create(self, cloud):
        return self.conn


class FakeRest:
    def __init__(self, conn):
        self.conn = conn

    def get(self, service_type, path, microversion=None):
        if path == "/resource_providers":
            return {"resource_providers": [{"uuid": "rp1", "name": "compute-1"}]}
        if "inventories" in path:
            return {"inventories": {"VCPU": {"total": 4}}}
        if "usages" in path:
            return {"usages": {"VCPU": 4}}
        if "allocations" in path:
            return {"allocations": {}}
        return {"uuid": path.rsplit("/", 1)[-1], "name": "compute-1"}


@pytest.fixture
def runtime_config():
    return RuntimeConfig(
        clouds={
            "test-mgmt-02": CloudConfig(
                cloud_id="test-mgmt-02",
                cloud="test-mgmt-02",
                region_name="RegionOne",
                interface="internal",
                clouds_yaml_ref="file:/tmp/clouds.yaml",
                storage_backend="PowerFlex",
                ceph=False,
                linked_k8s={"mcp_server": "ocp-k8s-diagnostic-mcp", "cluster_id": "test-mgmt-02", "namespace": "openstack-helm"},
            )
        },
        policies={"limits": {"max_results": 500, "timeout_seconds": 20, "stdout_limit_bytes": 262144}},
        cli_allowlist={"commands": [{"argv_prefix": ["openstack", "server", "show"]}]},
    )


@pytest.fixture
def service(runtime_config):
    return DiagnosticService(runtime_config=runtime_config, client_factory=FakeFactory(), rest_factory=lambda conn: FakeRest(conn))

