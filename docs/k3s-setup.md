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
| Build Docker image | GitHub Actions |
| Store image | GHCR (`ghcr.io/kimheang-code-it/school-domnak`) |
| Deploy | SSH → Hostinger VPS → K3s |
| VPS stores | **No source code** — images + k8s YAML + scripts only |

---

## 1. VPS runtime (one-time)

Install Docker + K3s + UFW. Use the script from `D:\hostinger-terraform\install-vps-runtime.sh` or:

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
2. **CD Deploy to Hostinger K3s** — builds image → pushes GHCR → SSH to VPS → `kubectl` update

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

Flow: **User → Ubuntu nginx :80 → K3s NodePort :30000 → Pod**

---

## 6. Verify deployment

On VPS:

```bash
kubectl get pods -n devops-lab
kubectl get svc -n devops-lab
curl -I http://127.0.0.1:3000
```

From browser: `http://72.62.250.194` (Ubuntu **host** nginx → K3s NodePort 30000)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ImagePullBackOff` / 401 | Recreate `ghcr-secret` — see [k8s/README.md](../k8s/README.md) |
| `CreateContainerError` / no command | Image was wrong stage — CD must use `target: runtime` in Dockerfile build |
| CD not running | Push to `devops-lab`; check **CD Deploy to Hostinger K3s** workflow exists |
| Old AWS workflows in Actions sidebar | Delete old `.github/workflows/cd-aws*.yml` from repo on GitHub |

See also: [docs/CI-CD.md](./CI-CD.md), [k8s/README.md](../k8s/README.md)
