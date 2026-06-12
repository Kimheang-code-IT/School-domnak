# K3s setup on AWS EC2 (Ubuntu)

University DevOps lab guide for **School-domnak** — one small EC2 instance, no EKS.

## 1. Launch EC2

- **AMI:** Ubuntu 22.04 or 24.04 LTS
- **Instance type:** `t3.small` or `t3.medium` (free tier / low cost)
- **Storage:** 20–30 GB gp3
- **Security group inbound:** `22`, `80`, `443`, `30000`, `30080`
- Attach a **key pair** for SSH

## 2. Install Docker (for building images on EC2)

```bash
sudo apt-get update
sudo apt-get install -y docker.io git
sudo usermod -aG docker ubuntu
newgrp docker
```

## 3. Clone the repository

```bash
cd /home/ubuntu
git clone https://github.com/YOUR_ORG/School-domnak.git school-devops-lab
cd school-devops-lab
git checkout devops-lab
```

## 4. Install K3s

```bash
curl -sfL https://get.k3s.io | sh -
```

## 5. Configure kubectl

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown ubuntu:ubuntu ~/.kube/config
chmod 600 ~/.kube/config
```

## 6. Check node

```bash
kubectl get nodes
```

Expected: one node in `Ready` state.

## 7. Create namespace and real secret (manual — never commit to Git)

Replace `EC2_PUBLIC_IP` with your instance public IP.

```bash
kubectl create namespace school-domnak --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic school-domnak-secrets \
  --namespace school-domnak \
  --from-literal=APP_ENV='production' \
  --from-literal=SECRET_KEY='change-this-secret' \
  --from-literal=POSTGRES_PASSWORD='postgres' \
  --from-literal=DATABASE_URL='postgresql+psycopg2://postgres:postgres@postgres:5432/school_db' \
  --from-literal=REDIS_URL='redis://redis:6379/0' \
  --from-literal=CELERY_BROKER_URL='redis://redis:6379/0' \
  --from-literal=CELERY_RESULT_BACKEND='redis://redis:6379/1' \
  --from-literal=NUXT_PUBLIC_API_BASE='http://EC2_PUBLIC_IP:30080/api/v1' \
  --from-literal=NUXT_PUBLIC_USE_BACKEND_API='true' \
  --dry-run=client -o yaml | kubectl apply -f -
```

## 8. First manual deploy (optional)

```bash
cd /home/ubuntu/school-devops-lab

docker build -t school-backend:latest ./backend
docker build -t school-frontend:latest ./Frontend \
  --build-arg NUXT_PUBLIC_API_BASE='http://EC2_PUBLIC_IP:30080/api/v1' \
  --build-arg NUXT_PUBLIC_USE_BACKEND_API=true

docker save school-backend:latest | sudo k3s ctr images import -
docker save school-frontend:latest | sudo k3s ctr images import -

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml

kubectl get pods -n school-domnak
kubectl get svc -n school-domnak
```

## 9. Verify

```bash
curl http://127.0.0.1:30080/health
curl -I http://127.0.0.1:30000
```

From your browser:

- Backend: `http://EC2_PUBLIC_IP:30080/health`
- Frontend: `http://EC2_PUBLIC_IP:30000`

## 10. GitHub Actions CD

Add repository secrets: `AWS_HOST`, `AWS_USER`, `AWS_SSH_KEY`.

Push to `devops-lab` — workflow `.github/workflows/cd-k3s.yml` runs automatically.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ImagePullBackOff` | Re-import images: `docker save ... \| sudo k3s ctr images import -` |
| Backend `CrashLoopBackOff` | Check secret exists: `kubectl get secret -n school-domnak` |
| Postgres not ready | Wait 30s after first deploy; check `kubectl logs deployment/postgres -n school-domnak` |
| Frontend shows wrong API URL | Rebuild frontend image with correct `NUXT_PUBLIC_API_BASE` build-arg |
| SSH timeout from GitHub | Open port 22 in security group to `0.0.0.0/0` (lab only) |
