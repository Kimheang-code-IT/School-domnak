#!/usr/bin/env bash
# =============================================================================
# Generate k8s/secret.yaml from secret.example.yaml with random SECRET_KEY + password.
# Run on your PC or VPS — output is secret.yaml (gitignored).
#
# Usage:
#   ./scripts/generate-k8s-secret.sh
#   ./scripts/generate-k8s-secret.sh "MyStrongPostgresPassword"
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXAMPLE="${REPO_ROOT}/k8s/secret.example.yaml"
OUTPUT="${REPO_ROOT}/k8s/secret.yaml"

if [[ ! -f "${EXAMPLE}" ]]; then
  echo "ERROR: ${EXAMPLE} not found." >&2
  exit 1
fi

POSTGRES_PASSWORD="${1:-}"
if [[ -z "${POSTGRES_PASSWORD}" ]]; then
  if command -v openssl >/dev/null 2>&1; then
    POSTGRES_PASSWORD="$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)"
  else
    POSTGRES_PASSWORD="$(date +%s | sha256sum | head -c 24)"
  fi
fi

if command -v openssl >/dev/null 2>&1; then
  SECRET_KEY="$(openssl rand -hex 32)"
else
  SECRET_KEY="$(date +%s | sha256sum | awk '{print $1}')"
fi

sed \
  -e "s|REPLACE_WITH_openssl_rand_hex_32|${SECRET_KEY}|g" \
  -e "s|REPLACE_POSTGRES_PASSWORD|${POSTGRES_PASSWORD}|g" \
  "${EXAMPLE}" > "${OUTPUT}"

echo "==> Wrote ${OUTPUT}"
echo ""
echo "PostgreSQL (local DBeaver):"
echo "  Host:     72.62.250.194"
echo "  Port:     30432"
echo "  Database: school_db   (POSTGRES_DB)"
echo "  User:     postgres    (POSTGRES_USER)"
echo "  Password: ${POSTGRES_PASSWORD}"
echo ""
echo "Apply on VPS:"
echo "  scp k8s/secret.yaml root@72.62.250.194:/opt/devops-runtime/k8s/"
echo "  ssh root@72.62.250.194 kubectl apply -f /opt/devops-runtime/k8s/secret.yaml"
