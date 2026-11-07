#!/usr/bin/env bash
# Fail on HIGH/CRITICAL image vulnerabilities. No Docker socket is mounted.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
scanner=aquasec/trivy:0.76.2
tag="${APP_VERSION:-0.1.0}"
docker pull "$scanner"
for image in "releaseops-api:$tag" "releaseops-web:$tag"; do
  printf 'Scanning %s with %s\n' "$image" "$scanner"
  # Streaming the image works with a local daemon and Jenkins's remote TLS daemon.
  # Trivy downloads its public vulnerability database; no account or card is needed.
  docker image save "$image" | docker run --rm -i --memory=1g \
    --volume releaseops-trivy-cache:/root/.cache/trivy \
    --entrypoint /bin/sh "$scanner" -c \
    'cat > /tmp/image.tar; exec trivy image --input /tmp/image.tar --scanners vuln --severity HIGH,CRITICAL --exit-code 1 --timeout 10m'
done
