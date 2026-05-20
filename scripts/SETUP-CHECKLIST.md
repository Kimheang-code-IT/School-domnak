# School-domnak setup checklist

Follow in order. Check each box when done.

## Already done on your machine (if you ran the agent setup)

- [x] Docker Desktop + Kubernetes running
- [x] Namespace `schooldomnak` created
- [x] Secret `school-secrets` from `.env`
- [x] Code pushed to GitHub (`main`) — CI + GHCR workflows triggered

## You must do (about 15 minutes)

### Step 1 — Wait for GHCR images (GitHub website)

1. Open https://github.com/Kimheang-code-IT/School-domnak/actions
2. Wait until **SchoolDomnak GHCR Publish** is green (first run may take 5–10 min).
3. Open https://github.com/orgs/Kimheang-code-IT/packages (or your profile **Packages**).
4. For each `schooldomnak-*` package: **Package settings** → allow access for repo **School-domnak** (if images are private).

### Step 2 — GHCR pull secret on Kubernetes

Create a GitHub PAT: **Settings → Developer settings → Personal access tokens** with `read:packages`.

```powershell
cd "D:\project\School Domnak"
.\scripts\setup-ghcr-pull-secret.ps1 -GitHubUsername YOUR_GITHUB_USERNAME -GitHubToken YOUR_PAT
```

### Step 3 — Self-hosted runner (required for auto deploy)

1. Open https://github.com/Kimheang-code-IT/School-domnak/settings/actions/runners/new?arch=x64&os=win
2. Create folder `D:\actions-runner-schooldomnak` and download/extract the runner there.
3. Run the **config.cmd** line from GitHub (includes `--token ...`).
4. Install as service (recommended):

```bat
cd D:\actions-runner-schooldomnak
.\svc install
.\svc start
```

Or keep interactive: `.\run.cmd`

5. In GitHub **Settings → Actions → Runners**, status must show **Idle** (green).

### Step 4 — Deploy (automatic or manual)

**Automatic:** After Step 3, re-run deploy or push again:

```powershell
git commit --allow-empty -m "trigger deploy"
git push origin main
```

Wait for **SchoolDomnak K8s Local Deploy** (self-hosted) to finish green.

**Manual** (if runner not ready yet):

```powershell
cd "D:\project\School Domnak"
kubectl apply -f deploy/kubernetes/nginx/
kubectl rollout restart deployment/school-backend deployment/school-frontend deployment/school-celery-worker deployment/school-celery-beat deployment/school-telegram-bot -n schooldomnak
kubectl get pods -n schooldomnak
```

### Step 5 — Open the app

```powershell
kubectl get svc school-nginx -n schooldomnak
```

Open **http://localhost** (Docker Desktop LoadBalancer maps port 80).

## Verify

```powershell
kubectl get pods -n schooldomnak
kubectl get svc -n schooldomnak
```

All pods should be `Running` / `READY 1/1`.

## If something fails

| Symptom | Fix |
|---------|-----|
| `ErrImagePull` / `denied` | Step 2 + Step 1 package access |
| K8s deploy workflow skipped | Runner offline — Step 3 |
| `school-secrets` not found | `kubectl create secret generic school-secrets -n schooldomnak --from-env-file=.env` |
| nginx CrashLoop | `kubectl apply -f deploy/kubernetes/nginx/` (config fix) |
