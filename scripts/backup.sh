#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
backup_dir="${BACKUP_DIR:-.backups}"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="$backup_dir/releaseops-$stamp.dump"
temporary="$backup.tmp.$$"
if [[ -e "$backup" ]]; then
  echo "Refusing to overwrite existing backup: $backup" >&2
  exit 1
fi
umask 077
trap 'rm -f "$temporary"' EXIT
docker compose exec -T db sh -c 'pg_dump --format=custom --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' > "$temporary"
if [[ ! -s "$temporary" ]]; then
  echo 'Backup is empty; inspect database health and logs.' >&2
  exit 1
fi
docker compose exec -T db pg_restore --list < "$temporary" >/dev/null
mv -- "$temporary" "$backup"
echo "Created and structurally verified $backup"
