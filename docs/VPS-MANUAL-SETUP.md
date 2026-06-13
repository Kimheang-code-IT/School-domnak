# VPS manual setup — Hostinger K3s (no shell scripts)

Everything below is **copy-paste commands** only. No `.sh` files on the VPS.


| Item                        | Value                                   |
| --------------------------- | --------------------------------------- |
| VPS IP                      | `72.62.250.194`                         |
| Site                        | `https://school.72-62-250-194.sslip.io` |
| K8s namespace               | `devops-lab`                            |
| Postgres NodePort (DBeaver) | `30432`                                 |


---

## Part 1 — Copy files from Windows (PowerShell)

```powershell
cd "D:\School Domnak"

$KEY = "$env:USERPROFILE\.ssh\sdh_devops_new"
$VPS = "root@72.62.250.194"

ssh -i $KEY $VPS "mkdir -p /opt/devops-runtime/k8s /opt/devops-runtime/nginx"

scp -i $KEY -r .\k8s\*                  ${VPS}:/opt/devops-runtime/k8s/
scp -i $KEY .\nginx\host-k3s-proxy.conf ${VPS}:/opt/devops-runtime/nginx/
```

---

## Part 2 — Create `secret.yaml` on VPS

```bash
cp /opt/devops-runtime/k8s/secret.example.yaml /opt/devops-runtime/k8s/secret.yaml
nano /opt/devops-runtime/k8s/secret.yaml
```

Replace:


| Key                            | Example                                  |
| ------------------------------ | ---------------------------------------- |
| `SECRET_KEY`                   | output of `openssl rand -hex 32`         |
| `POSTGRES_PASSWORD`            | plain password (letters+numbers easiest) |
| `DATABASE_URL`                 | same password in URL — see below         |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | your spreadsheet ID                      |


**DATABASE_URL rules**

- Host inside K3s must be `postgres` (not `localhost`)
- Password must match `POSTGRES_PASSWORD`
- Use a **simple password** (no `@`, `$`, `#`) OR URL-encode special chars

Example (password `SchoolDomnak2026`):

```yaml
POSTGRES_PASSWORD: SchoolDomnak2026
DATABASE_URL: postgresql+psycopg2://postgres:SchoolDomnak2026@postgres:5432/school_db
```

If password has special characters, encode on VPS:

```bash
python3 -c "from urllib.parse import quote_plus; print(quote_plus('YOUR_PASSWORD'))"
```

Use encoded value **only** in `DATABASE_URL`, plain text in `POSTGRES_PASSWORD`.

Apply:

```bash
kubectl apply -f /opt/devops-runtime/k8s/secret.yaml
```

---

## Part 3 — Google Sheets credentials (optional)

**Windows — copy JSON:**

```powershell
scp -i $KEY .\backend\credentials\school-domnak-576f89315ae9.json ${VPS}:/tmp/google-sheets-service-account.json
```

**VPS — create K8s secret:**

```bash
kubectl create secret generic google-sheets-credentials \
  --namespace=devops-lab \
  --from-file=google-sheets-service-account.json=/tmp/google-sheets-service-account.json

rm -f /tmp/google-sheets-service-account.json
```

Share spreadsheet with **Editor**:

```
school-domnak@school-domnak.iam.gserviceaccount.com
```

In `secret.yaml`:

```yaml
GOOGLE_SHEETS_BACKUP_ENABLED: "true"
GOOGLE_SHEETS_CREDENTIALS_FILE: /app/secrets/google-sheets-service-account.json
GOOGLE_SHEETS_SPREADSHEET_ID: 1ue-Zdq5qwyHrXJxvj03hAVLnXoK0ZPcH6L6lA5v_GOM
```

```bash
kubectl apply -f /opt/devops-runtime/k8s/secret.yaml
```

---

## Part 4 — Apply Kubernetes stack (manual)

```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
K8S=/opt/devops-runtime/k8s

kubectl apply -f $K8S/namespace.yaml
kubectl apply -f $K8S/postgres.yaml
kubectl apply -f $K8S/redis.yaml

kubectl wait --for=condition=ready pod -l app=postgres -n devops-lab --timeout=180s
kubectl wait --for=condition=ready pod -l app=redis -n devops-lab --timeout=120s

kubectl apply -f $K8S/backend.yaml
kubectl apply -f $K8S/deployment.yaml
kubectl apply -f $K8S/service.yaml
```

---

## Part 5 — GHCR pull secret (manual)

```bash
kubectl delete secret ghcr-secret -n devops-lab --ignore-not-found
kubectl create secret docker-registry ghcr-secret \
  --namespace=devops-lab \
  --docker-server=ghcr.io \
  --docker-username=kimheang-code-it \
  --docker-password=YOUR_GHCR_PAT
```

---

## Part 6 — SSL certificate (manual)

```bash
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/school-domnak.key \
  -out /etc/nginx/ssl/school-domnak.crt \
  -subj "/CN=school.72-62-250-194.sslip.io"
chmod 600 /etc/nginx/ssl/school-domnak.key
chmod 644 /etc/nginx/ssl/school-domnak.crt
```

---

## Part 7 — Nginx HTTPS (manual)

```bash
apt-get update && apt-get install -y nginx

cp /opt/devops-runtime/nginx/host-k3s-proxy.conf /etc/nginx/sites-available/devops-k3s
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/devops-k3s /etc/nginx/sites-enabled/devops-k3s

nginx -t
systemctl enable nginx
systemctl restart nginx
```

Scale down Traefik if port 80/443 conflict:

```bash
kubectl -n kube-system scale deployment traefik --replicas=0
```

---

## Part 8 — Deploy images (manual or via GitHub CD)

**Option A — push to `devops-lab`** (GitHub Actions builds + deploys via SSH/kubectl)

**Option B — manual on VPS:**

```bash
kubectl set image deployment/devops-app devops-app=ghcr.io/kimheang-code-it/school-domnak:latest -n devops-lab
kubectl set image deployment/backend backend=ghcr.io/kimheang-code-it/school-domnak-backend:latest -n devops-lab

kubectl rollout status deployment/devops-app -n devops-lab --timeout=300s
kubectl rollout status deployment/backend -n devops-lab --timeout=600s
```

---

## Part 9 — Verify

```bash
kubectl get pods -n devops-lab
curl -k https://school.72-62-250-194.sslip.io/api/v1/auth/setup-status
```

Open: **[https://school.72-62-250-194.sslip.io/register-admin](https://school.72-62-250-194.sslip.io/register-admin)**

Test Google Sheets backup:

```bash
kubectl exec -n devops-lab deploy/backend -- python scripts/run_google_sheets_backup.py
```

---

## Part 10 — DBeaver from your PC

Open firewall (replace with your home IP):

```bash
ufw allow from YOUR_HOME_IP to any port 30432 proto tcp
```


| Field    | Value                           |
| -------- | ------------------------------- |
| Host     | `72.62.250.194`                 |
| Port     | `30432`                         |
| Database | `school_db`                     |
| User     | `postgres`                      |
| Password | `POSTGRES_PASSWORD` from secret |


---

## Reset database

```bash
kubectl scale deployment backend -n devops-lab --replicas=0
kubectl delete pvc postgres-data -n devops-lab
kubectl apply -f /opt/devops-runtime/k8s/postgres.yaml
kubectl apply -f /opt/devops-runtime/k8s/secret.yaml
kubectl scale deployment backend -n devops-lab --replicas=1
```

---

## Troubleshooting


| Problem                                   | Fix                                                               |
| ----------------------------------------- | ----------------------------------------------------------------- |
| Backend `CrashLoopBackOff` + `$@postgres` | Fix `DATABASE_URL` — password must match, no unencoded `@` or `$` |
| `ImagePullBackOff`                        | Recreate `ghcr-secret` (Part 5)                                   |
| `/api` 502                                | `kubectl logs -n devops-lab deploy/backend --tail=50`             |
| Secret missing                            | Part 2 — `kubectl apply -f secret.yaml`                           |


Check backend logs:

```bash
kubectl logs -n devops-lab -l app=backend -c backend --tail=50
```

Fix DATABASE_URL with Python:

```bash
python3 << 'EOF'
from urllib.parse import quote_plus
user, password, db = "postgres", "YOUR_PLAIN_PASSWORD", "school_db"
print(f"postgresql+psycopg2://{user}:{quote_plus(password)}@postgres:5432/{db}")
EOF
```

Copy output into `secret.yaml` → `kubectl apply` → `kubectl delete pod -n devops-lab -l app=backend`