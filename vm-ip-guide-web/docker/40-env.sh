#!/bin/sh
set -eu

cat >/usr/share/nginx/html/config.js <<EOF
window.APP_CONFIG = {
  CLOUD_PORTAL_URL: "${CLOUD_PORTAL_URL:-#}",
  CLOUD_PORTAL_URL_DEV: "${CLOUD_PORTAL_URL_DEV:-}",
  CLOUD_PORTAL_URL_PROD: "${CLOUD_PORTAL_URL_PROD:-}"
};
EOF
