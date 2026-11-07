#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p .secrets
chmod 700 .secrets
admin_file=.secrets/jenkins-admin-password
if [[ ! -s "$admin_file" ]]; then
  umask 077
  python3 -c 'import secrets; print(secrets.token_urlsafe(32))' > "$admin_file"
  chmod 600 "$admin_file"
fi
export JENKINS_ADMIN_ID=releaseops
export JENKINS_ADMIN_PASSWORD="$(cat "$admin_file")"
if [[ ! -e .env ]]; then bash scripts/local-secrets.sh; fi
echo 'Building and starting the local Jenkins controller, isolated Docker engine, and agent.'
docker compose -f compose.jenkins.yaml up --build -d
echo 'Waiting for Jenkins startup; inspect with: docker compose -f compose.jenkins.yaml logs --tail=80 jenkins agent'
for attempt in $(seq 1 60); do
  if curl --fail --silent http://127.0.0.1:8081/login >/dev/null; then
    echo 'Jenkins is responding at http://127.0.0.1:8081/ (username: releaseops).'
    echo 'Read the generated password with: cat .secrets/jenkins-admin-password'
    exit 0
  fi
  sleep 2
done
echo 'Jenkins did not become ready within 120 seconds. Inspect the logs command printed above.' >&2
exit 1
