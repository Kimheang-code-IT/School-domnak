# syntax=docker/dockerfile:1

# ── Dependencies (cached layer) ──────────────────────────────────────────────
FROM node:22-bookworm-slim AS deps

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && corepack enable

COPY package.json pnpm-lock.yaml ./

RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# ── Build static Nuxt output ─────────────────────────────────────────────────
FROM node:22-bookworm-slim AS build

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml ./
COPY --from=deps /app/node_modules ./node_modules

COPY . .

ARG NUXT_PUBLIC_API_BASE=http://localhost:30080/api/v1
ARG NUXT_PUBLIC_USE_BACKEND_API=true

ENV NODE_ENV=production \
    NUXT_TELEMETRY_DISABLED=1 \
    NUXT_DEVTOOLS_ENABLED=false \
    NODE_OPTIONS=--max-old-space-size=4096 \
    NUXT_PUBLIC_API_BASE=${NUXT_PUBLIC_API_BASE} \
    NUXT_PUBLIC_USE_BACKEND_API=${NUXT_PUBLIC_USE_BACKEND_API} \
    VITE_API_BASE_URL=${NUXT_PUBLIC_API_BASE}

RUN pnpm run build

# ── Optional: export static files only (Docker Compose / host Nginx volume) ──
FROM scratch AS export
COPY --from=build /app/.output/public /dist

# ── Runtime: Nginx serves static files on port 3000 (K3s / production) ───────
# Last stage = default build target (must have CMD for Kubernetes)
FROM nginx:1.27-alpine AS runtime

COPY nginx-k3s.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/.output/public /usr/share/nginx/html

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
