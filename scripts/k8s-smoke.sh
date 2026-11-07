#!/usr/bin/env bash
set -euo pipefail
context=kind-releaseops
namespace=releaseops
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ "$(kubectl config current-context)" != "$context" ]]; then
  echo "Expected current context '$context'; refusing port forwarding." >&2
  exit 1
fi
kubectl --context "$context" -n "$namespace" exec -i deployment/api -- env BASE_URL=http://web:8080 /app/.venv/bin/python - < scripts/smoke.py
echo 'Kubernetes order lifecycle passed. Forwarding localhost:8082; leave this terminal open for browser access (Ctrl+C stops forwarding).'
kubectl --context "$context" -n "$namespace" port-forward --address 127.0.0.1 service/web 8082:8080
