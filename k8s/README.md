# Kubernetes manifests (K3s on EC2)

## Kubernetes Free Deployment with K3s on AWS EC2

This project uses **K3s on a single AWS EC2 instance** instead of **AWS EKS** to avoid extra AWS cost (no EKS, ALB, RDS, NAT Gateway, or ECR).

### CD architecture (improved)

| Step | Where |
|------|--------|
| Build Docker images | **GitHub Actions** (fast runner) |
| Store images | **GitHub Container Registry (GHCR)** — free |
| Deploy | SSH to EC2 → `kubectl apply` + `kubectl set image` |
| Run workloads | **K3s** pulls images from GHCR |

**Old slow method:** build Nuxt + backend on t3.micro EC2 → import into K3s.  
**New method:** build on GitHub, push to GHCR, EC2 only pulls and deploys.

Workflow: `.github/workflows/cd-k3s.yml` (branch: `devops-lab`).

### Access URLs

Replace `EC2_PUBLIC_IP` with your instance public IP:

| Service | URL |
|---------|-----|
| Backend health | http://EC2_PUBLIC_IP:30080/health |
| Frontend | http://EC2_PUBLIC_IP:30000 |

### AWS Security Group (inbound)

| Port | Purpose |
|------|---------|
| 22 | SSH (GitHub Actions deploy) |
| 30000 | Frontend NodePort |
| 30080 | Backend NodePort |

### GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_HOST` | EC2 public IP |
| `AWS_USER` | SSH user (`ubuntu`) |
| `AWS_SSH_KEY` | Private SSH key (PEM) |
| `GHCR_USERNAME` | GitHub username (K3s pull) |
| `GHCR_TOKEN` | PAT with `read:packages` (K3s pull) |

### Kubernetes secrets (manual on EC2)

Do **not** commit real secrets. Create `school-domnak-secrets` once — see [docs/k3s-setup.md](../docs/k3s-setup.md).

CD creates `ghcr-secret` automatically for pulling images from GHCR.

### Manifest files

| File | Description |
|------|-------------|
| `namespace.yaml` | Namespace `school-domnak` |
| `postgres.yaml` | PostgreSQL 16 |
| `redis.yaml` | Redis 7 |
| `backend.yaml` | FastAPI (NodePort 30080, pulls from GHCR) |
| `frontend.yaml` | Nuxt static (NodePort 30000, pulls from GHCR) |
| `secret.example.yaml` | Example only — not applied by CD |

### First-time setup

See [docs/k3s-setup.md](../docs/k3s-setup.md).
