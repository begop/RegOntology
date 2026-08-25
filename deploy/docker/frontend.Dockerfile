# syntax=docker/dockerfile:1.7
FROM node:24.15.0-alpine3.22 AS dependencies

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH

RUN corepack enable && corepack prepare pnpm@11.19.0 --activate

WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile

FROM dependencies AS test

COPY frontend/ ./
RUN pnpm typecheck \
    && pnpm test \
    && pnpm build

FROM dependencies AS build

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_DEMO_MODE=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_DEMO_MODE=$VITE_DEMO_MODE

COPY frontend/ ./
RUN pnpm build

FROM build AS nginx-assets

RUN rm -rf /app/frontend/dist/server /app/frontend/dist/.openai

FROM nginxinc/nginx-unprivileged:1.30.1-alpine3.23-slim AS runtime

ARG APP_VERSION=dev
ARG VCS_REF=unknown

LABEL org.opencontainers.image.title="RegOntology Web" \
      org.opencontainers.image.description="Regulation knowledge graph QA web application" \
      org.opencontainers.image.source="https://github.com/begop/RegOntology" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.version="$APP_VERSION"

COPY --chown=101:101 deploy/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=nginx-assets --chown=101:101 /app/frontend/dist/ /usr/share/nginx/html/

USER 101:101
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["wget", "--quiet", "--tries=1", "--spider", "http://127.0.0.1:8080/healthz"]
