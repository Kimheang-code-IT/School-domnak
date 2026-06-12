#!/usr/bin/env bash
# =============================================================================
# Configure Ubuntu host nginx → K3s NodePort (not Traefik, not public Docker nginx)
# Run on VPS as root. Safe to re-run.
#
# Flow:  User → Ubuntu nginx :80 → localhost:30000 → K3s Service → Pod
# =============================================================================
set -euo pipefail

K3S_NODE_PORT="${K3S_NODE_PORT:-30000}"
NGINX_SITE_NAME="devops-k3s"
CONFIG_SRC="${1:-/opt/devops-runtime/nginx/host-k3s-proxy.conf}"

kubectl() {
  if command -v k3s >/dev/null 2>&1; then
    k3s kubectl "$@"
  else
    command kubectl "$@"
  fi
}

export KUBECONFIG="${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}"

echo "==> Install nginx on Ubuntu host (if missing)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx

echo "==> Remove Traefik ingress (host nginx is the public entry)..."
kubectl delete ingress devops-app -n devops-lab --ignore-not-found 2>/dev/null || true

echo "==> Free port 80 from K3s Traefik (host nginx owns :80)..."
kubectl -n kube-system scale deployment traefik --replicas=0 2>/dev/null || true
kubectl -n kube-system delete svc traefik --ignore-not-found 2>/dev/null || true
for ds in $(kubectl -n kube-system get daemonset -o name 2>/dev/null | grep traefik || true); do
  kubectl -n kube-system delete "$ds" --ignore-not-found 2>/dev/null || true
done

echo "==> Install nginx site config..."
if [[ ! -f "${CONFIG_SRC}" ]]; then
  echo "ERROR: Config not found: ${CONFIG_SRC}" >&2
  exit 1
fi

install -d /opt/devops-runtime/nginx
install -m 644 "${CONFIG_SRC}" /opt/devops-runtime/nginx/host-k3s-proxy.conf
install -m 644 "${CONFIG_SRC}" "/etc/nginx/sites-available/${NGINX_SITE_NAME}"

rm -f /etc/nginx/sites-enabled/default
ln -sf "/etc/nginx/sites-available/${NGINX_SITE_NAME}" "/etc/nginx/sites-enabled/${NGINX_SITE_NAME}"

echo "==> Test nginx and reload..."
nginx -t
systemctl enable nginx
systemctl restart nginx

echo "==> Verify K3s NodePort ${K3S_NODE_PORT} responds..."
if curl -sf "http://127.0.0.1:${K3S_NODE_PORT}/" -o /dev/null; then
  echo "    NodePort OK"
else
  echo "    WARNING: NodePort not responding yet — check: kubectl get svc -n devops-lab"
fi

echo "==> Verify host nginx on port 80..."
if curl -sf "http://127.0.0.1/" -o /dev/null; then
  echo "    Host nginx OK — users open http://VPS_IP"
else
  echo "    WARNING: host nginx not responding — check: systemctl status nginx"
fi

echo "==> Done. Public URL: http://$(curl -sf ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
