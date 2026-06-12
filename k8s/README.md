# Kubernetes manifests — Hostinger VPS + K3s

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

Workflow: [`.github/workflows/cd-k3s.yml`](../.github/workflows/cd-k3s.yml) — runs **automatically after CI passes** on branch **`devops-lab`**.

Full pipeline diagram: [docs/CI-CD.md](../docs/CI-CD.md)

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

1. Install K3s + Docker on VPS (see `D:\hostinger-terraform` or `docs/k3s-setup.md`).
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
   kubectl apply -f /opt/devops-runtime/k8s/ingress.yaml
   ```
5. Update `k8s/deployment.yaml` image placeholder and `k8s/ingress.yaml` host before first apply.

CD creates `ghcr-secret` automatically on each deploy.

---

## Manifest files

| File | Description |
|------|-------------|
| `namespace.yaml` | Namespace `devops-lab` |
| `deployment.yaml` | App `devops-app`, container port **3000**, pulls from GHCR |
| `service.yaml` | ClusterIP port 80 → targetPort 3000 |
| `ingress.yaml` | Traefik ingress, host placeholder `your-domain.com` |

### Legacy multi-service manifests (optional)

These are **not** used by the current Hostinger CD workflow:

| File | Description |
|------|-------------|
| `postgres.yaml` | PostgreSQL (legacy EC2 setup) |
| `redis.yaml` | Redis (legacy EC2 setup) |
| `backend.yaml` | FastAPI backend (legacy EC2 setup) |
| `frontend.yaml` | Frontend NodePort (legacy EC2 setup) |
| `secret.example.yaml` | Example secrets — never commit real values |

---

## Access

| Method | URL |
|--------|-----|
| Ingress (after DNS) | `http://your-domain.com` |
| VPS IP via Traefik | `http://<VPS_HOST>` (if no host rule match, configure DNS) |

Point DNS A record for `your-domain.com` to your VPS IP. UFW must allow ports **22**, **80**, **443**.

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
