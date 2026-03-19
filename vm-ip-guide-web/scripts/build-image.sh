#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-vm-ip-guide-web}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "[build] ${IMAGE_NAME}:${IMAGE_TAG}"
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .
echo "[done] image build completed"
