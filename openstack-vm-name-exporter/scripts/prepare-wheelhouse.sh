#!/usr/bin/env bash
set -euo pipefail

# Build Linux-compatible wheelhouse using the same Python base image.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

rm -rf wheels
mkdir -p wheels

docker run --rm \
  -v "$ROOT_DIR":/work \
  -w /work \
  python:3.11-slim \
  sh -c "pip install --no-cache-dir -U pip && pip download --only-binary=:all: -r requirements.txt -d wheels"

echo "Wheelhouse created: $ROOT_DIR/wheels"
