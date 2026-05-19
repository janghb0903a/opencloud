# ImagePullBackOff

Use `diagnose.pod` and `k8s.get_pod_events`.

Common checks:

- Image name and tag
- Registry reachability symptoms in events
- Authentication failures described in events
- Namespace image pull secret references, without reading Secret objects

This MCP server does not read Kubernetes Secret resources.

