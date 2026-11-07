#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ -e .env ]]; then
  echo ".env already exists; leaving it unchanged." >&2
  exit 1
fi
umask 077
python3 - <<'PY'
from pathlib import Path
import secrets

template = Path('.env.example').read_text()
template = template.replace('replace-with-generated-local-secret', secrets.token_urlsafe(32), 1)
template = template.replace('replace-with-generated-local-secret', secrets.token_urlsafe(32), 1)
Path('.env').write_text(template)
PY
chmod 600 .env
echo "Created .env with local random credentials (values are not displayed)."
