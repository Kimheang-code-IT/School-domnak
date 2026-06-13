#!/usr/bin/env bash
# =============================================================================
# Deploy frontend + backend images to K3s on Hostinger VPS.
# Runs ON THE VPS only — never clones or builds application source code.
#
# Usage:
#   deploy-image.sh <frontend-image> [backend-image]
#
# Examples:
#   deploy-image.sh ghcr.io/user/school-domnak:abc123
#   deploy-image.sh ghcr.io/user/school-domnak:abc123 ghcr.io/user/school-domnak-backend:abc123
# =============================================================================
set -euo pipefail

FRONTEND_IMAGE="${1:-}"
BACKEND_IMAGE="${2:-}"
NAMESPACE="devops-lab"
FRONTEND_DEPLOYMENT="devops-app"
FRONTEND_CONTAINER="devops-app"
BACKEND_DEPLOYMENT="backend"
BACKEND_CONTAINER="backend"
TIMEOUT="${DEPLOY_TIMEOUT:-300s}"

if [[ -z "${FRONTEND_IMAGE}" ]]; then
  echo "ERROR: Frontend image argument required." >&2
  echo "Usage: $0 <frontend-image> [backend-image]" >&2
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
  local label="${1:-}"
  echo ""
  echo "========== Pod status (${label}) =========="
  kubectl get pods -n "${NAMESPACE}" -o wide || true
  echo ""
  echo "========== Recent events =========="
  kubectl get events -n "${NAMESPACE}" --sort-by='.lastTimestamp' | tail -20 || true
}

rollout() {
  local deployment="$1"
  echo "==> Waiting for ${deployment} rollout (timeout ${TIMEOUT})..."
  if ! kubectl rollout status "deployment/${deployment}" -n "${NAMESPACE}" --timeout="${TIMEOUT}"; then
    echo "ERROR: Rollout for ${deployment} did not finish in time."
    show_diagnostics "${deployment}"
    exit 1
  fi
}

echo "==> Updating frontend image to: ${FRONTEND_IMAGE}"
kubectl set image "deployment/${FRONTEND_DEPLOYMENT}" "${FRONTEND_CONTAINER}=${FRONTEND_IMAGE}" -n "${NAMESPACE}"
rollout "${FRONTEND_DEPLOYMENT}"

if [[ -n "${BACKEND_IMAGE}" ]]; then
  if kubectl get deployment "${BACKEND_DEPLOYMENT}" -n "${NAMESPACE}" >/dev/null 2>&1; then
    echo "==> Updating backend image to: ${BACKEND_IMAGE}"
    kubectl set image "deployment/${BACKEND_DEPLOYMENT}" "${BACKEND_CONTAINER}=${BACKEND_IMAGE}" -n "${NAMESPACE}"
    rollout "${BACKEND_DEPLOYMENT}"
  else
    echo "WARNING: deployment/${BACKEND_DEPLOYMENT} not found — apply k8s/backend.yaml first."
  fi
fi

echo "==> Pods:"
kubectl get pods -n "${NAMESPACE}"

echo "==> Services:"
kubectl get svc -n "${NAMESPACE}"

echo "==> Deploy complete."
