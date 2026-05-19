# opencloud

OpenCloud is a collection of infrastructure operations, diagnostics, migration, monitoring, and automation tools. Each directory is designed to be usable on its own and usually includes its own README, container build files, Helm chart, or deployment scripts.

## Projects

| Directory | What It Does | Runtime / Deploy |
| --- | --- | --- |
| [`ansible-monthly-check/`](./ansible-monthly-check/README.md) | Runs monthly OpenStack and Kubernetes checks from a bastion host and writes one report file per host. | Ansible |
| [`grafana-ai-assistant/`](./grafana-ai-assistant/README.md) | Generates Grafana dashboard JSON from natural-language requests using Prometheus metadata and an AI backend. | Next.js, FastAPI, Helm |
| [`helm-ai-agent/`](./helm-ai-agent/README.md) | Converts Kubernetes YAML manifests into Helm chart structure with AI assistance. | FastAPI, Nginx, Docker Compose |
| [`nexus-image-pusher/`](./nexus-image-pusher/README.md) | Re-tags images from `docker save` archives and pushes them to a private Nexus registry. | FastAPI, Docker, Helm |
| [`ocp-k8s-diagnostic-mcp/`](./ocp-k8s-diagnostic-mcp/README.md) | Provides a read-only MCP server for Kubernetes/OCP diagnostics. | Python, MCP, Helm |
| [`ocp-openstack-diagnostic-mcp/`](./ocp-openstack-diagnostic-mcp/README.md) | Provides a read-only MCP server for OpenStack diagnostics and incident investigation. | Python, MCP, Helm |
| [`openstack-migration-web/`](./openstack-migration-web/README.md) | Provides a web UI for planning OpenStack volume and VM migration command sequences. | Node.js, Docker Compose |
| [`openstack-vm-name-exporter/`](./openstack-vm-name-exporter/README.md) | Exposes OpenStack VM UUID/name mappings as Prometheus metrics. | Python, Docker, Helm |
| [`openstack-vm-recovery-auto/`](./openstack-vm-recovery-auto/README.md) | Discovers OpenStack VMs automatically and applies ping-based recovery policy. | Python, CronJob, Helm |
| [`oss-report-agent/`](./oss-report-agent/README.md) | Reads infrastructure check outputs and generates Markdown reports with an LLM backend. | Python, Docker, Helm |
| [`vm-ip-guide-web/`](./vm-ip-guide-web/README.md) | Serves a static VM IP and hostname guide with runtime URL injection. | Nginx, Docker, Helm |

## Project Groups

### Diagnostics

- `ocp-k8s-diagnostic-mcp/`
- `ocp-openstack-diagnostic-mcp/`
- `openstack-vm-name-exporter/`

### Automation And Recovery

- `ansible-monthly-check/`
- `openstack-vm-recovery-auto/`
- `nexus-image-pusher/`

### AI-Assisted Tools

- `grafana-ai-assistant/`
- `helm-ai-agent/`
- `oss-report-agent/`

### Web Utilities

- `openstack-migration-web/`
- `vm-ip-guide-web/`

## Common Workflow

1. Choose the project directory that matches the task.
2. Read that directory's `README.md` for build, run, and deployment instructions.
3. Use `helm/` or `deploy/helm/` when deploying to Kubernetes.
4. For air-gapped environments, prepare wheelhouses, image tar files, or offline package artifacts before moving the project inside.

## Repository Guidelines

- Keep real credentials, kubeconfigs, OpenStack `clouds.yaml`, Prometheus tokens, and AI API keys out of Git.
- Use placeholders in examples and inject real values through Kubernetes Secrets, environment variables, or external secret managers.
- Keep each tool self-contained: source code, README, Dockerfile, Helm chart, and helper scripts should live under the tool directory.
- Prefer environment-specific values files over editing chart defaults directly.
