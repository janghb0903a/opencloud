#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-default}"
RELEASE_NAME="${2:-oss-report-agent}"
SOURCE_DIR="${3:-check}"
TARGET_DIR="${4:-/input/checks}"
APP_NAME_LABEL="${5:-oss-report-agent}"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Source directory not found: ${SOURCE_DIR}" >&2
  exit 1
fi

if ! find "${SOURCE_DIR}" -maxdepth 1 -type f | grep -q .; then
  echo "No check files found in source directory: ${SOURCE_DIR}" >&2
  exit 1
fi

POD_NAME="$(kubectl -n "${NAMESPACE}" get pods \
  -l "app.kubernetes.io/instance=${RELEASE_NAME},app.kubernetes.io/name=${APP_NAME_LABEL}" \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].metadata.name}')"

if [[ -z "${POD_NAME}" ]]; then
  echo "No running report-agent pod found in namespace=${NAMESPACE}, release=${RELEASE_NAME}" >&2
  exit 1
fi

echo "Using target pod: ${POD_NAME}"
kubectl -n "${NAMESPACE}" exec "${POD_NAME}" -- mkdir -p "${TARGET_DIR}"

while IFS= read -r file; do
  kubectl -n "${NAMESPACE}" cp "${file}" "${POD_NAME}:${TARGET_DIR}/$(basename "${file}")"
done < <(find "${SOURCE_DIR}" -maxdepth 1 -type f)

kubectl -n "${NAMESPACE}" exec "${POD_NAME}" -- ls -l "${TARGET_DIR}"
echo "Copied check files to ${POD_NAME}:${TARGET_DIR}."
