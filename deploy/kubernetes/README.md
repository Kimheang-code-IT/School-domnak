# Kubernetes manifests (Docker Desktop)

Namespace: **`schooldomnak`**

## Structure

```
deploy/kubernetes/
├── namespace.yaml
├── configmap.yaml
├── secret.example.yaml
├── postgres/
├── redis/
├── backend/
├── frontend/
├── celery/
├── telegram/
└── nginx/
```

## Images (GHCR)

| Deployment | Image |
|------------|--------|
| school-backend | `ghcr.io/kimheang-code-it/schooldomnak-backend:latest` |
| school-frontend | `ghcr.io/kimheang-code-it/schooldomnak-frontend:latest` |
| school-celery-worker | `ghcr.io/kimheang-code-it/schooldomnak-celery-worker:latest` |
| school-celery-beat | `ghcr.io/kimheang-code-it/schooldomnak-celery-beat:latest` |
| school-telegram-bot | `ghcr.io/kimheang-code-it/schooldomnak-telegram-bot:latest` |

Stock: `postgres:16-alpine`, `redis:7-alpine`, `nginx:1.27-alpine`

## Services

| Name | Type | Exposed |
|------|------|---------|
| school-nginx | LoadBalancer | **Yes** |
| school-backend | ClusterIP | No |
| school-frontend | ClusterIP | No |
| school-postgres | ClusterIP | No |
| school-redis | ClusterIP | No |

Celery and Telegram: Deployment only (no Service).

## One-time secret

```bash
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl create secret generic school-secrets -n schooldomnak --from-env-file=.env
```

Auto deploy: push to `main` → GHCR publish → self-hosted `k8s-local-deploy.yml`.
