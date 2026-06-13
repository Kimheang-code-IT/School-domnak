# K3s on Hostinger VPS

**All setup is manual — no `.sh` scripts on the VPS.**

→ **[VPS-MANUAL-SETUP.md](./VPS-MANUAL-SETUP.md)** — complete step-by-step guide

---

## Summary

| Step | Where |
|------|--------|
| Copy `k8s/` + nginx config | Windows `scp` |
| Create `secret.yaml` | VPS `nano` + `kubectl apply` |
| Apply stack | VPS `kubectl apply` |
| SSL + nginx | VPS `openssl` + `nginx` |
| Deploy images | GitHub CD (push `devops-lab`) or manual `kubectl set image` |

Site: **https://school.72-62-250-194.sslip.io**

See also: [CI-CD.md](./CI-CD.md)
