#!/usr/bin/env bash
# =============================================================================
# Create self-signed TLS cert for school.72-62-250-194.sslip.io
# Run on VPS as root (before setup-host-nginx.sh)
#
# Usage:
#   ./setup-ssl-self-signed.sh
#   ./setup-ssl-self-signed.sh school.72-62-250-194.sslip.io
# =============================================================================
set -euo pipefail

DOMAIN="${1:-school.72-62-250-194.sslip.io}"
SSL_DIR="/etc/nginx/ssl"
CERT_FILE="${SSL_DIR}/school-domnak.crt"
KEY_FILE="${SSL_DIR}/school-domnak.key"
DAYS="${SSL_DAYS:-365}"

install -d -m 755 "${SSL_DIR}"

if [[ -f "${CERT_FILE}" && -f "${KEY_FILE}" ]]; then
  echo "==> SSL files already exist:"
  echo "    ${CERT_FILE}"
  echo "    ${KEY_FILE}"
  echo "    Delete them first to regenerate."
  exit 0
fi

echo "==> Generating self-signed certificate for ${DOMAIN} (${DAYS} days)..."
openssl req -x509 -nodes -days "${DAYS}" -newkey rsa:2048 \
  -keyout "${KEY_FILE}" \
  -out "${CERT_FILE}" \
  -subj "/CN=${DOMAIN}/O=School Domnak/C=KH"

chmod 644 "${CERT_FILE}"
chmod 600 "${KEY_FILE}"

echo "==> Done."
echo "    Certificate: ${CERT_FILE}"
echo "    Private key: ${KEY_FILE}"
echo ""
echo "Browsers will warn (self-signed). Accept once or use Let's Encrypt later."
