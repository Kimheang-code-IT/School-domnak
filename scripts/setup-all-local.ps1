# One-shot local setup: Kubernetes + GHCR images + deploy School-domnak
# Run from repo root:  .\scripts\setup-all-local.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$env:KUBECONFIG = Join-Path $env:USERPROFILE ".kube\config"
if (-not (Test-Path $env:KUBECONFIG)) {
    Write-Error "Enable Kubernetes in Docker Desktop first, then run: kubectl get nodes"
}

Write-Host "=== 1. Kubernetes cluster ===" -ForegroundColor Cyan
kubectl cluster-info
kubectl get nodes

Write-Host "`n=== 2. Namespace and secrets ===" -ForegroundColor Cyan
kubectl apply -f deploy/kubernetes/namespace.yaml

if (-not (kubectl get secret school-secrets -n schooldomnak 2>$null)) {
    if (-not (Test-Path ".env")) {
        Write-Error "Missing .env — run: cp .env.example .env"
    }
    kubectl create secret generic school-secrets -n schooldomnak --from-env-file=.env
    Write-Host "Created school-secrets from .env" -ForegroundColor Green
} else {
    Write-Host "school-secrets already exists" -ForegroundColor Green
}

Write-Host "`n=== 3. Pull GHCR images (Docker) ===" -ForegroundColor Cyan
$images = @(
    "ghcr.io/kimheang-code-it/schooldomnak-backend:latest",
    "ghcr.io/kimheang-code-it/schooldomnak-frontend:latest"
)
foreach ($img in $images) {
    Write-Host "Pulling $img ..."
    docker pull $img
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Pull failed for $img — login: docker login ghcr.io -u YOUR_GITHUB_USER"
        Write-Warning "Or run: .\scripts\setup-ghcr-pull-secret.ps1 -GitHubUsername USER -GitHubToken PAT"
    }
}

Write-Host "`n=== 4. Apply manifests ===" -ForegroundColor Cyan
kubectl apply -f deploy/kubernetes/configmap.yaml
kubectl apply -f deploy/kubernetes/postgres/
kubectl apply -f deploy/kubernetes/redis/
kubectl apply -f deploy/kubernetes/backend/
kubectl apply -f deploy/kubernetes/frontend/
kubectl apply -f deploy/kubernetes/celery/
kubectl apply -f deploy/kubernetes/telegram/
kubectl apply -f deploy/kubernetes/nginx/

Write-Host "`n=== 5. Clean stuck pods and restart ===" -ForegroundColor Cyan
kubectl delete pods -n schooldomnak --field-selector=status.phase=Failed 2>$null
kubectl rollout restart deployment/school-backend -n schooldomnak
kubectl rollout restart deployment/school-frontend -n schooldomnak
kubectl rollout restart deployment/school-celery-worker -n schooldomnak
kubectl rollout restart deployment/school-celery-beat -n schooldomnak
kubectl rollout restart deployment/school-telegram-bot -n schooldomnak
kubectl rollout restart deployment/school-nginx -n schooldomnak

Write-Host "`n=== 6. Wait for rollouts (up to 10 min) ===" -ForegroundColor Cyan
$deployments = @("school-backend", "school-frontend", "school-nginx", "school-postgres", "school-redis")
foreach ($d in $deployments) {
    kubectl rollout status "deployment/$d" -n schooldomnak --timeout=600s
    if ($LASTEXITCODE -ne 0) { Write-Warning "$d not ready yet" }
}

Write-Host "`n=== 7. Status ===" -ForegroundColor Cyan
kubectl get pods -n schooldomnak
kubectl get svc -n schooldomnak

Write-Host "`nOpen app: http://localhost  (nginx LoadBalancer)" -ForegroundColor Green
Write-Host "If not ready: kubectl get pods -n schooldomnak" -ForegroundColor Yellow
Write-Host "Keep GitHub runner running: cd D:\actions-runner-schooldomnak; .\run.cmd" -ForegroundColor Yellow
