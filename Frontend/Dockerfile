# ---------- dependencies ----------
FROM node:20-slim AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci


# ---------- dev ----------
# Used by docker-compose.yml (local development) via `target: dev`. Keeps the
# full toolchain and the Next dev server, since that compose file bind-mounts
# the source tree over /app and expects hot reload.
FROM node:20-slim AS dev

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]


# ---------- build ----------
FROM node:20-slim AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* values are inlined into the client bundle at build time, so they
# must arrive as build args. Changing either one requires a rebuild, not a
# restart. CAREERS_ORG_SLUG must match the backend's DEFAULT_ORG_SLUG.
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_CAREERS_ORG_SLUG=peer-consulting
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL} \
    NEXT_PUBLIC_CAREERS_ORG_SLUG=${NEXT_PUBLIC_CAREERS_ORG_SLUG} \
    NEXT_TELEMETRY_DISABLED=1

RUN test -n "$NEXT_PUBLIC_API_BASE_URL" \
    || (echo "ERROR: NEXT_PUBLIC_API_BASE_URL build arg is required." \
        && echo "It is baked into the bundle; without it the app calls localhost." && exit 1)

RUN npm run build


# ---------- runtime ----------
FROM node:20-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 nextjs

# The standalone output carries its own minimal server plus traced dependencies.
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nextjs /app/public ./public

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:3000/ || exit 1

CMD ["node", "server.js"]
