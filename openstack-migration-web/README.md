# OpenStack Migration Web (Prototype)

Card-based UI prototype for validating OpenStack migration steps.
This version is tuned for transfer-and-test on a Linux server.

## Included
- Hostname search and instance/volume selection
- Volume clone command generation (`-rep` suffix)
- `cinder unmanage` step command generation
- PowerFlex `source-id` based re-create command template
- Re-clone and `-rep` cleanup command generation
- Network port input (default 1 + dynamic add)
- VM create command template

## Linux prerequisites
- Docker Engine 24+
- Docker Compose plugin (`docker compose`)

## Transfer to Linux server
From Windows host (example):

```bash
cd /c/Users/24313027/opencloud
scp -r openstack-migration-web <USER>@<LINUX_SERVER_IP>:/opt/
```

On Linux server:

```bash
cd /opt/openstack-migration-web
```

## Run on Linux (recommended)
```bash
chmod +x scripts/deploy_linux.sh
./scripts/deploy_linux.sh
```

Default port is `8080`. To override:

```bash
PORT=18080 ./scripts/deploy_linux.sh
```

## Run on Linux (manual)
```bash
docker compose up -d --build
```

Open in browser:
- `http://<LINUX_SERVER_IP>:8080`

Check status:
```bash
docker compose ps
curl -fsS http://127.0.0.1:8080/healthz
```

Stop:
```bash
docker compose down
```

## source-id lookup strategy (PowerFlex)
To get `<ID>` for `openstack volume create --remote-source source-id=<ID>`:

1. Save metadata before unmanage:
```bash
openstack volume show <rep-volume-id> -f json
```
Store name, size, timestamp, and host.

2. Run unmanage:
```bash
cinder unmanage <rep-volume-name-or-id>
```

3. Query manageable list:
```bash
cinder manageable-list cinder-volume-worker@powerflex#PD-1:SP-1
```
Find source-id candidates in `reference` and match with saved metadata.

4. Create volume on new OpenStack:
```bash
openstack volume create --remote-source source-id=<SOURCE_ID> --host cinder-volume-worker@powerflex#PD-1:SP-1 --type powerflex <volume-name>-rep
```

## Note
- Current version focuses on command planning/visualization.
- Real execution can be added by wiring OpenRC/auth/permissions/error handling in backend API.