# Kubernetes manifests — Hostinger VPS + K3s

**Full manual setup:** [docs/VPS-MANUAL-SETUP.md](../docs/VPS-MANUAL-SETUP.md)  
No shell scripts — only `kubectl`, `nginx`, and `openssl` commands.

---

## Architecture

```
Browser → Ubuntu nginx :443 (school.72-62-250-194.sslip.io)
            ├── /        → frontend NodePort 30000
            └── /api/    → backend NodePort 30080

Backend → postgres:5432 + redis:6379 (inside K3s)
DBeaver → VPS:30432 → postgres
```

| Component | NodePort |
|-----------|----------|
| Frontend `devops-app` | 30000 |
| Backend | 30080 |
| PostgreSQL | 30432 |

---

## Files

| File | Purpose |
|------|---------|
| `namespace.yaml` | Namespace `devops-lab` |
| `postgres.yaml` | PostgreSQL + PVC |
| `redis.yaml` | Redis |
| `backend.yaml` | FastAPI backend |
| `deployment.yaml` | Frontend |
| `service.yaml` | Frontend NodePort |
| `secret.example.yaml` | Template → copy to `secret.yaml` on VPS |

Also copy `nginx/host-k3s-proxy.conf` to VPS for HTTPS.

---

## Quick start (summary)

1. **Windows:** `scp` `k8s/*` + `nginx/host-k3s-proxy.conf` to `/opt/devops-runtime/`
2. **VPS:** edit `secret.yaml`, `kubectl apply`
3. **VPS:** apply manifests, GHCR secret, SSL, nginx
4. **GitHub:** push `devops-lab` for CD deploy

See [docs/VPS-MANUAL-SETUP.md](../docs/VPS-MANUAL-SETUP.md) for every command.

---

## CD workflow

[`.github/workflows/cd-k3s.yml`](../.github/workflows/cd-k3s.yml) — SSH + inline `kubectl` (no scripts on VPS).

---

## Fix backend CrashLoopBackOff (`$@postgres`)

`DATABASE_URL` password must match `POSTGRES_PASSWORD`. Encode special chars:

```bash
python3 -c "from urllib.parse import quote_plus; print(quote_plus('YOUR_PASSWORD'))"
```

Use encoded value in `DATABASE_URL` only.
