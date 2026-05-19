# Claude Code Usage

HTTP MCP endpoint after Helm deployment:

```bash
claude mcp add --transport http ocp-openstack-diagnostic-mcp \
  --scope user \
  https://ocp-openstack-diagnostic-mcp.example.internal/mcp
```

Every OpenStack tool requires `cloud_id` except `cloud.list`, `runbook.search`, and `runbook.get`.

## Target Routing

This MCP server is the source of truth for OpenStack diagnostics only.

Use this MCP server when the user asks about:

- OpenStack
- Nova, Neutron, Cinder, Glance, Keystone, Placement
- VM/server create failures
- hypervisors or compute hosts
- OpenStack networks, routers, ports, floating IPs
- volumes, attachments, volume backends, PowerFlex
- images, projects, quotas, API catalog, endpoints

If the configured user-facing cloud id is `openstack`, use `cloud_id=openstack` when the user says "openstack".

Do not use this MCP server for Kubernetes cluster ids such as `mgmt`, `test-app-01`, `dev-app-01`, `test-genai-01`, `test-genai-02`, `test-mgmt-01`, or `test-mgmt-02` unless the user explicitly asks for OpenStack/OpenStack Helm correlation. Those ids belong to the Kubernetes MCP.

## Answering Rules

Never invent infrastructure names. Hypervisor names, VM names, project ids, network ids, volume ids, image ids, endpoints, IPs, and health states must come from MCP tool results.

Call the relevant MCP tool before answering OpenStack infrastructure questions. Do not provide example names such as `node-01`, `compute-01`, `vm-01`, or `nova-01` before a tool result is available.

After calling a tool, wait for the tool result before giving the final answer. Do not say that a tool is missing, failed, or still waiting unless the returned MCP payload explicitly contains an `error` object.

If a tool returns a normal `result` with an empty list, say that the query succeeded but returned no matching data. Do not call that a tool failure.

If a tool returns an `error` object, say `MCP 조회 실패` and summarize the error code/message only.

## OpenStack Tool Selection

Use `cloud.check_auth` to verify OpenStack authentication.

Use `cloud.diagnose_api_health` for OpenStack API endpoint health.

Use `diagnose.cloud` for broad OpenStack health checks.

Use `nova.get_hypervisors` when the user asks for OpenStack nodes, compute nodes, or hypervisors.

Use `nova.get_services` when the user asks for Nova service status.

Use `nova.list_servers` for VM/server lists.

Use `nova.get_server` and `nova.get_server_actions` when the user provides a server id.

Use `nova.diagnose_no_valid_host` or `diagnose.vm_create_failure` for VM creation failures or NoValidHost.

Use `neutron.*` tools for VM network, router, floating IP, port, subnet, and security group issues.

Use `cinder.*` tools for volume, attachment, backend, and PowerFlex issues.

Use `glance.*` tools for image checks.

Use `quota.*` tools when the user provides a project id and asks about quota.

Use `placement.*` tools for resource provider, inventory, usage, allocation, and capacity questions.
