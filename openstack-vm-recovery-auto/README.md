# openstack-vm-recovery-auto

Ping-based OpenStack VM recovery service with:

- 10-minute CronJob checks
- OpenStack `server list` based VM discovery
- IP selection from `ap*` networks first, then `db*` networks
- recovery only from the 3rd consecutive ping failure
- per-VM web policy to decide whether an ACTIVE server should still be soft rebooted after repeated ping failure
- if a VM still meets the same recovery condition after one reboot attempt, it is classified as unresponsive instead of being rebooted repeatedly
- manual suppression for intentionally stopped VMs
- SQLite-backed event history
- lightweight web console for status and suppression control

## Structure

- `app/openstack_vm_recovery.py`: main app
- `Dockerfile`: image build
- `requirements.txt`: Python dependency
- `scripts/prepare-wheelhouse.sh`: Linux wheel download helper
- `scripts/prepare-wheelhouse.ps1`: Windows wheel download helper
- `wheels/`: offline pip package directory
- `helm/openstack-vm-recovery-auto/`: Helm chart

## Discovery

This variant does not require static `targets` in `values.yaml`.

When the web app starts, when the CronJob runs, or when the web `Sync Targets` button is pressed, the app runs:

```bash
openstack server list --long -f json
```

It then picks the ping address in this order:

1. First IP from a network whose name starts with `ap`
2. First IP from a network whose name starts with `db`
3. First IP matching the fallback prefixes in `discovery.fallbackIpPrefixes`

The default discovery values are:

```yaml
discovery:
  enabled: true
  networkNamePrefixes:
    - ap
    - db
  fallbackIpPrefixes:
    - 16.120.
    - 16.120.120.
    - 16.120.121.
  serverListArgs: []
```

If your OpenStack account needs extra list arguments, add them to `serverListArgs`.
For example:

```yaml
discovery:
  serverListArgs:
    - --all-projects
```

## Wheelhouse preparation

On an internet-connected test environment, download Python packages first:

Linux:

```bash
./scripts/prepare-wheelhouse.sh
```

Windows PowerShell:

```powershell
.\scripts\prepare-wheelhouse.ps1
```

This fills `./wheels/`. You can then carry the whole project directory into the internal environment.

The scripts also verify that the wheelhouse is not empty and that
`python_openstackclient-7.2.1` was downloaded successfully.

## Build

```bash
docker build -t registry.example.com/opencloud/openstack-vm-recovery-auto:0.4.0 .
```

The current Docker build installs Python dependencies only from `./wheels/`.
If `./wheels/` contains package files, the build installs from that offline directory.
If `./wheels/` is empty, the build falls back to online `pip install`.

The default image build uses `registry.access.redhat.com/ubi9/python-311:latest` and installs ping tooling with `dnf`.

This is a better fit when your runtime environment is RHEL-compatible.

## Helm

```bash
helm upgrade --install openstack-vm-recovery-auto \
  ./helm/openstack-vm-recovery-auto \
  -n opencloud --create-namespace
```

Ingress example:

```bash
helm upgrade --install openstack-vm-recovery-auto \
  ./helm/openstack-vm-recovery-auto \
  -n opencloud \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=vm-recovery.example.com
```
