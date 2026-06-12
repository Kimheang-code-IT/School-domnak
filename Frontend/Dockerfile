# Optional: build static frontend for Nginx (output -> Frontend/dist)
FROM node:22-alpine AS build

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

ENV NUXT_PUBLIC_API_BASE=/api
ENV NUXT_PUBLIC_USE_BACKEND_API=true
ENV VITE_API_BASE_URL=/api

RUN pnpm run generate \
    && mkdir -p dist \
    && cp -r .output/public/. dist/

FROM scratch AS export
COPY --from=build /app/dist /dist
