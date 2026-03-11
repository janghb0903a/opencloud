#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-default}"
RELEASE_NAME="${2:-oss-report-agent}"
CHART_PATH="${3:-./helm/oss-report-agent}"
PVC_NAME="${4:-oss-report-agent-check-pvc}"
CHECK_DIR="${5:-./check}"
IMAGE_REPOSITORY="${6:-oss-report-agent}"
IMAGE_TAG="${7:-0.1.0}"
LLM_PROVIDER="${8:-ollama}"
LLM_BASE_URL="${9:-http://ollama-api.default.svc.cluster.local:11434}"
LLM_MODEL="${10:-llama3.1:8b}"

echo "[1/3] Deploying Helm release..."
HELM_ARGS=(
  --namespace "${NAMESPACE}"
  --create-namespace
  --set image.repository="${IMAGE_REPOSITORY}"
  --set image.tag="${IMAGE_TAG}"
  --set checkStorage.mode=pvc
  --set checkStorage.pvc.name="${PVC_NAME}"
  --set env.LLM_PROVIDER="${LLM_PROVIDER}"
)

if [[ "${LLM_PROVIDER}" == "openai" ]]; then
  HELM_ARGS+=(--set env.OPENAI_BASE_URL="${LLM_BASE_URL}")
  HELM_ARGS+=(--set env.OPENAI_MODEL="${LLM_MODEL}")
else
  HELM_ARGS+=(--set env.OLLAMA_BASE_URL="${LLM_BASE_URL}")
  HELM_ARGS+=(--set env.OLLAMA_MODEL="${LLM_MODEL}")
fi

helm upgrade --install "${RELEASE_NAME}" "${CHART_PATH}" \
  "${HELM_ARGS[@]}"

echo "[2/3] Waiting for PVC binding..."
kubectl -n "${NAMESPACE}" wait --for=jsonpath='{.status.phase}'=Bound pvc/"${PVC_NAME}" --timeout=180s

echo "[3/3] Copying check files into PVC..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/copy-check-files-to-pvc.sh" "${NAMESPACE}" "${RELEASE_NAME}" "${CHECK_DIR}" "/input/checks" "oss-report-agent"

echo "Done. Deployment and check file sync completed."
