# Claude Usage Guidance

This MCP server is the source of truth for Kubernetes cluster diagnostics only.

## Target Routing

Use this MCP server when the user mentions one of these Kubernetes `cluster_id` values:

- `mgmt`
- `test-app-01`
- `dev-app-01`
- `test-genai-01`
- `test-genai-02`
- `test-mgmt-01`
- `test-mgmt-02`

If the user mentions only `test-genai-01`, `test-app-01`, `dev-app-01`, or another cluster id above, treat it as a Kubernetes cluster id and call the Kubernetes MCP tools. Do not ask whether it is OpenStack.

Use `ocp-openstack-diagnostic-mcp` only when the user asks about OpenStack cloud, Nova, Neutron, Cinder, Glance, Keystone, Placement, VM, hypervisor, flavor, quota, or volume diagnostics.

## Answering Rules

Never invent infrastructure names. Node names, pod names, namespaces, IPs, endpoints, VM names, hypervisor names, and health states must come from MCP tool results.

Call the relevant MCP tool before answering Kubernetes/OpenStack infrastructure questions. Do not provide example names such as `node-01`, `node-02`, `compute-01`, or `pod-abc` before a tool result is available.

After calling a tool, wait for the tool result before giving the final answer. Do not say that a tool is missing, failed, or still waiting unless the returned MCP payload explicitly contains an `error` object.

If a tool returns a normal `result` with an empty list, say that the query succeeded but returned no matching data. Do not call that a tool failure.

If a tool returns an `error` object, say `MCP 조회 실패` and summarize the error code/message only.

## Kubernetes Tool Selection

Use `k8s.get_nodes` for Kubernetes node lists.

Use `diagnose.cluster` for overall cluster health.

Use `diagnose.node` only after a real node name is known from `k8s.get_nodes`.

Use `k8s.get_pods` before diagnosing pods if the pod name is not known.

Use `diagnose.pod` only after namespace and pod name are known from tool results or the user.

Use `openstack_helm.*` tools only for `cluster_id=test-mgmt-02`.

## Metrics Guidance

Use `metrics.query_prometheus` for explicit PromQL from the user.

`count(node_cpu_seconds_total)` checks whether the metric exists; it is not CPU usage.

For node CPU usage percentage, prefer:

```promql
100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))
```

For node memory usage percentage, prefer:

```promql
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))
```

For CPU request allocation percentage, prefer:

```promql
100 * sum by (node) (kube_pod_container_resource_requests{resource="cpu"}) / sum by (node) (kube_node_status_allocatable{resource="cpu"})
```
