# Optional: build static frontend for Nginx (output -> Frontend/dist)
FROM node:22-bookworm-slim AS build

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

ENV NODE_ENV=production \
    NUXT_TELEMETRY_DISABLED=1 \
    NUXT_DEVTOOLS_ENABLED=false \
    NODE_OPTIONS=--max-old-space-size=4096 \
    NUXT_PUBLIC_API_BASE=/api \
    NUXT_PUBLIC_USE_BACKEND_API=true \
    VITE_API_BASE_URL=/api

# `nuxt build` matches CI and outputs static files to .output/public (nitro preset: static)
RUN pnpm run build \
    && mkdir -p dist \
    && cp -r .output/public/. dist/

FROM scratch AS export
COPY --from=build /app/dist /dist
