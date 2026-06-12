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

echo "==> Updating deployment image to: ${IMAGE}"
kubectl set image "deployment/${DEPLOYMENT}" "${CONTAINER}=${IMAGE}" -n "${NAMESPACE}"

echo "==> Waiting for rollout..."
kubectl rollout status "deployment/${DEPLOYMENT}" -n "${NAMESPACE}" --timeout=300s

echo "==> Pods:"
kubectl get pods -n "${NAMESPACE}"

echo "==> Deploy complete."
