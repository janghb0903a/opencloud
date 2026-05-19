# ocp-k8s-diagnostic-mcp

Read-only Kubernetes diagnostic MCP server.

This directory is trimmed for image build and Helm-based deployment.

## Remaining Files

- `Dockerfile`: container image build
- `src/`: MCP server source code
- `config/`: config examples copied into the image
- `runbooks/`: bundled diagnostic runbooks
- `helm/ocp-k8s-diagnostic-mcp/`: Helm chart
- `pyproject.toml`: Python package metadata
- `.dockerignore`: Docker build context cleanup

## Build Image

```bash
cd ocp-k8s-diagnostic-mcp

docker build -t ocp-k8s-diagnostic-mcp:dev .
docker run --rm ocp-k8s-diagnostic-mcp:dev --help
```

## Save For Internal Import

```bash
docker save ocp-k8s-diagnostic-mcp:dev -o ocp-k8s-diagnostic-mcp-dev.tar
tar czf ocp-k8s-diagnostic-mcp-helm.tgz helm/ocp-k8s-diagnostic-mcp
```

Move these files into the internal network:

```text
ocp-k8s-diagnostic-mcp-dev.tar
ocp-k8s-diagnostic-mcp-helm.tgz
```

## Load And Push Internally

```bash
docker load -i ocp-k8s-diagnostic-mcp-dev.tar
docker tag ocp-k8s-diagnostic-mcp:dev internal-registry.example.local/diagnostics/ocp-k8s-diagnostic-mcp:dev
docker push internal-registry.example.local/diagnostics/ocp-k8s-diagnostic-mcp:dev
```

## Helm Deploy

Create `values-internal.yaml`:

```yaml
image:
  repository: internal-registry.example.local/diagnostics/ocp-k8s-diagnostic-mcp
  tag: dev

transport: http

http:
  host: 0.0.0.0
  port: 8080
  path: /mcp

service:
  enabled: true
  type: ClusterIP
  port: 8080

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: ocp-k8s-diagnostic-mcp.example.internal
      paths:
        - path: /mcp
          pathType: Prefix
  tls:
    - secretName: ocp-k8s-diagnostic-mcp-tls
      hosts:
        - ocp-k8s-diagnostic-mcp.example.internal

config:
  clustersYaml: |
    clusters:
      - cluster_id: mgmt
        kubeconfig_ref: file:/kubeconfigs/mgmt
        prometheus_ref: mgmt
        rancher_cluster_name: mgmt
  prometheusYaml: |
    prometheus:
      mgmt:
        url: http://prometheus.cattle-monitoring-system.svc:9090
  rancherYaml: |
    rancher:
      enabled: false
      url: https://rancher.example.internal
      verify_tls: true
      timeout_seconds: 10
      user_token_ref: env:RANCHER_BEARER_TOKEN

kubeconfigSecret:
  enabled: true
  existingSecret: ocp-k8s-diagnostic-kubeconfigs
  mountPath: /kubeconfigs
```

Create kubeconfig Secret:

```bash
kubectl create namespace ocp-diagnostics

kubectl -n ocp-diagnostics create secret generic ocp-k8s-diagnostic-kubeconfigs \
  --from-file=mgmt=./kubeconfigs/mgmt
```

Install:

```bash
tar xzf ocp-k8s-diagnostic-mcp-helm.tgz

helm upgrade --install ocp-k8s-diagnostic-mcp ./helm/ocp-k8s-diagnostic-mcp \
  --namespace ocp-diagnostics \
  --create-namespace \
  -f values-internal.yaml
```

Claude Code registration after Ingress/Route is ready:

```bash
claude mcp add --transport http ocp-k8s-diagnostic-mcp \
  --scope user \
  https://ocp-k8s-diagnostic-mcp.example.internal/mcp
```

With Rancher token authorization:

```bash
claude mcp add --transport http ocp-k8s-diagnostic-mcp \
  --scope user \
  https://ocp-k8s-diagnostic-mcp.example.internal/mcp \
  --header "Authorization: Bearer token-xxxxx:yyyyyyyyy"
```

## Rancher Token Authorization

For local stdio tests, Rancher authorization can be enabled with a user API Key bearer value:

```text
Bearer value = Access Key:Secret Key
example      = token-xxxxx:yyyyyyyyy
```

Set it as an environment variable. Do not pass it as a tool argument.

```bash
docker run --rm -i \
  -e OCP_DIAG_CONFIG_DIR=/app/config \
  -e RANCHER_BEARER_TOKEN='token-xxxxx:yyyyyyyyy' \
  -v "$PWD/local-test/config:/app/config:ro,Z" \
  -v "$PWD/local-test/kubeconfigs:/kubeconfigs:ro,Z" \
  ocp-k8s-diagnostic-mcp:dev
```

## Transport

The image supports both transports:

```bash
ocp-k8s-diagnostic-mcp --transport stdio
ocp-k8s-diagnostic-mcp --transport http --host 0.0.0.0 --port 8080 --path /mcp
```

The Helm chart defaults to HTTP transport for Kubernetes deployment.
