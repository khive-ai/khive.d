# Multi-stage Docker build for Ocean's Agentic ERP Command Center Frontend
# Optimized for performance and security with minimal attack surface

# Stage 1: Base dependencies
FROM node:20-alpine AS base
WORKDIR /app

# Install dependencies only for production
RUN apk add --no-cache libc6-compat curl
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Stage 2: Dependencies installation
FROM base AS deps
WORKDIR /app

# Copy package files for dependency resolution
COPY package.json package-lock.json* ./

# Install dependencies with npm ci for exact reproducible builds
RUN \
  if [ -f package-lock.json ]; then \
    npm ci --only=production --omit=dev && \
    npm cache clean --force; \
  else \
    echo "Lockfile not found." && exit 1; \
  fi

# Stage 3: Development dependencies (for build)
FROM base AS build-deps
WORKDIR /app

COPY package.json package-lock.json* ./
RUN \
  if [ -f package-lock.json ]; then \
    npm ci && \
    npm cache clean --force; \
  else \
    echo "Lockfile not found." && exit 1; \
  fi

# Stage 4: Application build
FROM build-deps AS builder
WORKDIR /app

# Copy all source files
COPY . .

# Generate Next.js telemetry ID but disable telemetry
RUN npx next telemetry disable

# Build the application with Next.js standalone output
ENV NEXT_OUTPUT=standalone
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN npm run build

# Stage 5: Production runner (minimal size)
FROM node:20-alpine AS runner
WORKDIR /app

# Install curl for health checks and security updates
RUN apk add --no-cache curl && \
    apk upgrade --no-cache

# Create nextjs user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application with proper ownership
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy package.json for metadata
COPY --from=builder /app/package.json ./package.json

# Create health check endpoint availability
RUN mkdir -p .next/server/pages/api && \
    chown -R nextjs:nodejs .next

# Switch to non-root user
USER nextjs

# Environment configuration
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

# Start the application
CMD ["node", "server.js"]