# Build static Nuxt for Nginx. Compose copies .output/public into the frontend_dist volume.
# Optional host export: docker build -f Frontend/Dockerfile --output type=local,dest=Frontend/dist Frontend
FROM node:22-alpine AS build

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

ENV NUXT_PUBLIC_API_BASE=/api
ENV NUXT_PUBLIC_USE_BACKEND_API=true
ENV VITE_API_BASE_URL=/api

RUN pnpm run generate

FROM scratch AS export
# Export static files at image root so `docker build --output dest=Frontend/dist`
# places index.html directly in Frontend/dist (not Frontend/dist/dist).
COPY --from=build /app/.output/public /
