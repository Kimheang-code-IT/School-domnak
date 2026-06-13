#!/usr/bin/env bash
# =============================================================================
# Open PostgreSQL NodePort (30432) for local DB tools (DBeaver, pgAdmin).
# Restrict to your home IP — do NOT expose Postgres to the whole internet.
#
# Usage:
#   ./open-postgres-firewall.sh YOUR_HOME_PUBLIC_IP
#   ./open-postgres-firewall.sh YOUR_HOME_PUBLIC_IP 30432
# =============================================================================
set -euo pipefail

CLIENT_IP="${1:-}"
PORT="${2:-30432}"

if [[ -z "${CLIENT_IP}" ]]; then
  echo "Usage: $0 <your-public-ip> [port]" >&2
  echo "Find your IP: curl -s ifconfig.me" >&2
  exit 1
fi

if ! command -v ufw >/dev/null 2>&1; then
  echo "ERROR: ufw not found." >&2
  exit 1
fi

echo "==> Allow PostgreSQL NodePort ${PORT} from ${CLIENT_IP} only"
ufw allow from "${CLIENT_IP}" to any port "${PORT}" proto tcp comment "School Domnak Postgres"

echo ""
echo "==> UFW status:"
ufw status numbered

echo ""
echo "Also open TCP ${PORT} in Hostinger hPanel → VPS → Firewall (same IP restriction if possible)."
echo ""
echo "Local connection:"
echo "  Host:     $(curl -sf ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
echo "  Port:     ${PORT}"
echo "  Database: school_db"
echo "  User:     postgres"
echo "  Password: (from school-domnak-secrets POSTGRES_PASSWORD)"
