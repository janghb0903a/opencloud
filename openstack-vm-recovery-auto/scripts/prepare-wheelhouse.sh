#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

rm -rf wheels
mkdir -p wheels

docker run --rm \
  -v "$ROOT_DIR":/work \
  -w /work \
  registry.access.redhat.com/ubi9/python-311:latest \
  sh -c "python -m pip install --no-cache-dir -U pip && python -m pip download --only-binary=:all: -r requirements.txt -d wheels"

if ! find wheels -maxdepth 1 -type f \( -name '*.whl' -o -name '*.tar.gz' -o -name '*.zip' \) | grep -q .; then
  echo "Wheelhouse is empty. Dependency download failed." >&2
  exit 1
fi

if ! find wheels -maxdepth 1 -type f -name 'python_openstackclient-7.2.1-*.whl' | grep -q .; then
  echo "Required wheel missing: python_openstackclient-7.2.1" >&2
  exit 1
fi

echo "Wheelhouse created: $ROOT_DIR/wheels"
