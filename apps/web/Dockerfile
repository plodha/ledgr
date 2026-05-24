# apps/web/Dockerfile — multi-stage build for Next.js 16 production runtime.
# Stage 1 (deps): install dependencies into a deterministic layer.
# Stage 2 (builder): produce .next build artifacts.
# Stage 3 (runner): minimal runtime image containing only the runnable bundle.
#
# Build context expected: repo root (so `apps/web/...` and shared workspace
# files are reachable). docker-compose in Plan 05 will set context: .. and
# dockerfile: apps/web/Dockerfile accordingly.

FROM node:22-alpine AS deps
WORKDIR /app
RUN corepack enable pnpm
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:22-alpine AS builder
WORKDIR /app
RUN corepack enable pnpm
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web ./
RUN pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN corepack enable pnpm
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["pnpm", "start"]
