# openstack-vm-name-exporter

Minimal exporter that reads OpenStack VM `ID(UUID)` and `Name`, then exposes Prometheus metrics on `/metrics`.

## Files

- `server.py`: metric endpoint server
- `requirements.txt`: Python dependency list
- `Dockerfile`: offline image build (installs from local wheel files only)
- `scripts/prepare-wheelhouse.sh`: make wheel files on an internet-connected Linux host
- `scripts/prepare-wheelhouse.ps1`: make wheel files on an internet-connected Windows host

## Metric output

- `openstack_vm_identity{uuid="...",name="..."} 1`
- `openstack_vm_identity_scrape_success`
- `openstack_vm_identity_last_success_timestamp_seconds`

## 1) Internet zone: prepare artifacts for transfer

Run one of the scripts below in this project directory:

Linux:

```bash
./scripts/prepare-wheelhouse.sh
```

Windows PowerShell:

```powershell
.\scripts\prepare-wheelhouse.ps1
```

This creates `./wheels/*.whl`.

Then build and export image tar:

```bash
docker build -t registry.example.com/monitoring/openstack-vm-name-exporter:0.1.0 .
docker save registry.example.com/monitoring/openstack-vm-name-exporter:0.1.0 -o openstack-vm-name-exporter_0.1.0.tar
```

Transfer these into internal network:

- project source (including `wheels/`)
- `openstack-vm-name-exporter_0.1.0.tar` (optional if you build outside and only import inside)

## 2) Internal zone: offline image build or load

Option A: Build inside internal network (no internet needed):

```bash
docker build -t registry.example.com/monitoring/openstack-vm-name-exporter:0.1.0 .
```

Option B: Load prebuilt tar:

```bash
docker load -i openstack-vm-name-exporter_0.1.0.tar
```

Push to internal registry if needed:

```bash
docker push registry.example.com/monitoring/openstack-vm-name-exporter:0.1.0
```

## 3) Runtime requirement

Before deploying to Kubernetes, confirm this command works with the service account/credentials:

```bash
openstack server list --all-projects -f json -c ID -c Name
```

If this fails, exporter will not produce mapping data.

## 4) Local run example

```bash
docker run --rm -p 9189:9189 \
  -e OS_AUTH_URL='https://keystone.example.com:5000/v3' \
  -e OS_IDENTITY_API_VERSION='3' \
  -e OS_AUTH_TYPE='v3password' \
  -e OS_USERNAME='monitoring' \
  -e OS_PASSWORD='********' \
  -e OS_PROJECT_NAME='admin' \
  -e OS_USER_DOMAIN_NAME='Default' \
  -e OS_PROJECT_DOMAIN_NAME='Default' \
  -e POLL_INTERVAL='60' \
  registry.example.com/monitoring/openstack-vm-name-exporter:0.1.0
```

Check:

```bash
curl -s http://127.0.0.1:9189/metrics | head
```

## 5) Included Grafana dashboard JSON

This repository includes the VM name mapped dashboard JSON:

- `dashboards/libvirtd_osh_compatible_dashboard_name_mapped.json`

Import this file in Grafana:

1. Dashboards -> Import
2. Upload JSON file above
3. Map datasource variables:
   - `DS_VICTORIAMETRICS`
   - `DS_VM-SELECT-HAPROXY`

## 6) Kubernetes deployment with Helm chart

Chart path:

```text
helm/openstack-vm-name-exporter
```

Internal deployment (values file example):

```bash
helm upgrade --install openstack-vm-name-exporter \
  ./helm/openstack-vm-name-exporter \
  -n monitoring --create-namespace \
  -f ./helm/openstack-vm-name-exporter/values-internal.example.yaml
```

If OpenStack auth secret already exists:

```bash
helm upgrade --install openstack-vm-name-exporter \
  ./helm/openstack-vm-name-exporter \
  -n monitoring \
  --set secret.create=false \
  --set secret.existingSecret=openstack-vm-name-exporter-auth
```

## 7) Prometheus scrape job: what to add

If you use Prometheus Operator, prefer `ServiceMonitor`:

```bash
helm upgrade --install openstack-vm-name-exporter \
  ./helm/openstack-vm-name-exporter \
  -n monitoring \
  --set serviceMonitor.enabled=true
```

If you use static scrape configs (Prometheus/vmagent), add one job manually:

```yaml
- job_name: openstack-vm-name-exporter
  scrape_interval: 60s
  metrics_path: /metrics
  static_configs:
    - targets:
        - openstack-vm-name-exporter.monitoring.svc:9189
```

Verification query after reload:

```promql
openstack_vm_identity
```

## 8) Privacy note

This repository version uses generic placeholders only (for example `registry.example.com`, `keystone.example.com`, `monitoring`, `change-me`) and does not include personal credentials.
