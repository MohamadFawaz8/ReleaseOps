#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
BASE_URL="${PREVIEW_URL:-http://engine:8080}" python3 scripts/smoke.py
