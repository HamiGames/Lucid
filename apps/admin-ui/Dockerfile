# Multi-stage build for distroless admin UI
FROM node:20-slim AS builder

WORKDIR /build

# Copy package files
COPY package*.json ./
COPY next.config.js ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY src/ ./src/
COPY public/ ./public/
COPY tsconfig.json ./
COPY tailwind.config.js ./
COPY postcss.config.js ./

# Build the application
RUN npm run build

# Production stage - distroless
FROM gcr.io/distroless/nodejs20-debian12

# Copy built application
COPY --from=builder --chown=nonroot:nonroot /build/.next/standalone ./
COPY --from=builder --chown=nonroot:nonroot /build/.next/static ./.next/static
COPY --from=builder --chown=nonroot:nonroot /build/public ./public

# Set user and working directory
USER nonroot
WORKDIR /app

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["node", "-e", "require('http').get('http://localhost:3000/api/health', (res) => process.exit(res.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"]

# Start the application
CMD ["server.js"]
