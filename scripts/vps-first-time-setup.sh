#!/usr/bin/env bash
# =============================================================================
# One-time VPS setup after copying files from Windows (fixes CRLF + full stack)
# Run on VPS as root:
#   bash /opt/devops-runtime/scripts/vps-first-time-setup.sh
# =============================================================================
set -euo pipefail

RUNTIME="/opt/devops-runtime"
SCRIPTS="${RUNTIME}/scripts"
K8S="${RUNTIME}/k8s"

fix_crlf() {
  echo "==> Fix Windows CRLF in shell scripts..."
  if [[ -d "${SCRIPTS}" ]]; then
    sed -i 's/\r$//' "${SCRIPTS}"/*.sh 2>/dev/null || true
    chmod +x "${SCRIPTS}"/*.sh 2>/dev/null || true
  fi
}

kubectl_cmd() {
  if command -v k3s >/dev/null 2>&1; then
    k3s kubectl "$@"
  else
    kubectl "$@"
  fi
}

export KUBECONFIG="${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}"

fix_crlf

if [[ ! -f "${K8S}/secret.yaml" ]]; then
  echo "ERROR: ${K8S}/secret.yaml missing."
  echo "  cp ${K8S}/secret.example.yaml ${K8S}/secret.yaml"
  echo "  nano ${K8S}/secret.yaml   # set passwords"
  exit 1
fi

echo "==> Apply Kubernetes secret..."
kubectl_cmd apply -f "${K8S}/secret.yaml"

echo "==> Apply full K8s stack..."
"${SCRIPTS}/apply-k8s-stack.sh"

if [[ -x "${SCRIPTS}/setup-ssl-self-signed.sh" ]]; then
  echo "==> Create SSL certificate..."
  "${SCRIPTS}/setup-ssl-self-signed.sh"
else
  echo "WARNING: setup-ssl-self-signed.sh missing — copy scripts from PC first."
fi

if [[ -f "${RUNTIME}/nginx/host-k3s-proxy.conf" && -x "${SCRIPTS}/setup-host-nginx.sh" ]]; then
  echo "==> Configure host nginx (HTTPS)..."
  "${SCRIPTS}/setup-host-nginx.sh" "${RUNTIME}/nginx/host-k3s-proxy.conf"
fi

echo ""
echo "==> Pod status:"
kubectl_cmd get pods,svc -n devops-lab

echo ""
echo "==> Next steps:"
echo "  1. Create ghcr-secret (if ImagePullBackOff): see k8s/README.md"
echo "  2. Push to devops-lab branch OR run deploy-image.sh with frontend + backend images"
echo "  3. Open postgres firewall for local DBeaver:"
echo "       ${SCRIPTS}/open-postgres-firewall.sh YOUR_HOME_IP"
echo "  4. Site: https://school.72-62-250-194.sslip.io/register-admin"
