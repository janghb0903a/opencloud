# CrashLoopBackOff

Use `diagnose.pod` first, then inspect `k8s.get_pod_events` and bounded `k8s.get_pod_logs`.

Common checks:

- Container exit reason and restart count
- Recent warning events
- Application errors in recent logs
- Missing configuration visible from pod status or events

This MCP server does not restart, patch, exec, or debug the pod.

