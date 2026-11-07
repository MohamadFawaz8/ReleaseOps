#!/usr/bin/env bash
set -euo pipefail

cluster_name=releaseops
context="kind-$cluster_name"
if ! command -v kind >/dev/null; then
  echo "kind is not installed." >&2
  exit 1
fi
if ! kind get clusters | grep -Fxq "$cluster_name"; then
  echo "The '$cluster_name' kind cluster does not exist; nothing to delete."
  exit 0
fi
if [[ "$(kubectl config current-context)" != "$context" ]]; then
  echo "Current kubectl context is not '$context'; refusing cluster deletion." >&2
  exit 1
fi
echo "Deleting only the explicitly named local kind cluster: $cluster_name"
kind delete cluster --name "$cluster_name"
