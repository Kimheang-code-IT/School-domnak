# Create Kubernetes secret so cluster can pull private GHCR images.
# Requires: GitHub PAT with read:packages (or use GITHUB_TOKEN from a logged-in gh session).

param(
    [Parameter(Mandatory = $true)]
    [string]$GitHubUsername,
    [Parameter(Mandatory = $true)]
    [string]$GitHubToken,
    [string]$Namespace = "schooldomnak"
)

$ErrorActionPreference = "Stop"

kubectl apply -f "$PSScriptRoot\..\deploy\kubernetes\namespace.yaml" 2>$null

kubectl create secret docker-registry ghcr-pull-secret `
    --docker-server=ghcr.io `
    --docker-username=$GitHubUsername `
    --docker-password=$GitHubToken `
    --namespace=$Namespace `
    --dry-run=client -o yaml | kubectl apply -f -

Write-Host "ghcr-pull-secret updated in namespace $Namespace" -ForegroundColor Green
Write-Host "Restart app deployments after GHCR publish completes:"
Write-Host "  kubectl rollout restart deployment/school-backend -n $Namespace"
Write-Host "  kubectl rollout restart deployment/school-frontend -n $Namespace"
Write-Host "  kubectl rollout restart deployment/school-celery-worker -n $Namespace"
Write-Host "  kubectl rollout restart deployment/school-celery-beat -n $Namespace"
Write-Host "  kubectl rollout restart deployment/school-telegram-bot -n $Namespace"
