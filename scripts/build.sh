#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
tag="${1:-${APP_VERSION:-0.1.0}}"
docker build --target runtime --tag "releaseops-api:${tag}" .
docker build --file docker/web.Dockerfile --tag "releaseops-web:${tag}" .
