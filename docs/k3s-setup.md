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
- **Instance type:** `t3.micro` or `t3.small` (lab / low cost)
- **Storage:** 20–30 GB gp3
- **Security group inbound:** `22`, `30000`, `30080` (optional: `80`, `443`)
- Attach a **key pair** for SSH

## 2. Clone the repository

```bash
cd /home/ubuntu
git clone https://github.com/YOUR_ORG/School-domnak.git school-devops-lab
cd school-devops-lab
git checkout devops-lab
```

Docker on EC2 is **optional** (only needed for local debugging). CD no longer builds images on the server.

## 3. Install K3s

```bash
# --write-kubeconfig-mode allows the ubuntu user to read the cluster config
curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644
```

## 4. Verify K3s and kubectl

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

## 5. Check node

```bash
kubectl get nodes
```

## 6. Create namespace and Kubernetes secret (manual — never commit to Git)

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

## 7. GitHub Secrets (repository settings)

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

## 8. CD workflow (automatic)

Push to branch **`devops-lab`**:

1. GitHub Actions builds backend + frontend on a fast runner
2. Pushes to `ghcr.io/<owner>/school-domnak-backend` and `school-domnak-frontend`
3. SSH to EC2 → pull manifests → `kubectl set image` with commit SHA
4. K3s pulls images from GHCR using `ghcr-secret`

## 9. Verify

```bash
curl http://127.0.0.1:30080/health
curl -I http://127.0.0.1:30000
```

| Service | URL |
|---------|-----|
| Backend | `http://EC2_PUBLIC_IP:30080/health` |
| Frontend | `http://EC2_PUBLIC_IP:30000` |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ImagePullBackOff` | Check `ghcr-secret`, `GHCR_TOKEN`, package visibility |
| `ErrImagePull` / 401 | Regenerate PAT with `read:packages`; verify `GHCR_USERNAME` |
| Backend `CrashLoopBackOff` | `kubectl logs deployment/backend -n school-domnak`; check `school-domnak-secrets` |
| SSH timeout from GitHub | Security group: allow TCP **22** from `0.0.0.0/0` (lab only) |
| `TLS handshake timeout` (kubectl) | `sudo systemctl restart k3s` then `sudo k3s kubectl get nodes` |
| K3s API slow on t3.micro | Wait 2–3 min after reboot; CD retries up to 3 minutes |
| Frontend wrong API URL | Re-run CD after setting `AWS_HOST` secret correctly (used at build time) |
| Slow build (old method) | Use new GHCR workflow — do not build on EC2 |
