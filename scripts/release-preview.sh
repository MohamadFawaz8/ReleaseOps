#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
state_dir=/home/jenkins/preview
env_file="$state_dir/releaseops.env"
mkdir -p "$state_dir"
chmod 700 "$state_dir"
if [[ ! -s "$env_file" ]]; then
  umask 077
  python3 - "$env_file" <<'PY'
import secrets
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    "POSTGRES_DB=releaseops\nPOSTGRES_USER=releaseops\n"
    f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n"
    "APP_VERSION=0.1.0\nWORKER_POLL_SECONDS=1\n"
    "WORKER_PROCESS_SECONDS=1\nWEB_BIND_ADDRESS=0.0.0.0\n"
    "WEB_BIND_PORT=8080\nGRAFANA_ADMIN_USER=admin\n"
    f"GRAFANA_ADMIN_PASSWORD={secrets.token_urlsafe(32)}\n"
)
PY
  chmod 600 "$env_file"
fi
docker compose --env-file "$env_file" -p releaseops-preview up --build --detach --wait
echo 'Preview is available at http://127.0.0.1:8083/. Database and credentials persist in the Jenkins preview volumes.'
