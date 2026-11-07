#!/usr/bin/env bash
set -euo pipefail

context=kind-releaseops
namespace=releaseops
require_context() {
  local current
  current="$(kubectl config current-context)"
  if [[ "$current" != "$context" ]]; then
    echo "Expected current context '$context'; got '$current'. Refusing Kubernetes changes." >&2
    exit 1
  fi
  kind get clusters | grep -Fxq releaseops || {
    echo "The local kind cluster 'releaseops' is not running." >&2
    exit 1
  }
  kubectl --context "$context" get namespace "$namespace" >/dev/null || {
    echo "Create the Terraform namespace before applying workloads." >&2
    exit 1
  }
}

require_context
kubectl --context "$context" -n "$namespace" get secret releaseops-db >/dev/null || {
  echo "Run scripts/k8s-secrets.sh first to create the local database secret." >&2
  exit 1
}
kind load docker-image --name releaseops releaseops-api:0.1.0 releaseops-web:0.1.0
kubectl --context "$context" apply -k infra/k8s
kubectl --context "$context" -n "$namespace" rollout status statefulset/db --timeout=180s
kubectl --context "$context" -n "$namespace" rollout status deployment/redis --timeout=120s

# A completed Job is immutable; replace just this named migration Job per deployment.
kubectl --context "$context" -n "$namespace" delete job releaseops-migrate --ignore-not-found=true --wait=true
kubectl --context "$context" apply -f infra/k8s/migration-job.yaml
kubectl --context "$context" -n "$namespace" wait --for=condition=complete job/releaseops-migrate --timeout=180s || {
  kubectl --context "$context" -n "$namespace" logs job/releaseops-migrate || true
  kubectl --context "$context" -n "$namespace" describe job/releaseops-migrate || true
  exit 1
}
kubectl --context "$context" -n "$namespace" rollout status deployment/api --timeout=180s
kubectl --context "$context" -n "$namespace" rollout status deployment/worker --timeout=180s
kubectl --context "$context" -n "$namespace" rollout status deployment/web --timeout=120s
kubectl --context "$context" -n "$namespace" get pods,services,pvc
