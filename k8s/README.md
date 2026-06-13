# Kubernetes manifests — Hostinger VPS + K3s (full stack)

## Architecture

```
Browser → Ubuntu host nginx (:80 / :443)
            ├── /        → frontend NodePort 30000 → devops-app pod
            └── /api/    → backend NodePort 30080 → FastAPI pod

Backend → postgres:5432 (ClusterIP, inside K3s)
Backend → redis:6379

Local PC (DBeaver) → VPS:30432 → postgres NodePort
```

| Component | K8s name | NodePort | Notes |
|-----------|----------|----------|-------|
| Frontend | `devops-app` | 30000 | Static Nuxt SPA |
| Backend | `backend` | 30080 | FastAPI + Alembic migrations |
| PostgreSQL | `postgres` | **30432** | Persistent volume — connect from local tools |
| Redis | `redis` | (internal) | Celery optional (`USE_CELERY_TASKS=false` by default) |

Traefik is **not** used for public access. Host nginx owns port **80/443**.

---

## Deploy flow

1. Push to **`devops-lab`** → CI tests + CD builds **frontend + backend** → GHCR
2. CD SSH to VPS → apply k8s manifests → update both images

Workflow: [`.github/workflows/cd-k3s.yml`](../.github/workflows/cd-k3s.yml)

---

## One-time VPS setup

### 1. Copy files to VPS

```powershell
scp -i $env:USERPROFILE\.ssh\sdh_devops_new -r .\k8s root@72.62.250.194:/opt/devops-runtime/
scp -i $env:USERPROFILE\.ssh\sdh_devops_new .\scripts\*.sh root@72.62.250.194:/opt/devops-runtime/scripts/
scp -i $env:USERPROFILE\.ssh\sdh_devops_new .\nginx\host-k3s-proxy.conf root@72.62.250.194:/opt/devops-runtime/nginx/
ssh -i $env:USERPROFILE\.ssh\sdh_devops_new root@72.62.250.194 "chmod +x /opt/devops-runtime/scripts/*.sh"
```

### 2. Create secrets (required before first deploy)

**Generate automatically:**

```powershell
bash scripts/generate-k8s-secret.sh
scp k8s/secret.yaml root@72.62.250.194:/opt/devops-runtime/k8s/
```

**Or copy template and edit** — see `k8s/secret.example.yaml` (complete list):

| Key | Purpose |
|-----|---------|
| `POSTGRES_DB` | Database name (postgres pod) |
| `POSTGRES_USER` | Database user (postgres pod) |
| `POSTGRES_PASSWORD` | Database password (postgres pod) |
| `DATABASE_URL` | Backend connection (`@postgres:5432` inside K3s) |
| `SECRET_KEY` | JWT signing key |
| `BACKEND_CORS_ORIGINS` | Must include `https://school.72-62-250-194.sslip.io` |

```bash
kubectl apply -f /opt/devops-runtime/k8s/secret.yaml
```

`POSTGRES_PASSWORD` must match the password inside `DATABASE_URL`.

### 3. HTTPS certificate + nginx

```bash
/opt/devops-runtime/scripts/setup-ssl-self-signed.sh
/opt/devops-runtime/scripts/setup-host-nginx.sh /opt/devops-runtime/nginx/host-k3s-proxy.conf
```

Public URL: **https://school.72-62-250-194.sslip.io**

### 4. Apply stack

```bash
/opt/devops-runtime/scripts/apply-k8s-stack.sh
```

### 5. Open PostgreSQL for local DB tools

```bash
# Replace with your home public IP
/opt/devops-runtime/scripts/open-postgres-firewall.sh YOUR_HOME_IP
```

Also allow **TCP 30432** in Hostinger hPanel firewall.

**Local connection:**

```
postgresql://postgres:YOUR_PASSWORD@72.62.250.194:30432/school_db
```

---

## Google Sheets backup (service account JSON)

Uses `backend/credentials/school-domnak-576f89315ae9.json` (never commit this file).

### 1. Share spreadsheet with service account

In Google Sheets → **Share** → add as **Editor**:

```
school-domnak@school-domnak.iam.gserviceaccount.com
```

Spreadsheet ID from URL (`/d/<ID>/edit`):

```
https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit
```

### 2. Copy JSON to VPS + create K8s secret

**Windows:**

```powershell
cd "D:\School Domnak"
$KEY = "$env:USERPROFILE\.ssh\sdh_devops_new"
$VPS = "root@72.62.250.194"

scp -i $KEY .\backend\credentials\school-domnak-576f89315ae9.json ${VPS}:/tmp/google-sheets-service-account.json
scp -i $KEY .\scripts\setup-google-sheets-secret.sh ${VPS}:/opt/devops-runtime/scripts/
ssh -i $KEY $VPS "sed -i 's/\r$//' /opt/devops-runtime/scripts/setup-google-sheets-secret.sh && chmod +x /opt/devops-runtime/scripts/setup-google-sheets-secret.sh"
ssh -i $KEY $VPS "/opt/devops-runtime/scripts/setup-google-sheets-secret.sh /tmp/google-sheets-service-account.json"
```

### 3. Enable in secret.yaml on VPS

```yaml
GOOGLE_SHEETS_BACKUP_ENABLED: "true"
GOOGLE_SHEETS_CREDENTIALS_FILE: /app/secrets/google-sheets-service-account.json
GOOGLE_SHEETS_SPREADSHEET_ID: YOUR_SPREADSHEET_ID
```

```bash
kubectl apply -f /opt/devops-runtime/k8s/secret.yaml
kubectl apply -f /opt/devops-runtime/k8s/backend.yaml
kubectl rollout restart deployment/backend -n devops-lab
```

### 4. Test backup

```bash
kubectl exec -n devops-lab deploy/backend -- python scripts/run_google_sheets_backup.py
```

Automatic daily backup runs at **19:00** (`Asia/Phnom_Penh`) while backend pod is running.

Manual API (admin login required): `POST https://school.72-62-250-194.sslip.io/api/v1/backup/google-sheets`

---

## Manifest files

| File | Description |
|------|-------------|
| `namespace.yaml` | Namespace `devops-lab` |
| `postgres.yaml` | PostgreSQL 16 + PVC + NodePort **30432** |
| `redis.yaml` | Redis 7 (internal) |
| `backend.yaml` | FastAPI backend + NodePort **30080** |
| `deployment.yaml` | Frontend `devops-app` |
| `service.yaml` | Frontend NodePort **30000** |
| `secret.example.yaml` | Template — copy to `secret.yaml` on VPS only |

---

## Reset database on VPS

```bash
kubectl scale deployment backend -n devops-lab --replicas=0
kubectl delete pvc postgres-data -n devops-lab
kubectl apply -f /opt/devops-runtime/k8s/postgres.yaml
kubectl scale deployment backend -n devops-lab --replicas=1
```

Backend runs `alembic upgrade head` on startup. Then open `/register-admin`.

---

## Manual deploy

```bash
/opt/devops-runtime/scripts/deploy-image.sh \
  ghcr.io/kimheang-code-it/school-domnak:latest \
  ghcr.io/kimheang-code-it/school-domnak-backend:latest
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| CD fails: secret missing | Create `school-domnak-secrets` from `secret.example.yaml` |
| `ImagePullBackOff` | Recreate `ghcr-secret` (see below) |
| `/api` returns 502 | Check backend pod: `kubectl logs -n devops-lab deploy/backend` |
| Cannot connect to DB locally | Open UFW + Hostinger firewall for port **30432** |
| Backend crash loop | Postgres not ready — check `kubectl get pods -n devops-lab` |

### Fix GHCR pull on VPS

```bash
kubectl delete secret ghcr-secret -n devops-lab --ignore-not-found
kubectl create secret docker-registry ghcr-secret \
  --namespace=devops-lab \
  --docker-server=ghcr.io \
  --docker-username=kimheang-code-it \
  --docker-password=YOUR_GHCR_TOKEN
```

See also: [docs/k3s-setup.md](../docs/k3s-setup.md), [docs/CI-CD.md](../docs/CI-CD.md)
