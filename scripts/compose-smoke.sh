#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
project="releaseops-ci-${CI_RUN_ID:-local}-$$"
secret_dir="$(mktemp -d "${TMPDIR:-/tmp}/releaseops-ci.XXXXXXXX")"
env_file="$secret_dir/compose.env"
python3 - "$env_file" "$project" <<'PY'
import secrets
import sys
from pathlib import Path

path, project = sys.argv[1:]
port = 18000 + (int.from_bytes(secrets.token_bytes(2), "big") % 10000)
Path(path).write_text(
    f"POSTGRES_DB=releaseops\nPOSTGRES_USER=releaseops\n"
    f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\nAPP_VERSION=0.1.0\n"
    f"WORKER_POLL_SECONDS=1\nWORKER_PROCESS_SECONDS=1\n"
    f"GRAFANA_ADMIN_USER=admin\nGRAFANA_ADMIN_PASSWORD={secrets.token_urlsafe(32)}\n"
    f"WEB_BIND_PORT={port}\nCI_PROJECT={project}\n"
)
PY
cleanup() {
  docker compose --env-file "$env_file" -p "$project" down --volumes --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$secret_dir"
}
trap cleanup EXIT INT TERM
docker compose --env-file "$env_file" -p "$project" up --build --detach --wait
docker compose --env-file "$env_file" -p "$project" exec -T -e BASE_URL=http://web:8080 api python - < scripts/smoke.py

# Generated values are URL-safe shell assignments. Export them so shared
# operational scripts address this disposable project, never the main deployment.
set -a
source "$env_file"
set +a
export COMPOSE_PROJECT_NAME="$project"
export BACKUP_DIR="$secret_dir/backups"
bash scripts/recovery-check.sh
bash scripts/backup.sh
backups=("$BACKUP_DIR"/*.dump)
if [[ ${#backups[@]} != 1 || ! -f "${backups[0]}" ]]; then
  echo 'Expected exactly one disposable backup.' >&2
  exit 1
fi
bash scripts/restore.sh --backup "${backups[0]}" --target releaseops_restore_check
bash scripts/restore.sh --backup "${backups[0]}" --target releaseops_restore_check --apply
source_count="$(docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM orders"')"
restored_count="$(docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d releaseops_restore_check -Atc "SELECT count(*) FROM orders"')"
[[ "$source_count" == "$restored_count" && "$source_count" -ge 2 ]]
echo "PASS: separate-database restore preserves $restored_count order records."
