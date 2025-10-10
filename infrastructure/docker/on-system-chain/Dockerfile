# On-System Chain Docker Image
# EVM-compatible blockchain container for Lucid session anchoring
# Supports LucidAnchors and LucidChunkStore smart contracts

# Multi-stage build for optimized image size
FROM node:18-alpine AS base

# Install system dependencies
RUN apk add --no-cache \
    git \
    python3 \
    make \
    g++ \
    openssl-dev \
    libc-dev \
    curl \
    jq

# Set working directory
WORKDIR /app

# ============================================================================
# Stage 1: Build Dependencies
# ============================================================================
FROM base AS dependencies

# Copy package files
COPY package*.json ./
COPY yarn.lock* ./

# Install Node.js dependencies
RUN yarn install --frozen-lockfile --production=false

# ============================================================================
# Stage 2: Build Ethereum Client
# ============================================================================
FROM dependencies AS builder

# Clone and build Geth (Ethereum client)
RUN git clone https://github.com/ethereum/go-ethereum.git /tmp/go-ethereum && \
    cd /tmp/go-ethereum && \
    git checkout v1.13.0 && \
    make geth && \
    cp build/bin/geth /usr/local/bin/ && \
    rm -rf /tmp/go-ethereum

# Build smart contract deployment tools
COPY contracts/ ./contracts/
RUN yarn build:contracts

# ============================================================================
# Stage 3: Runtime Image
# ============================================================================
FROM alpine:3.18 AS runtime

# Install runtime dependencies
RUN apk add --no-cache \
    nodejs \
    npm \
    curl \
    jq \
    openssl \
    ca-certificates \
    tzdata

# Create non-root user
RUN addgroup -g 1001 -S onchain && \
    adduser -u 1001 -S onchain -G onchain

# Set working directory
WORKDIR /app

# Copy built artifacts from builder stage
COPY --from=builder /usr/local/bin/geth /usr/local/bin/
COPY --from=builder /app/dist/ ./dist/
COPY --from=builder /app/node_modules/ ./node_modules/
COPY --from=builder /app/package*.json ./

# Copy configuration files
COPY configs/on-system-chain/ ./configs/
COPY scripts/on-system-chain/ ./scripts/

# Create data directories
RUN mkdir -p /app/data/chaindata /app/data/keystore /app/logs && \
    chown -R onchain:onchain /app

# Set permissions
RUN chmod +x /usr/local/bin/geth && \
    chmod +x ./scripts/*.sh

# Switch to non-root user
USER onchain

# Expose ports
EXPOSE 8545 8546 30303 30303/udp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8545 -X POST \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
        || exit 1

# Default command
CMD ["./scripts/start-on-system-chain.sh"]

# ============================================================================
# Stage 4: Development Image (optional)
# ============================================================================
FROM runtime AS development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN apk add --no-cache \
    git \
    vim \
    htop \
    netcat-openbsd \
    tcpdump

# Install development Node.js packages
RUN npm install -g \
    truffle \
    ganache-cli \
    @remix-project/remixd

# Copy development scripts
COPY scripts/dev/ ./scripts/dev/

# Set development permissions
RUN chmod +x ./scripts/dev/*.sh

# Switch back to non-root user
USER onchain

# Development command
CMD ["./scripts/dev/start-dev-chain.sh"]

# ============================================================================
# Stage 5: Production Image (final)
# ============================================================================
FROM runtime AS final

# Copy production configuration
COPY --from=builder /app/configs/production/ ./configs/production/

# Set production environment variables
ENV NODE_ENV=production
ENV ON_SYSTEM_CHAIN_NETWORK=mainnet
ENV ON_SYSTEM_CHAIN_RPC_PORT=8545
ENV ON_SYSTEM_CHAIN_WS_PORT=8546
ENV ON_SYSTEM_CHAIN_P2P_PORT=30303

# Copy startup script
COPY scripts/production/start-production-chain.sh ./scripts/
RUN chmod +x ./scripts/start-production-chain.sh

# Production command
CMD ["./scripts/start-production-chain.sh"]

# Labels for metadata
LABEL maintainer="Lucid Team <team@lucid.com>"
LABEL description="On-System Chain EVM-compatible blockchain for Lucid session anchoring"
LABEL version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/HamiGames/Lucid"
LABEL org.opencontainers.image.licenses="MIT"
