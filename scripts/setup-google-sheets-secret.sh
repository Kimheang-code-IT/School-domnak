#!/usr/bin/env bash
# =============================================================================
# Mount Google Sheets service account JSON into K8s for backend backup.
#
# Usage (on VPS):
#   ./setup-google-sheets-secret.sh /tmp/google-sheets-service-account.json
#
# Usage (copy from Windows first):
#   scp backend/credentials/school-domnak-576f89315ae9.json root@VPS:/tmp/google-sheets-service-account.json
#   ssh root@VPS /opt/devops-runtime/scripts/setup-google-sheets-secret.sh /tmp/google-sheets-service-account.json
# =============================================================================
set -euo pipefail

JSON_FILE="${1:-}"
NAMESPACE="devops-lab"
SECRET_NAME="google-sheets-credentials"

if [[ -z "${JSON_FILE}" || ! -f "${JSON_FILE}" ]]; then
  echo "Usage: $0 /path/to/service-account.json" >&2
  exit 1
fi

kubectl_cmd() {
  if command -v k3s >/dev/null 2>&1; then
    k3s kubectl "$@"
  else
    kubectl "$@"
  fi
}

export KUBECONFIG="${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}"

EMAIL="$(grep -o '"client_email"[[:space:]]*:[[:space:]]*"[^"]*"' "${JSON_FILE}" | sed 's/.*"\([^"]*\)"$/\1/')"
if [[ -z "${EMAIL}" ]]; then
  echo "ERROR: Could not read client_email from ${JSON_FILE}" >&2
  exit 1
fi

echo "==> Creating secret ${SECRET_NAME} in ${NAMESPACE}..."
kubectl_cmd create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl_cmd apply -f -
kubectl_cmd delete secret "${SECRET_NAME}" -n "${NAMESPACE}" --ignore-not-found
kubectl_cmd create secret generic "${SECRET_NAME}" \
  --namespace="${NAMESPACE}" \
  --from-file=google-sheets-service-account.json="${JSON_FILE}"

echo "==> Restart backend to mount credentials..."
kubectl_cmd rollout restart deployment/backend -n "${NAMESPACE}" 2>/dev/null || true

echo ""
echo "==> Done."
echo "Share your Google Spreadsheet with this service account (Editor):"
echo "  ${EMAIL}"
echo ""
echo "In secret.yaml set:"
echo "  GOOGLE_SHEETS_BACKUP_ENABLED: \"true\""
echo "  GOOGLE_SHEETS_SPREADSHEET_ID: <id from spreadsheet URL>"
echo ""
echo "Test backup (after backend is running):"
echo "  kubectl exec -n ${NAMESPACE} deploy/backend -- python scripts/run_google_sheets_backup.py"
