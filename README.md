# opencloud

This repository collects OpenCloud operations and automation tools.

## Directory Overview

### `ansible-monthly-check/`
- Monthly infrastructure checks for OpenStack and Kubernetes using Ansible
- Runs from a bastion host and writes one output file per host (`<hostname>_check`)
- Check outputs can be used as input for `oss-report-agent`

### `grafana-ai-assistant/`
- AI-assisted Grafana dashboard JSON generation project
- Includes frontend, backend, and deploy assets (Docker/Helm/K8s)

### `grafana-ai-assistant+/`
- Alternate/extended workspace for Grafana AI assistant components
- Contains `frontend/`, `backend/`, `deploy/`, and `docs/`

### `nexus-image-pusher/`
- Web app to retag and push images from `docker save` archives (`.tar`) to private Nexus registries
- Applies metacode-based path rewrite rules (for example: `<registry>/<metacode>/<image>:<tag>`)
- Supports container runtime and Helm deployment

### `openstack-migration-web/`
- Web prototype for OpenStack migration support workflows

### `openstack-vm-name-exporter/`
- Exports OpenStack VM name and related metadata for monitoring/reporting use

### `oss-report-agent/`
- Python report agent that reads `*_check` files and generates Markdown reports
- Supports Ollama and OpenAI-compatible (vLLM) backends
- Supports Docker/Helm deployment and PVC-based input paths

### `vm-ip-guide-web/`
- Web service for VM IP lookup/guide workflows
- Includes Kubernetes deployment manifests

## Quick Links

- [ansible-monthly-check](./ansible-monthly-check/README.md)
- [grafana-ai-assistant](./grafana-ai-assistant/README.md)
- `grafana-ai-assistant+/` (README 없음)
- [nexus-image-pusher](./nexus-image-pusher/README.md)
- [openstack-migration-web](./openstack-migration-web/README.md)
- [openstack-vm-name-exporter](./openstack-vm-name-exporter/README.md)
- [oss-report-agent](./oss-report-agent/README.md)
- [vm-ip-guide-web](./vm-ip-guide-web/README.md)
