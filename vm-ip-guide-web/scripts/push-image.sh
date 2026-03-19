#!/usr/bin/env bash
set -euo pipefail

IMAGE_REPO="${IMAGE_REPO:?set IMAGE_REPO, e.g. registry.internal/platform/vm-ip-guide-web}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "[tag] vm-ip-guide-web:${IMAGE_TAG} -> ${IMAGE_REPO}:${IMAGE_TAG}"
docker tag "vm-ip-guide-web:${IMAGE_TAG}" "${IMAGE_REPO}:${IMAGE_TAG}"

echo "[push] ${IMAGE_REPO}:${IMAGE_TAG}"
docker push "${IMAGE_REPO}:${IMAGE_TAG}"
echo "[done] image push completed"
