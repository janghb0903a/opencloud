#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVENTORY="${1:-$BASE_DIR/inventories/prod/hosts.ini}"
PLAYBOOK="$BASE_DIR/playbooks/monthly_check.yml"

ansible-playbook -i "$INVENTORY" "$PLAYBOOK"

