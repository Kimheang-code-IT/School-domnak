# Production web image: Nuxt static assets + Nginx reverse proxy (for Docker Compose and Kubernetes)
FROM node:22-bookworm-slim AS frontend-build

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable

COPY Frontend/package.json Frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY Frontend/ .

ENV NODE_ENV=production \
    NUXT_TELEMETRY_DISABLED=1 \
    NUXT_DEVTOOLS_ENABLED=false \
    NODE_OPTIONS=--max-old-space-size=4096 \
    NUXT_PUBLIC_API_BASE=/api \
    NUXT_PUBLIC_USE_BACKEND_API=true \
    VITE_API_BASE_URL=/api

RUN pnpm run build

FROM nginx:1.27-alpine

COPY nginx/conf.d/app.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /app/.output/public /usr/share/nginx/html

RUN mkdir -p /app/uploads

EXPOSE 80
