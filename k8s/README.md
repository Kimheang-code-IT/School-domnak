# Kubernetes manifests (K3s on EC2)

## Kubernetes Free Deployment with K3s on AWS EC2

This project uses **K3s on a single AWS EC2 instance** instead of **AWS EKS** to avoid extra AWS cost (no EKS control plane, no ALB, no RDS, no NAT Gateway).

**GitHub Actions** deploys automatically when code is pushed to the **`devops-lab`** branch (workflow: `.github/workflows/cd-k3s.yml`).

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
| 80 | HTTP (optional) |
| 443 | HTTPS (optional) |
| 30000 | Frontend NodePort |
| 30080 | Backend NodePort |

### GitHub Secrets (repository settings)

| Secret | Description |
|--------|-------------|
| `AWS_HOST` | EC2 public IP or hostname |
| `AWS_USER` | SSH user (usually `ubuntu`) |
| `AWS_SSH_KEY` | Private SSH key (PEM) |

### Kubernetes Secret (manual on EC2 only)

Do **not** commit real secrets. Create `school-domnak-secrets` on the server once — see [docs/k3s-setup.md](../docs/k3s-setup.md).

### Manifest files

| File | Description |
|------|-------------|
| `namespace.yaml` | Namespace `school-domnak` |
| `postgres.yaml` | PostgreSQL 16 |
| `redis.yaml` | Redis 7 |
| `backend.yaml` | FastAPI backend (NodePort 30080) |
| `frontend.yaml` | Nuxt static frontend (NodePort 30000) |
| `secret.example.yaml` | Example secret keys (not applied by CD) |

### First-time server setup

See [docs/k3s-setup.md](../docs/k3s-setup.md) for K3s install, kubectl config, and secret creation.
