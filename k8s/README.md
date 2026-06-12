# Kubernetes manifests — Hostinger VPS + K3s

## Architecture (Ubuntu host nginx → K3s)

```
User browser
    ↓  http://72.62.250.194:80
Ubuntu nginx (on VPS host — not Docker public port)
    ↓  proxy_pass http://127.0.0.1:30000
K3s NodePort Service (devops-app)
    ↓
Pod (container nginx serves app on :3000 — internal only)
```

Traefik ingress is **not** used for public access. Host nginx owns port **80**.

---

## Architecture (no source code on VPS)

| Step | Where |
|------|--------|
| Source code | **GitHub** (checkout on Actions runner only) |
| Build & test | **GitHub Actions** (`ci.yml`) |
| Build Docker image | **GitHub Actions** (`cd-k3s.yml`) |
| Store images | **GHCR** (`ghcr.io/<username>/<repo>:<sha>`) |
| Deploy | **Hostinger VPS** — `deploy-image.sh` updates K3s only |
| Run workloads | **K3s** pulls images from GHCR |

The VPS stores **only** Docker images, Kubernetes YAML, and deployment scripts under `/opt/devops-runtime/`. It never stores application source code.

Workflow: [`.github/workflows/cd-k3s.yml`](../.github/workflows/cd-k3s.yml) — **CD Deploy to Hostinger K3s** (not AWS).

Full pipeline: [docs/CI-CD.md](../docs/CI-CD.md)

---

## Deploy flow

1. Push to **`devops-lab`** → **SchoolDomnak CI** (tests) and **CD Deploy to Hostinger K3s** (build + deploy) run together.

Manual deploy: **Actions → CD Deploy to Hostinger K3s → Run workflow**

See [docs/CI-CD.md](../docs/CI-CD.md) for the full diagram.

---

## Required GitHub secrets

| Secret | Description |
|--------|-------------|
| `GHCR_TOKEN` | GitHub PAT with `write:packages` (push) and `read:packages` (VPS pull) |
| `GHCR_USERNAME` | GitHub username for GHCR login and image path |
| `VPS_HOST` | Hostinger VPS IP (e.g. `72.62.250.194`) |
| `VPS_USER` | SSH user (e.g. `root`) |
| `VPS_SSH_KEY` | Private SSH key contents (PEM) |

**Do not commit secrets to the repository.**

---

## One-time VPS setup

1. Install K3s + Docker on VPS (see [docs/k3s-setup.md](../docs/k3s-setup.md)).
2. Create runtime folders:
   ```bash
   mkdir -p /opt/devops-runtime/{k8s,scripts}
   ```
3. Copy manifests from your PC (YAML only):
   ```powershell
   scp -i $env:USERPROFILE\.ssh\sdh_devops_new -r .\k8s root@72.62.250.194:/opt/devops-runtime/
   scp -i $env:USERPROFILE\.ssh\sdh_devops_new .\scripts\deploy-image.sh root@72.62.250.194:/opt/devops-runtime/scripts/
   ```
4. Apply manifests (namespace first):
   ```bash
   kubectl apply -f /opt/devops-runtime/k8s/namespace.yaml
   kubectl apply -f /opt/devops-runtime/k8s/deployment.yaml
   kubectl apply -f /opt/devops-runtime/k8s/service.yaml
   ```
4. Setup host nginx:
   ```bash
   /opt/devops-runtime/scripts/setup-host-nginx.sh
   ```

CD applies Kubernetes YAML and updates the image only. **Host nginx is manual** (see below).

---

## Manifest files

| File | Description |
|------|-------------|
| `namespace.yaml` | Namespace `devops-lab` |
| `deployment.yaml` | App `devops-app`, container port **3000**, pulls from GHCR |
| `service.yaml` | NodePort **30000** → pod port 3000 (for host nginx) |
| `ingress.yaml` | Removed — use host nginx instead |
| `nginx/host-k3s-proxy.conf` | Ubuntu host nginx config |
| `scripts/setup-host-nginx.sh` | Install/configure host nginx on VPS |

### Legacy multi-service manifests (optional)

These are **not** used by the current Hostinger CD workflow:

| File | Description |
|------|-------------|
| `postgres.yaml` | PostgreSQL (legacy — not used) |
| `redis.yaml` | Redis (legacy — not used) |
| `backend.yaml` | FastAPI backend (legacy — not used) |
| `frontend.yaml` | Frontend NodePort (legacy — not used) |
| `secret.example.yaml` | Example secrets — never commit real values |

---

## Access

| VPS IP | `http://72.62.250.194` (Ubuntu **host** nginx on port 80) |

---

## One-time / manual host nginx setup

From Windows:

```powershell
scp -i $env:USERPROFILE\.ssh\sdh_devops_new nginx/host-k3s-proxy.conf root@72.62.250.194:/opt/devops-runtime/nginx/
scp -i $env:USERPROFILE\.ssh\sdh_devops_new scripts/setup-host-nginx.sh root@72.62.250.194:/opt/devops-runtime/scripts/
```

On VPS:

```bash
kubectl apply -f /opt/devops-runtime/k8s/service.yaml
chmod +x /opt/devops-runtime/scripts/setup-host-nginx.sh
/opt/devops-runtime/scripts/setup-host-nginx.sh
curl -I http://127.0.0.1/
```

---

## Manual deploy (without waiting for CD)

```bash
/opt/devops-runtime/scripts/deploy-image.sh ghcr.io/kimheang-code-it/school-domnak:latest
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ImagePullBackOff` / `401 Unauthorized` | Private GHCR — recreate `ghcr-secret` (see below) and re-apply `k8s/deployment.yaml` (has `imagePullSecrets`) |
| Pod container named `app` not `devops-app` | Old Hostinger placeholder — re-apply `k8s/deployment.yaml` from this repo |
| Rollout stuck | `kubectl get pods -n devops-lab` and `kubectl describe pod -n devops-lab <name>` |

### Fix GHCR pull on VPS (manual)

```bash
kubectl delete secret ghcr-secret -n devops-lab --ignore-not-found
kubectl create secret docker-registry ghcr-secret \
  --namespace=devops-lab \
  --docker-server=ghcr.io \
  --docker-username=kimheang-code-it \
  --docker-password=YOUR_GHCR_TOKEN

kubectl apply -f /opt/devops-runtime/k8s/deployment.yaml
kubectl delete pods -n devops-lab -l app=devops-app
```

Ensure `GHCR_TOKEN` is a PAT with **`read:packages`** (and `write:packages` for CI push).

On GitHub: **Packages → school-domnak → Package settings** — link package to `School-domnak` repo or allow org access.

- VPS has no git clone of the application repository.
- Images are built only in GitHub Actions.
- Use private GHCR packages + `ghcr-secret` on the cluster.
- Rotate `GHCR_TOKEN` and SSH keys periodically.
