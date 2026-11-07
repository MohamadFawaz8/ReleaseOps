#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
apply=false
backup=''
target=''
while (($#)); do
  case "$1" in
    --apply) apply=true ;;
    --backup) shift; backup="${1:-}" ;;
    --target) shift; target="${1:-}" ;;
    -h|--help)
      echo 'Usage: scripts/restore.sh --backup .backups/file.dump [--target releaseops_restore_name] [--apply]'
      echo 'Without --apply, this validates the dump and prints the new-database restore plan only.'
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
if [[ -z "$backup" || ! -f "$backup" ]]; then
  echo 'Provide an existing dump with --backup PATH.' >&2
  exit 2
fi
if [[ -z "$target" ]]; then
  target="releaseops_restore_$(date -u +%Y%m%d%H%M%S)"
fi
if [[ ! "$target" =~ ^[a-z][a-z0-9_]{0,30}$ ]]; then
  echo 'Target must be a lowercase database name (a-z, 0-9, underscore), maximum 31 characters.' >&2
  exit 2
fi
docker compose exec -T db pg_restore --list < "$backup" >/dev/null
echo "Validated $backup. Target is a new database named $target; existing databases are never replaced."
if [[ "$apply" != true ]]; then
  echo 'Dry run only. Review the target, then repeat with --apply to create and restore into this new database.'
  exit 0
fi
db_user="$(docker compose exec -T db sh -c 'printf %s "$POSTGRES_USER"')"
if ! docker compose exec -T db createdb -U "$db_user" "$target"; then
  echo "Could not create $target. It may already exist; no existing database was modified." >&2
  exit 1
fi
if ! docker compose exec -T db pg_restore --no-owner --role="$db_user" --username="$db_user" --dbname="$target" < "$backup"; then
  echo "Restore failed; the new database '$target' may be partial. No existing database was changed." >&2
  exit 1
fi
count="$(docker compose exec -T db psql -U "$db_user" -d "$target" -Atc 'SELECT count(*) FROM orders')"
echo "Restore completed into new database $target; orders table contains $count rows. The application still uses the original database."
