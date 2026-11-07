#!/usr/bin/env bash
set -euo pipefail

context=kind-releaseops
namespace=releaseops
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ "$(kubectl config current-context)" != "$context" ]]; then
  echo "Select '$context' with kubectl config use-context before setting credentials." >&2
  exit 1
fi
kubectl --context "$context" get namespace "$namespace" >/dev/null || {
  echo "Terraform must create namespace '$namespace' before this step." >&2
  exit 1
}
if kubectl --context "$context" -n "$namespace" get secret releaseops-db >/dev/null 2>&1; then
  echo 'Secret releaseops-db already exists; leaving credentials unchanged.'
  exit 0
fi
mkdir -p .secrets/kubernetes
chmod 700 .secrets .secrets/kubernetes
umask 077
python3 - <<'PY'
import secrets
from pathlib import Path

directory = Path('.secrets/kubernetes')
password_file = directory / 'password'
if not password_file.exists():
    password_file.write_text(secrets.token_urlsafe(32))
password = password_file.read_text().strip()
if len(password) < 24 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in password):
    raise SystemExit('Existing local password has an invalid format; no secret was changed.')
(directory / 'database-url').write_text(f'postgresql+psycopg://releaseops:{password}@db:5432/releaseops')
PY
kubectl --context "$context" -n "$namespace" create secret generic releaseops-db \
  --from-file=password=.secrets/kubernetes/password \
  --from-file=database-url=.secrets/kubernetes/database-url \
  --dry-run=client -o yaml | kubectl --context "$context" apply -f -
echo 'Created namespace-local secret releaseops-db from ignored local files. Existing PVC passwords are never rotated automatically.'
