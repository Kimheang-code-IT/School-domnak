# Kubernetes manifests (Docker Desktop)

Namespace: `schooldomnak`

## Images (GHCR)

- `ghcr.io/kimheang-code-it/schooldomnak-backend:latest`
- `ghcr.io/kimheang-code-it/schooldomnak-frontend:latest`
- `ghcr.io/kimheang-code-it/schooldomnak-celery-worker:latest`
- `ghcr.io/kimheang-code-it/schooldomnak-celery-beat:latest`
- `ghcr.io/kimheang-code-it/schooldomnak-telegram-bot:latest`

Stock images: `postgres:16-alpine`, `redis:7-alpine`, `nginx:1.27-alpine`

## Exposure

| Service | Type | Exposed outside cluster |
|---------|------|-------------------------|
| school-nginx | LoadBalancer | **Yes** (app entry point) |
| school-backend | ClusterIP | No |
| school-frontend | ClusterIP | No |
| school-postgres | ClusterIP | No |
| school-redis | ClusterIP | No |
| celery / telegram | — | No (Deployments only) |

## One-time setup

1. Enable Kubernetes in Docker Desktop.
2. Create secret (never commit real values):

```bash
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl create secret generic school-secrets -n schooldomnak --from-env-file=.env
```

See `secret.example.yaml` for required keys.

3. Install and run a **self-hosted GitHub Actions runner** on the same machine (see root `README.md`).

## Manual apply (optional)

```bash
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl apply -f deploy/kubernetes/configmap.yaml
kubectl apply -f deploy/kubernetes/postgres/
kubectl apply -f deploy/kubernetes/redis/
kubectl apply -f deploy/kubernetes/backend/
kubectl apply -f deploy/kubernetes/frontend/
kubectl apply -f deploy/kubernetes/celery/
kubectl apply -f deploy/kubernetes/telegram/
kubectl apply -f deploy/kubernetes/nginx/
```

## Auto deploy

Push to `main` → GHCR publish → **SchoolDomnak K8s Local Deploy** workflow on self-hosted runner.
