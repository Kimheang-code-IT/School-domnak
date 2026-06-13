#!/usr/bin/env bash
# =============================================================================
# Apply full School Domnak stack on K3s (data layer + app layer).
# Run on VPS after copying k8s/ to /opt/devops-runtime/k8s/
#
# Prerequisites:
#   1. kubectl / K3s installed
#   2. Secret created: kubectl apply -f secret.yaml (from secret.example.yaml)
#   3. ghcr-secret created (CD does this automatically)
# =============================================================================
set -euo pipefail

K8S_DIR="${K8S_DIR:-/opt/devops-runtime/k8s}"

kubectl() {
  if command -v k3s >/dev/null 2>&1; then
    k3s kubectl "$@"
  else
    command kubectl "$@"
  fi
}

export KUBECONFIG="${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}"

apply_if_exists() {
  local file="$1"
  if [[ -f "${file}" ]]; then
    echo "==> Applying ${file}"
    kubectl apply -f "${file}"
  else
    echo "WARNING: missing ${file}" >&2
  fi
}

echo "==> Apply full stack from ${K8S_DIR}"

apply_if_exists "${K8S_DIR}/namespace.yaml"
apply_if_exists "${K8S_DIR}/postgres.yaml"
apply_if_exists "${K8S_DIR}/redis.yaml"
apply_if_exists "${K8S_DIR}/backend.yaml"
apply_if_exists "${K8S_DIR}/deployment.yaml"
apply_if_exists "${K8S_DIR}/service.yaml"

echo ""
echo "==> Waiting for data layer..."
kubectl wait --for=condition=ready pod -l app=postgres -n devops-lab --timeout=180s 2>/dev/null || true
kubectl wait --for=condition=ready pod -l app=redis -n devops-lab --timeout=120s 2>/dev/null || true

echo ""
kubectl get pods,svc,pvc -n devops-lab

echo ""
echo "==> Done. Postgres NodePort: 30432 (open firewall for local DB tools)."
