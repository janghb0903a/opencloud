# NoValidHost

Use `nova.diagnose_no_valid_host`, then inspect:

- `nova.get_hypervisors`
- `nova.get_services`
- `placement.get_resource_providers`
- `placement.diagnose_capacity`
- linked Kubernetes `k8s.get_pods` for `application=nova`

This MCP server does not resize, migrate, evacuate, or create servers.

