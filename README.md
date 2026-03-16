# opencloud

This repository collects OpenCloud operations and automation tools.

## Directory Overview

### `ansible-monthly-check/`
- Monthly infrastructure checks for OpenStack and Kubernetes using Ansible
- Runs from a bastion host and writes one output file per host (`<hostname>_check`)
- Check outputs can be used as input for `oss-report-agent`

### `nexus-image-pusher/`
- Web app to retag and push images from `docker save` archives (`.tar`) to private Nexus registries
- Applies metacode-based path rewrite rules (for example: `<registry>/<metacode>/<image>:<tag>`)
- Supports container runtime and Helm deployment

### `oss-report-agent/`
- Python report agent that reads `*_check` files and generates Markdown reports
- Supports Ollama and OpenAI-compatible (vLLM) backends
- Supports Docker/Helm deployment and PVC-based input paths

## Quick Links

- [ansible-monthly-check](./ansible-monthly-check/README.md)
- [nexus-image-pusher](./nexus-image-pusher/README.md)
- [oss-report-agent](./oss-report-agent/README.md)
