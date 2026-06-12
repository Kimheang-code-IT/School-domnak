# CI/CD — GitHub Actions → GHCR → Hostinger VPS K3s

Automatic pipeline for [School-domnak](https://github.com/Kimheang-code-IT/School-domnak.git) on branch **`devops-lab`**.

**The VPS never builds Docker images and never stores source code.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub (your PC pushes code)                               │
│  Branch: devops-lab                                         │
└───────────────────────────┬─────────────────────────────────┘
                            │ push
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  CI  (.github/workflows/ci.yml)                             │
│  • Frontend tests + build                                   │
│  • Backend migrate + smoke test                             │
│  • Docker build validation (no push)                        │
└───────────────────────────┬─────────────────────────────────┘
                            │ CI success (push only)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  CD  (.github/workflows/cd-k3s.yml)                         │
│  • Build Frontend Docker image on GitHub runner             │
│  • Push to GHCR:                                            │
│      ghcr.io/kimheang-code-it/school-domnak:<commit-sha>    │
│      ghcr.io/kimheang-code-it/school-domnak:latest          │
│  • SSH → Hostinger VPS (YAML + deploy script only)          │
│  • kubectl updates K3s deployment                           │
└───────────────────────────┬─────────────────────────────────┘
                            │ pull image (authenticated)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Hostinger VPS 72.62.250.194                                │
│  • K3s Kubernetes                                           │
│  • Namespace: devops-lab                                    │
│  • No git clone, no docker build, no app source             │
│  • Only: images + k8s YAML + deploy-image.sh                │
└─────────────────────────────────────────────────────────────┘
```

---

## What runs where

| Task | GitHub Actions | GHCR | Hostinger VPS |
|------|----------------|------|---------------|
| Source code checkout | Yes | — | **Never** |
| Run tests | Yes | — | No |
| `docker build` | Yes | — | **Never** |
| `docker push` | Yes | Receives image | No |
| `docker pull` | No | Serves image | Yes (via K3s) |
| `kubectl apply` | Triggers via SSH | — | Yes |
| Run containers | No | — | Yes (K3s) |

---

## Automatic flow (devops-lab branch)

1. You push code to **`devops-lab`**.
2. **CI** starts automatically — tests must pass.
3. When CI succeeds, **CD** starts automatically.
4. CD builds the image and pushes to **GitHub Container Registry (GHCR)**.
5. CD SSH into the VPS and runs `deploy-image.sh`.
6. K3s pulls the new image and restarts the pod.

If CI fails, **CD does not run** (no broken deploy).

Manual deploy anytime: **Actions → CD Deploy to Hostinger K3s → Run workflow**.

---

## Required GitHub secrets

| Secret | Purpose |
|--------|---------|
| `GHCR_USERNAME` | GitHub username for GHCR login |
| `GHCR_TOKEN` | PAT with `read:packages` + `write:packages` |
| `VPS_HOST` | VPS IP (e.g. `72.62.250.194`) |
| `VPS_USER` | SSH user (e.g. `root`) |
| `VPS_SSH_KEY` | Private SSH key (full PEM contents) |

**Settings → Secrets and variables → Actions**

---

## Docker image location

Images are **not** stored on the VPS filesystem as tar files. They live in **GHCR**:

```
ghcr.io/kimheang-code-it/school-domnak:<git-commit-sha>
ghcr.io/kimheang-code-it/school-domnak:latest
```

K3s/kubelet pulls from GHCR when the deployment updates.

---

## How to deploy

```powershell
cd "D:\School Domnak"
git checkout devops-lab
git add .
git commit -m "your message"
git push origin devops-lab
```

Watch progress: **GitHub → Actions**

1. Wait for **CI** to finish green.
2. **CD Deploy to Hostinger K3s** starts automatically.
3. Open the site when CD completes (Ingress / VPS IP).

---

## VPS one-time setup

See [k8s/README.md](../k8s/README.md) and [k3s-setup.md](./k3s-setup.md).

Minimum:

- K3s installed
- `/opt/devops-runtime/scripts/` exists
- UFW ports 22, 80, 443 open

CD applies Kubernetes YAML on every deploy — you do not need to copy manifests manually after the first successful CD run.

---

## Workflows in this repo

| File | Name | Trigger |
|------|------|---------|
| `.github/workflows/ci.yml` | CI | Every push + PR |
| `.github/workflows/cd-k3s.yml` | CD Deploy to Hostinger K3s | After CI success on `devops-lab` push, or manual |

---

## Security

- `.env` and secrets stay off the VPS and out of git.
- VPS receives only container images, K8s YAML, and the deploy script.
- GHCR packages should stay **private**; CD creates `ghcr-secret` on the cluster for pulls.
