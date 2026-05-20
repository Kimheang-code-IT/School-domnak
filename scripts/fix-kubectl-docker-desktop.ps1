# Point kubectl at Docker Desktop (run once per PowerShell session or add to profile).
$kubeConfig = Join-Path $env:USERPROFILE ".kube\config"
if (-not (Test-Path $kubeConfig)) {
    Write-Error "Kubeconfig not found. Enable Kubernetes in Docker Desktop first."
}
$env:KUBECONFIG = $kubeConfig
Write-Host "KUBECONFIG=$kubeConfig"
kubectl config current-context
kubectl get nodes
