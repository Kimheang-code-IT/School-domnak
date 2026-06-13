# K3s setup on Hostinger VPS (Ubuntu)

University DevOps guide for **School-domnak** — **Hostinger VPS only** (no AWS, no EC2, no EKS).

| Item | Value |
|------|--------|
| Provider | Hostinger KVM VPS |
| OS | Ubuntu 24.04 LTS |
| Example IP | `72.62.250.194` |
| SSH user | `root` |
| CD workflow | `.github/workflows/cd-k3s.yml` → **CD Deploy to Hostinger K3s** |

---

## Architecture

| Step | Where |
|------|--------|
| Source code | GitHub only |
| Build Docker images | GitHub Actions (frontend + backend) |
| Store images | GHCR |
| Deploy | SSH → Hostinger VPS → K3s |
| VPS stores | **No source code** — images + k8s YAML + scripts only |
| Database | PostgreSQL in K3s (persistent volume) |
| Local DB tools | Connect to VPS IP port **30432** (after firewall) |

```
Browser → Ubuntu nginx :80/:443
            ├── /        → frontend NodePort 30000
            └── /api/    → backend NodePort 30080
Backend → postgres:5432 (inside K3s)
Local PC → VPS:30432 → postgres (DBeaver / pgAdmin)
```

---

## 0. Allow GitHub Actions to SSH (required for CD)

CD connects from **GitHub servers** to your VPS on port **22**. If CD shows `dial tcp :22: i/o timeout`, open SSH:

**On VPS (UFW):**
```bash
ufw allow 22/tcp
ufw status
```

**Hostinger hPanel:** VPS → **Security / Firewall** → allow **TCP 22** from anywhere (or add GitHub Actions IP ranges).

**Test from your PC:**
```powershell
ssh -i $env:USERPROFILE\.ssh\sdh_devops_new root@72.62.250.194
```

GitHub secret `VPS_HOST` must be `72.62.250.194` (no `http://`, no port).

---

## 1. Copy from Windows → VPS (one-time)

Run in **PowerShell** on your PC:

```powershell
cd "D:\School Domnak"

$KEY  = "$env:USERPROFILE\.ssh\sdh_devops_new"
$VPS  = "root@72.62.250.194"

# Create folders on VPS
ssh -i $KEY $VPS "mkdir -p /opt/devops-runtime/k8s /opt/devops-runtime/scripts /opt/devops-runtime/nginx"

# Copy k8s YAML + nginx + all scripts
scp -i $KEY -r .\k8s\*          ${VPS}:/opt/devops-runtime/k8s/
scp -i $KEY .\scripts\*.sh      ${VPS}:/opt/devops-runtime/scripts/
scp -i $KEY .\nginx\host-k3s-proxy.conf ${VPS}:/opt/devops-runtime/nginx/

# Fix Windows CRLF (fixes "bash\r: No such file or directory")
ssh -i $KEY $VPS "sed -i 's/\r$//' /opt/devops-runtime/scripts/*.sh && chmod +x /opt/devops-runtime/scripts/*.sh"
```

**If you already copied files and see `bash\r` error**, run only the fix line on VPS:

```bash
sed -i 's/\r$//' /opt/devops-runtime/scripts/*.sh
chmod +x /opt/devops-runtime/scripts/*.sh
```

### Create secrets (one-time, on VPS)

**Option A — generate on PC (recommended):**

```powershell
cd "D:\School Domnak"
bash scripts/generate-k8s-secret.sh
scp -i $env:USERPROFILE\.ssh\sdh_devops_new k8s/secret.yaml root@72.62.250.194:/opt/devops-runtime/k8s/
ssh -i $env:USERPROFILE\.ssh\sdh_devops_new root@72.62.250.194 "kubectl apply -f /opt/devops-runtime/k8s/secret.yaml"
```

**Option B — edit manually on VPS:**

```bash
cp /opt/devops-runtime/k8s/secret.example.yaml /opt/devops-runtime/k8s/secret.yaml
nano /opt/devops-runtime/k8s/secret.yaml
# Replace REPLACE_POSTGRES_PASSWORD (same in POSTGRES_PASSWORD + DATABASE_URL)
# Replace REPLACE_WITH_openssl_rand_hex_32 for SECRET_KEY
kubectl apply -f /opt/devops-runtime/k8s/secret.yaml
```

**Never commit `secret.yaml`.**

Secret includes: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`, Redis, CORS, Telegram, Google Sheets.

### HTTPS + sslip.io (one-time)

```bash
/opt/devops-runtime/scripts/setup-ssl-self-signed.sh
/opt/devops-runtime/scripts/setup-host-nginx.sh /opt/devops-runtime/nginx/host-k3s-proxy.conf
```

Site URL: **https://school.72-62-250-194.sslip.io**

### Apply everything on VPS (after secret.yaml is ready)

On **VPS** (SSH in as root):

```bash
# 1. Edit secret (if not done yet)
nano /opt/devops-runtime/k8s/secret.yaml
# Replace REPLACE_POSTGRES_PASSWORD and REPLACE_WITH_openssl_rand_hex_32

# 2. One command: secret + stack + SSL + nginx
bash /opt/devops-runtime/scripts/vps-first-time-setup.sh
```

Or step by step:

```bash
kubectl apply -f /opt/devops-runtime/k8s/secret.yaml
/opt/devops-runtime/scripts/apply-k8s-stack.sh
/opt/devops-runtime/scripts/setup-ssl-self-signed.sh
/opt/devops-runtime/scripts/setup-host-nginx.sh /opt/devops-runtime/nginx/host-k3s-proxy.conf
```

### GHCR pull secret (required for private images)

```bash
kubectl create namespace devops-lab --dry-run=client -o yaml | kubectl apply -f -
kubectl delete secret ghcr-secret -n devops-lab --ignore-not-found
kubectl create secret docker-registry ghcr-secret \
  --namespace=devops-lab \
  --docker-server=ghcr.io \
  --docker-username=kimheang-code-it \
  --docker-password=YOUR_GHCR_PAT
```

### Deploy images

Push to **`devops-lab`** on GitHub (CD builds frontend + backend), **or** manual:

```bash
/opt/devops-runtime/scripts/deploy-image.sh \
  ghcr.io/kimheang-code-it/school-domnak:latest \
  ghcr.io/kimheang-code-it/school-domnak-backend:latest
```

Check:

```bash
kubectl get pods -n devops-lab
```

Expected: `devops-app`, `backend`, `postgres`, `redis` all Running.

### Open PostgreSQL for local DB tools

From your PC, get your public IP: `curl ifconfig.me`

On VPS (restrict to your IP only):

```bash
/opt/devops-runtime/scripts/open-postgres-firewall.sh YOUR_HOME_IP
```

Also open **TCP 30432** in Hostinger hPanel → VPS → Firewall.

**DBeaver / pgAdmin connection:**

| Field | Value |
|-------|--------|
| Host | `72.62.250.194` |
| Port | `30432` |
| Database | `school_db` (`POSTGRES_DB`) |
| User | `postgres` (`POSTGRES_USER`) |
| Password | `POSTGRES_PASSWORD` from secret |

Connection string:

```
postgresql://postgres:YOUR_PASSWORD@72.62.250.194:30432/school_db
```

Public app: **https://school.72-62-250-194.sslip.io**

CD only runs **SSH + deploy-image.sh** — it does not copy files or configure nginx.

```powershell
scp -i $env:USERPROFILE\.ssh\sdh_devops_new install-vps-runtime.sh root@72.62.250.194:/tmp/
ssh -i $env:USERPROFILE\.ssh\sdh_devops_new root@72.62.250.194 "sed -i 's/\r$//' /tmp/install-vps-runtime.sh && bash /tmp/install-vps-runtime.sh"
```

UFW must allow: **22**, **80**, **443**.

Verify:

```bash
kubectl get nodes
docker --version
```

---

## 2. VPS folders (no app source)

```bash
mkdir -p /opt/devops-runtime/{k8s,scripts}
```

Copy from your PC (YAML + script only):

```powershell
scp -i $env:USERPROFILE\.ssh\sdh_devops_new -r .\k8s root@72.62.250.194:/opt/devops-runtime/
scp -i $env:USERPROFILE\.ssh\sdh_devops_new .\scripts\deploy-image.sh root@72.62.250.194:/opt/devops-runtime/scripts/
```

---

## 3. GitHub Secrets (Hostinger — NOT AWS)

| Secret | Example | Description |
|--------|---------|-------------|
| `VPS_HOST` | `72.62.250.194` | Hostinger VPS IP |
| `VPS_USER` | `root` | SSH user |
| `VPS_SSH_KEY` | (PEM contents) | Private SSH key |
| `GHCR_USERNAME` | `Kimheang-code-IT` | GitHub username |
| `GHCR_TOKEN` | (PAT) | `read:packages` + `write:packages` |

**Do not use** `AWS_HOST`, `AWS_USER`, or `AWS_SSH_KEY` — those are legacy.

---

## 4. Automatic CD (devops-lab branch)

Push to **`devops-lab`**:

1. **SchoolDomnak CI** — runs tests
2. **CD Deploy to Hostinger K3s** — builds frontend + backend → pushes GHCR → SSH → full K3s stack update

Manual run: **Actions → CD Deploy to Hostinger K3s → Run workflow**

---

## 5. Manual Ubuntu host nginx (one-time on VPS)

CD does **not** configure nginx automatically. Run this once on the VPS:

```powershell
scp -i $env:USERPROFILE\.ssh\sdh_devops_new nginx/host-k3s-proxy.conf root@72.62.250.194:/opt/devops-runtime/nginx/
scp -i $env:USERPROFILE\.ssh\sdh_devops_new scripts/setup-host-nginx.sh root@72.62.250.194:/opt/devops-runtime/scripts/
```

```bash
kubectl apply -f /opt/devops-runtime/k8s/service.yaml
chmod +x /opt/devops-runtime/scripts/setup-host-nginx.sh
/opt/devops-runtime/scripts/setup-host-nginx.sh /opt/devops-runtime/nginx/host-k3s-proxy.conf
```

Flow: **User → Ubuntu nginx :80 → frontend :30000 + backend :30080 (/api)**

Re-run after updating `host-k3s-proxy.conf` (adds `/api/` proxy to backend).

---

## 6. Verify deployment

On VPS:

```bash
kubectl get pods -n devops-lab
kubectl get svc -n devops-lab
curl -I http://127.0.0.1:30000/
curl -I http://127.0.0.1:30080/health
curl -I http://127.0.0.1/api/v1/auth/setup-status
```

From browser: **https://school.72-62-250-194.sslip.io/register-admin**

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `dial tcp :22: i/o timeout` in CD | Open port **22** in UFW + Hostinger firewall (section 0) |
| `ImagePullBackOff` / 401 | Recreate `ghcr-secret` — see [k8s/README.md](../k8s/README.md) |
| `CreateContainerError` / no command | Image was wrong stage — CD must use `target: runtime` in Dockerfile build |
| CD not running | Push to `devops-lab`; check **CD Deploy to Hostinger K3s** workflow exists |
| Old AWS workflows in Actions sidebar | Delete old `.github/workflows/cd-aws*.yml` from repo on GitHub |

See also: [docs/CI-CD.md](./CI-CD.md), [k8s/README.md](../k8s/README.md)
