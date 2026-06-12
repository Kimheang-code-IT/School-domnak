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

Workflow: [`.github/workflows/cd-k3s.yml`](../.github/workflows/cd-k3s.yml) — runs on branch **`devops-lab`** only.

Repository: [Kimheang-code-IT/School-domnak](https://github.com/Kimheang-code-IT/School-domnak.git)

GHCR image: `ghcr.io/<GHCR_USERNAME>/school-domnak:<commit-sha>`

---

## Deploy flow

1. Push to **`devops-lab`** (or run workflow manually from Actions tab).
2. **CI** runs tests on pull requests and pushes (`ci.yml`).
3. **CD** builds the Frontend Docker image on GitHub Actions.
4. CD pushes to GHCR:
   - `ghcr.io/<GHCR_USERNAME>/<repo>:<commit-sha>`
   - `ghcr.io/<GHCR_USERNAME>/<repo>:latest`
5. CD SSH into the Hostinger VPS (no source copy).
6. CD syncs `scripts/deploy-image.sh` only.
7. CD runs `/opt/devops-runtime/scripts/deploy-image.sh <image>`.
8. K3s pulls the new image and restarts pods in namespace `devops-lab`.

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

## Security notes

- VPS has no git clone of the application repository.
- Images are built only in GitHub Actions.
- Use private GHCR packages + `ghcr-secret` on the cluster.
- Rotate `GHCR_TOKEN` and SSH keys periodically.
