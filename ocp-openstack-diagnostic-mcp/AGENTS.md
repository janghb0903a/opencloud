# AGENTS.md

This repository implements a read-only OpenStack diagnostic MCP server.

## Guardrails

- Do not add mutating OpenStack APIs or raw OpenStack CLI passthrough.
- Keep OpenStack CLI fallback allowlisted, `shell=False`, timeout bounded, and redacted.
- Do not expose raw `clouds.yaml`, passwords, tokens, application credential secrets, `Authorization`, or `X-Auth-Token`.
- Do not modify `ocp-k8s-diagnostic-mcp`.
- Keep K8s MCP integration as recommendations only; do not import the K8s MCP code.

## Testing

```bash
pytest
```

