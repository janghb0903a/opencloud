# Node NotReady

Use `diagnose.node`, `k8s.describe_node`, and `k8s.get_pods_by_node`.

Common checks:

- Ready condition reason and message
- DiskPressure, MemoryPressure, PIDPressure
- Recent node warning events
- Impacted pods scheduled on the node

Node kubelet, rke2-agent, containerd, and systemd logs are outside v1.0 scope.

