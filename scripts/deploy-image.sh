#!/usr/bin/env bash
# =============================================================================
# Deploy a new container image to K3s on Hostinger VPS.
# Runs ON THE VPS only — never clones or builds application source code.
#
# Usage:
#   /opt/devops-runtime/scripts/deploy-image.sh ghcr.io/user/repo:sha
# =============================================================================
set -euo pipefail

IMAGE="${1:-}"
NAMESPACE="devops-lab"
DEPLOYMENT="devops-app"
CONTAINER="devops-app"
TIMEOUT="${DEPLOY_TIMEOUT:-300s}"

if [[ -z "${IMAGE}" ]]; then
  echo "ERROR: Image argument required." >&2
  echo "Usage: $0 <docker-image:tag>" >&2
  exit 1
fi

kubectl() {
  if command -v k3s >/dev/null 2>&1; then
    k3s kubectl "$@"
  else
    command kubectl "$@"
  fi
}

export KUBECONFIG="${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}"

show_diagnostics() {
  echo ""
  echo "========== Pod status =========="
  kubectl get pods -n "${NAMESPACE}" -o wide || true
  echo ""
  echo "========== Recent events =========="
  kubectl get events -n "${NAMESPACE}" --sort-by='.lastTimestamp' | tail -15 || true
  echo ""
  echo "========== Pod describe =========="
  kubectl describe pods -n "${NAMESPACE}" -l app="${DEPLOYMENT}" | tail -40 || true
  echo ""
  PENDING=$(kubectl get pods -n "${NAMESPACE}" -l app="${DEPLOYMENT}" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
  if [[ -n "${PENDING}" ]]; then
    echo "========== Logs (${PENDING}) =========="
    kubectl logs "${PENDING}" -n "${NAMESPACE}" --tail=30 || true
  fi
}

echo "==> Updating deployment image to: ${IMAGE}"
kubectl set image "deployment/${DEPLOYMENT}" "${CONTAINER}=${IMAGE}" -n "${NAMESPACE}"

echo "==> Waiting for rollout (timeout ${TIMEOUT})..."
if ! kubectl rollout status "deployment/${DEPLOYMENT}" -n "${NAMESPACE}" --timeout="${TIMEOUT}"; then
  echo "ERROR: Rollout did not finish in time."
  show_diagnostics
  exit 1
fi

echo "==> Pods:"
kubectl get pods -n "${NAMESPACE}"

echo "==> Deploy complete."
