# K3s setup on AWS EC2 (Ubuntu)

University DevOps lab guide for **School-domnak** — one small EC2 instance, no EKS.

## Deployment methods

| Method | Where images build | Speed on t3.micro |
|--------|-------------------|-------------------|
| **Old (slow)** | Build on EC2 with `docker build` + `k3s ctr import` | Very slow (Nuxt + fonts) |
| **New (recommended)** | Build on GitHub Actions → push to **GHCR** → K3s pulls images | Fast on EC2 |

The CD workflow `.github/workflows/cd-k3s.yml` uses the **new method**.

## 1. Launch EC2

- **AMI:** Ubuntu 22.04 or 24.04 LTS
- **Instance type:** `t3.small` recommended (2 GB RAM). `t3.micro` (1 GB) works only with swap + 1 replica per app.
- **Storage:** 20–30 GB gp3
- **Security group inbound:** `22`, `30000`, `30080` (optional: `80`, `443`)
- Attach a **key pair** for SSH

## 2. EC2 stores no source code

GitHub Actions CD does **not** clone or `git pull` on EC2. The server only needs:

- **K3s** (Kubernetes)
- **`school-domnak-secrets`** (created once manually)
- **Containers** pulled from **GHCR**

Source code and Docker builds live on **GitHub** and **GHCR** only.

## 3. Add swap (required on t3.micro)

K3s + Postgres + Redis + backend + frontend needs more than 1 GB RAM.

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

## 4. Install K3s (lightweight — disable unused components)

```bash
curl -sfL https://get.k3s.io | sh -s - server \
  --write-kubeconfig-mode 644 \
  --disable traefik \
  --disable servicelb
```

Wait 60 seconds, then verify:

```bash
sudo k3s kubectl --request-timeout=120s get nodes
```

## 5. Verify K3s and kubectl

On K3s, use the embedded kubectl (recommended for CD and manual use):

```bash
sudo k3s kubectl get nodes
```

Optional — configure `kubectl` for the ubuntu user:

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown ubuntu:ubuntu ~/.kube/config
chmod 600 ~/.kube/config
kubectl get nodes
```

GitHub Actions CD uses `sudo k3s kubectl` (no kubeconfig file required).

If you see `TLS handshake timeout`, check K3s is running:

```bash
sudo systemctl status k3s
sudo systemctl restart k3s
sudo k3s kubectl get nodes
```

## 6. Create namespace and Kubernetes secret (manual — never commit to Git)

Replace `EC2_PUBLIC_IP` with your instance public IP.

```bash
sudo k3s kubectl create namespace school-domnak --dry-run=client -o yaml | sudo k3s kubectl apply -f -

sudo k3s kubectl create secret generic school-domnak-secrets \
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
  --dry-run=client -o yaml | sudo k3s kubectl apply -f -
```

## 7. Manual deploy (optional — normally use GitHub Actions CD)

Push to `devops-lab` and let `.github/workflows/cd-k3s.yml` deploy automatically.

For a one-time manual apply, copy only `k8s/*.yaml` from your PC (not the full repo):

```bash
scp -i your-key.pem k8s/*.yaml ubuntu@EC2_IP:/tmp/school-domnak-k8s/

ssh -i your-key.pem ubuntu@EC2_IP
sudo k3s kubectl apply -f /tmp/school-domnak-k8s/
rm -rf /tmp/school-domnak-k8s
```

## 8. GitHub Secrets (repository settings)

| Secret | Description |
|--------|-------------|
| `AWS_HOST` | EC2 public IP |
| `AWS_USER` | SSH user (`ubuntu`) |
| `AWS_SSH_KEY` | Private SSH key (PEM) |
| `GHCR_USERNAME` | GitHub username (for K3s image pull) |
| `GHCR_TOKEN` | GitHub PAT with `read:packages` (for K3s image pull) |

`GITHUB_TOKEN` is used automatically to **push** images from Actions (no extra secret needed for push).

### Create GHCR_TOKEN

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens**
2. Create token with scope: **`read:packages`**
3. Save as repository secret `GHCR_TOKEN`
4. Set `GHCR_USERNAME` to your GitHub username

### Package visibility

After the first CD run, open **GitHub → Packages** and either:

- Link packages to the `School-domnak` repository, or
- Set package visibility to **Public** (simplest for university lab)

## 9. CD workflow (automatic)

Push to branch **`devops-lab`**:

1. GitHub Actions checks out source code (on GitHub runner only)
2. Builds backend + frontend Docker images on GitHub runner
3. Pushes to `ghcr.io/<owner>/school-domnak-backend` and `school-domnak-frontend`
4. SCP copies **only** `k8s/*.yaml` to `/tmp/school-domnak-k8s` on EC2 (temporary)
5. SSH runs **kubectl only** — no `git pull`, no `docker build` on EC2
6. First deploy: `kubectl apply` manifests; later deploys: `kubectl set image` only
7. K3s pulls images from GHCR using `ghcr-secret`
8. Temporary manifest folder is deleted after deploy

## 10. Verify

```bash
curl http://127.0.0.1:30080/health
curl -I http://127.0.0.1:30000
```

| Service | URL |
|---------|-----|
| Backend | `http://EC2_PUBLIC_IP:30080/health` |
| Frontend | `http://EC2_PUBLIC_IP:30000` |

## Troubleshooting

### K3s API timeout / `context deadline exceeded` (t3.micro out of memory)

Your logs show **618 MB swap used** — the API is too slow to respond.

**Fix now (run on EC2):**

```bash
# 1. Add swap if missing
sudo swapon --show
# If empty, run the swap commands from section 3

# 2. Stop anything heavy (old Docker builds, etc.)
docker stop $(docker ps -q) 2>/dev/null || true

# 3. Restart K3s and wait
sudo systemctl restart k3s
sleep 90

# 4. Test API (use long timeout)
sudo k3s kubectl --request-timeout=120s get nodes
```

If still failing, **upgrade to t3.small** (2 GB RAM) in AWS Console → Instance → Change instance type.

### Secret exists but `kubectl get all` shows nothing

The secret was created, but **deployments were never applied** (CD failed before `kubectl apply`). Run section 7 (manual deploy) or re-run GitHub Actions after K3s is healthy.

### Other issues

| Problem | Fix |
|---------|-----|
| `ImagePullBackOff` | Check `ghcr-secret`, `GHCR_TOKEN`, package visibility |
| `ErrImagePull` / 401 | Regenerate PAT with `read:packages`; verify `GHCR_USERNAME` |
| Backend `CrashLoopBackOff` | `sudo k3s kubectl logs deployment/backend -n school-domnak` |
| SSH timeout from GitHub | Security group: allow TCP **22** from `0.0.0.0/0` (lab only) |
| Frontend wrong API URL | Re-run CD after setting `AWS_HOST` secret correctly |
