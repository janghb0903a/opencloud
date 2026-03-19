#!/usr/bin/env bash
set -euo pipefail

RELEASE_NAME="${RELEASE_NAME:-vm-ip-guide-web}"
NAMESPACE="${NAMESPACE:-vm-ip-guide}"
CHART_PATH="${CHART_PATH:-./helm/vm-ip-guide-web}"
IMAGE_REPOSITORY="${IMAGE_REPOSITORY:?set IMAGE_REPOSITORY}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CLOUD_PORTAL_URL="${CLOUD_PORTAL_URL:-#}"
CLOUD_PORTAL_URL_DEV="${CLOUD_PORTAL_URL_DEV:-}"
CLOUD_PORTAL_URL_PROD="${CLOUD_PORTAL_URL_PROD:-}"
INGRESS_ENABLED="${INGRESS_ENABLED:-false}"
INGRESS_CLASS_NAME="${INGRESS_CLASS_NAME:-}"
INGRESS_HOST="${INGRESS_HOST:-vm-ip-guide.example.internal}"

if ! kubectl get ns "${NAMESPACE}" >/dev/null 2>&1; then
  kubectl create ns "${NAMESPACE}"
fi

helm upgrade --install "${RELEASE_NAME}" "${CHART_PATH}" \
  --namespace "${NAMESPACE}" \
  --set image.repository="${IMAGE_REPOSITORY}" \
  --set image.tag="${IMAGE_TAG}" \
  --set cloudPortalUrl="${CLOUD_PORTAL_URL}" \
  --set cloudPortalUrlDev="${CLOUD_PORTAL_URL_DEV}" \
  --set cloudPortalUrlProd="${CLOUD_PORTAL_URL_PROD}" \
  --set ingress.enabled="${INGRESS_ENABLED}" \
  --set ingress.className="${INGRESS_CLASS_NAME}" \
  --set ingress.hosts[0].host="${INGRESS_HOST}"

kubectl -n "${NAMESPACE}" rollout status deploy/"${RELEASE_NAME}"-vm-ip-guide-web --timeout=180s
kubectl -n "${NAMESPACE}" get pods,svc,ingress -l app.kubernetes.io/instance="${RELEASE_NAME}"
