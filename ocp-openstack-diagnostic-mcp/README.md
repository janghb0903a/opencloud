# ocp-openstack-diagnostic-mcp

Read-only OpenStack diagnostic MCP server for Claude Code.

Target cloud:

```text
cloud_id: test-mgmt-02
region_name: RegionOne
interface: internal
storage backend: PowerFlex
linked Kubernetes MCP: ocp-k8s-diagnostic-mcp / cluster_id=test-mgmt-02 / namespace=openstack-helm
```

## Build Image

```bash
cd ocp-openstack-diagnostic-mcp

docker build -t ocp-openstack-diagnostic-mcp:dev .
docker run --rm ocp-openstack-diagnostic-mcp:dev --help
```

## Save For Internal Import

```bash
docker save ocp-openstack-diagnostic-mcp:dev -o ocp-openstack-diagnostic-mcp-dev.tar
tar czf ocp-openstack-diagnostic-mcp-helm.tgz helm/ocp-openstack-diagnostic-mcp
```

## Internal Load And Push

```bash
docker load -i ocp-openstack-diagnostic-mcp-dev.tar
docker tag ocp-openstack-diagnostic-mcp:dev internal-registry.example.local/diagnostics/ocp-openstack-diagnostic-mcp:dev
docker push internal-registry.example.local/diagnostics/ocp-openstack-diagnostic-mcp:dev
```

## Helm Deploy

Create `values-internal.yaml`:

```yaml
image:
  repository: internal-registry.example.local/diagnostics/ocp-openstack-diagnostic-mcp
  tag: dev

transport: http

config:
  cloudsYaml: |
    clouds:
      - cloud_id: test-mgmt-02
        cloud: test-mgmt-02
        region_name: RegionOne
        interface: internal
        clouds_yaml_ref: file:/openstack/clouds.yaml
        storage_backend: PowerFlex
        ceph: false
        linked_k8s:
          mcp_server: ocp-k8s-diagnostic-mcp
          cluster_id: test-mgmt-02
          namespace: openstack-helm

cloudsSecret:
  enabled: true
  existingSecret: ocp-openstack-clouds
  mountPath: /openstack

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: ocp-openstack-diagnostic-mcp.example.internal
      paths:
        - path: /mcp
          pathType: Prefix
```

Create the OpenStack credentials secret:

```bash
kubectl create namespace ocp-diagnostics

kubectl -n ocp-diagnostics create secret generic ocp-openstack-clouds \
  --from-file=clouds.yaml=./clouds.yaml
```

Install:

```bash
tar xzf ocp-openstack-diagnostic-mcp-helm.tgz

helm upgrade --install ocp-openstack-diagnostic-mcp ./helm/ocp-openstack-diagnostic-mcp \
  --namespace ocp-diagnostics \
  --create-namespace \
  -f values-internal.yaml
```

Register in Claude Code:

```bash
claude mcp add --transport http ocp-openstack-diagnostic-mcp \
  --scope user \
  https://ocp-openstack-diagnostic-mcp.example.internal/mcp
```

## Local stdio Test

```bash
ocp-openstack-diagnostic-mcp --transport stdio
```

## Security

- No mutating OpenStack APIs are implemented.
- OpenStack CLI fallback is allowlisted only and never raw passthrough.
- Secrets, tokens, passwords, `Authorization`, `X-Auth-Token`, and raw `clouds.yaml` are redacted.
- K8s MCP integration is recommendation-only via `linked_k8s` and `recommended_next_tools`.

