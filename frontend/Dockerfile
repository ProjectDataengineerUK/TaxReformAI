# Build context: frontend/ (self-contido). Rodar sempre como:
#   docker build -f frontend/Dockerfile -t <tag> frontend/
#
# NEXT_PUBLIC_API_BASE_URL e lida em build time (frontend/lib/api-client.ts) e
# fica embutida no bundle JS gerado - precisa ser passada como --build-arg com
# a URL real do servico Cloud Run da API antes de buildar o frontend.

# --- deps: instala dependencias isoladas para melhor cache de camadas ---
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- builder: compila o Next.js em modo standalone ---
FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# --- runner: imagem final minima, so com o output standalone ---
FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=8080 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 8080

CMD ["node", "server.js"]
