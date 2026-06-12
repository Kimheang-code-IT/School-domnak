# Build static Nuxt app (default target: runtime on port 3000 for K3s)
FROM node:22-bookworm-slim AS build

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

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

FROM node:22-bookworm-slim AS runtime

WORKDIR /app

RUN npm install -g serve@14

COPY --from=build /app/.output/public ./public

EXPOSE 3000

CMD ["serve", "public", "-l", "3000"]

# Optional: export static files only (Docker Compose / Nginx volume)
FROM scratch AS export
COPY --from=build /app/.output/public /dist
