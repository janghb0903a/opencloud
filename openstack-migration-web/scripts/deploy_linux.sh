#!/usr/bin/env bash
set -euo pipefail

APP_NAME="openstack-migration-web"
PORT="${PORT:-8080}"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker is not installed"
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  docker compose up -d --build
else
  echo "[ERROR] docker compose plugin is required"
  exit 1
fi

echo "[INFO] ${APP_NAME} started on port ${PORT}"

echo "[INFO] health check:"
curl -fsS "http://127.0.0.1:${PORT}/healthz" && echo