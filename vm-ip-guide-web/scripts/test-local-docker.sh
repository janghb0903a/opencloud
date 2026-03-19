#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-vm-ip-guide-web}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CONTAINER_NAME="${CONTAINER_NAME:-vm-ip-guide-web-test}"
HOST_PORT="${HOST_PORT:-18080}"
CLOUD_PORTAL_URL="${CLOUD_PORTAL_URL:-https://cloud-portal.example.internal}"
KEEP_CONTAINER_ON_SUCCESS="${KEEP_CONTAINER_ON_SUCCESS:-false}"
KEEP_CONTAINER_ON_FAIL="${KEEP_CONTAINER_ON_FAIL:-true}"
TMP_HTML="/tmp/vm-ip-guide-web.index.html"

cleanup() {
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}

echo "[run] ${IMAGE_NAME}:${IMAGE_TAG} on http://127.0.0.1:${HOST_PORT}"
cleanup
docker run -d \
  --name "${CONTAINER_NAME}" \
  -p "${HOST_PORT}:80" \
  -e "CLOUD_PORTAL_URL=${CLOUD_PORTAL_URL}" \
  "${IMAGE_NAME}:${IMAGE_TAG}" >/dev/null

echo "[check] waiting for web response"
READY=0
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${HOST_PORT}/" >"${TMP_HTML}" 2>/dev/null; then
    READY=1
    break
  fi
  sleep 1
done

if [[ "${READY}" -ne 1 ]]; then
  echo "[fail] web endpoint is not reachable: http://127.0.0.1:${HOST_PORT}"
  echo "[info] container status:"
  docker ps -a --filter "name=${CONTAINER_NAME}" || true
  echo "[info] container logs:"
  docker logs --tail 50 "${CONTAINER_NAME}" || true
  if [[ "${KEEP_CONTAINER_ON_FAIL}" != "true" ]]; then
    cleanup
  fi
  exit 1
fi

if ! grep -q 'id="step-env"' "${TMP_HTML}"; then
  echo "[fail] expected app content not found (id=\"step-env\")"
  echo "[info] first response lines:"
  head -n 30 "${TMP_HTML}" || true
  echo "[info] container logs:"
  docker logs --tail 50 "${CONTAINER_NAME}" || true
  if [[ "${KEEP_CONTAINER_ON_FAIL}" != "true" ]]; then
    cleanup
  fi
  exit 1
fi

echo "[pass] local docker test passed"
echo "[info] open: http://127.0.0.1:${HOST_PORT}"
echo "[info] container logs:"
docker logs --tail 20 "${CONTAINER_NAME}" || true

if [[ "${KEEP_CONTAINER_ON_SUCCESS}" != "true" ]]; then
  cleanup
else
  echo "[info] container kept for manual test: ${CONTAINER_NAME}"
fi
