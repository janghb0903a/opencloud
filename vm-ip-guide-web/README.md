# vm-ip-guide-web

Static web app + container + Helm chart for VM IP/Hostname guide.

## Directory

- `site/`: web page source
- `Dockerfile`: nginx image build
- `docker/40-env.sh`: runtime env injection to `config.js`
- `scripts/build-image.sh`: Linux image build script
- `scripts/test-local-docker.sh`: Linux local docker run/test script
- `scripts/push-image.sh`: image push script
- `scripts/deploy-helm.sh`: Helm deploy script
- `helm/vm-ip-guide-web`: Helm chart for Kubernetes

## Prerequisites (Linux)

- `docker`
- `curl`
- `kubectl`
- `helm`

## 1) Build image

```bash
cd vm-ip-guide-web
chmod +x scripts/*.sh
./scripts/build-image.sh
```

Optional:

```bash
IMAGE_NAME=vm-ip-guide-web IMAGE_TAG=v1 ./scripts/build-image.sh
```

## 2) Run local docker test

```bash
./scripts/test-local-docker.sh
```

Optional:

```bash
IMAGE_NAME=vm-ip-guide-web IMAGE_TAG=v1 HOST_PORT=18080 CLOUD_PORTAL_URL="https://cloud-portal.internal" ./scripts/test-local-docker.sh
```

환경별 포탈 URL 사용:

```bash
CLOUD_PORTAL_URL_DEV="https://dev-portal.internal" \
CLOUD_PORTAL_URL_PROD="https://prod-portal.internal" \
KEEP_CONTAINER_ON_SUCCESS=true \
./scripts/test-local-docker.sh
```

Keep container for browser/manual check:

```bash
KEEP_CONTAINER_ON_SUCCESS=true ./scripts/test-local-docker.sh
```

## 3) Push image to internal registry

```bash
IMAGE_REPO=registry.internal/platform/vm-ip-guide-web IMAGE_TAG=v1 ./scripts/push-image.sh
```

## 4) Deploy to Kubernetes with Helm

### 4.1 Quick deploy by script

```bash
RELEASE_NAME=vm-ip-guide-web \
NAMESPACE=vm-ip-guide \
IMAGE_REPOSITORY=registry.internal/platform/vm-ip-guide-web \
IMAGE_TAG=v1 \
CLOUD_PORTAL_URL_DEV="https://dev-cloud-portal.internal" \
CLOUD_PORTAL_URL_PROD="https://prod-cloud-portal.internal" \
INGRESS_ENABLED=true \
INGRESS_CLASS_NAME=nginx \
INGRESS_HOST=vm-ip-guide.internal \
./scripts/deploy-helm.sh
```

### 4.2 Manual Helm command

```bash
helm upgrade --install vm-ip-guide-web ./helm/vm-ip-guide-web \
  -n vm-ip-guide --create-namespace \
  --set image.repository=registry.internal/platform/vm-ip-guide-web \
  --set image.tag=v1 \
  --set cloudPortalUrlDev="https://dev-cloud-portal.internal" \
  --set cloudPortalUrlProd="https://prod-cloud-portal.internal" \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=vm-ip-guide.internal
```

## 5) Verify

```bash
kubectl -n vm-ip-guide get pods,svc,ingress
kubectl -n vm-ip-guide logs deploy/vm-ip-guide-web-vm-ip-guide-web --tail=100
```
