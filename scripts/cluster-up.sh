#!/usr/bin/env bash
set -euo pipefail

cluster_name=releaseops
context="kind-$cluster_name"
config="infra/kind/cluster.yaml"

if ! command -v kind >/dev/null || ! command -v kubectl >/dev/null; then
  echo "Install the pinned tools first with scripts/install-platform-tools.sh." >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker engine is unavailable. Start Docker Desktop with Ubuntu WSL integration." >&2
  exit 1
fi

if kind get clusters | grep -Fxq "$cluster_name"; then
  echo "kind cluster '$cluster_name' already exists; leaving it untouched."
else
  kind create cluster --name "$cluster_name" --config "$config" --wait 180s
fi

actual_context="$(kubectl config current-context)"
if [[ "$actual_context" != "$context" ]]; then
  echo "Expected current context '$context'; got '$actual_context'. No workloads changed." >&2
  exit 1
fi
kubectl --context "$context" wait --for=condition=Ready node --all --timeout=180s
kubectl --context "$context" get nodes -o wide
