# Required Environment Files (.env.*) for Lucid Project

This document lists all `.env.*` files required by containers and services in the Lucid project. These files must exist in `/mnt/myssd/Lucid/Lucid/configs/environment/` (or service-specific directories as noted) for proper container deployment.

**Last Updated:** 2025-11-28  
**Total Required Files:** 40

---

## Core Phase Environment Files

These files are used across multiple services and phases:

| File Name | Purpose | Permission | Required By |
|-----------|---------|------------|-------------|
| `.env.foundation` | Phase 1: Foundation services (MongoDB, Redis, Elasticsearch, Auth) | 664 | All foundation services |
| `.env.core` | Phase 2: Core services | 664 | Core services, blockchain services |
| `.env.application` | Phase 3: Application services | 664 | Application services, session services |
| `.env.support` | Phase 4: Support services | 664 | Support services, RDP, payment systems |
| `.env.gui` | GUI integration services | 664 | GUI services |
| `.env.distroless` | Distroless-specific configuration | 664 | All distroless containers |
| `.env.secrets` | **Master secrets file** (passwords, keys, tokens) | **600** | All services (via docker-compose) |
| `.env.secure` | Master backup of secrets | **600** | Backup/restore operations |
| `.env.pi-build` | Raspberry Pi build configuration | 664 | Build scripts |

---

## Foundation Services Environment Files

| File Name | Purpose | Permission | Required By |
|-----------|---------|------------|-------------|
| `.env.tor-proxy` | Tor proxy service configuration | 664 | `tor-proxy` container |
| `.env.server-tools` | Server tools service | 664 | `lucid-server-tools` container |
| `.env.authentication` | Authentication service | 664 | `lucid-auth-service` container |
| `.env.authentication-service-distroless` | Auth service (distroless variant) | 664 | Auth service distroless build |

---

## API & Gateway Services Environment Files

| File Name | Purpose | Permission | Required By |
|-----------|---------|------------|-------------|
| `.env.api-gateway` | API Gateway service | 664 | API Gateway container |
| `.env.api-server` | API Server service | 664 | API Server container |
| `.env.openapi-gateway` | OpenAPI Gateway service | 664 | OpenAPI Gateway container |
| `.env.openapi-server` | OpenAPI Server service | 664 | OpenAPI Server container |
| `.env.api` | API service (local) | 664 | `03-api-gateway/api/` directory |

---

## Blockchain Services Environment Files

| File Name | Purpose | Permission | Required By |
|-----------|---------|------------|-------------|
| `.env.blockchain-api` | Blockchain API service | 664 | Blockchain API container |
| `.env.blockchain-governance` | Blockchain governance service | 664 | Blockchain governance container |
| `.env.blockchain-sessions-data` | Blockchain sessions data service | 664 | Blockchain sessions container |
| `.env.blockchain-vm` | Blockchain VM service | 664 | Blockchain VM container |
| `.env.blockchain-ledger` | Blockchain ledger service | 664 | Blockchain ledger container |
| `.env.tron-node-client` | TRON node client | 664 | TRON node client container |
| `.env.contract-deployment` | Contract deployment service | 664 | Contract deployment container |
| `.env.contract-compiler` | Contract compiler service | 664 | Contract compiler container |
| `.env.on-system-chain-client` | On-system chain client | 664 | On-system chain client container |
| `.env.deployment-orchestrator` | Deployment orchestrator | 664 | Deployment orchestrator container |

**Note:** Some blockchain env files may be located in `infrastructure/docker/blockchain/env/` directory.

---

## Session Services Environment Files

**Location:** `sessions/core/` directory

| File Name | Purpose | Permission | Required By |
|-----------|---------|------------|-------------|
| `.env.chunker` | Session chunker service | 664 | Session chunker container |
| `.env.merkle_builder` | Merkle builder service | 664 | Merkle builder container |
| `.env.orchestrator` | Session orchestrator service | 664 | Session orchestrator container |
| `.env.encryptor` | Session encryptor service | 664 | Session encryptor container (in `sessions/encryption/`) |

---

## TRON Payment Services Environment Files

| File Name | Purpose | Permission | Required By |
|-----------|---------|------------|-------------|
| `.env.tron-client` | TRON client service | 664 | TRON client container |
| `.env.tron-payout-router` | TRON payout router | 664 | TRON payout router container |
| `.env.tron-wallet-manager` | TRON wallet manager | 664 | TRON wallet manager container |
| `.env.tron-usdt-manager` | TRON USDT manager | 664 | TRON USDT manager container |
| `.env.tron-staking` | TRON staking service | 664 | TRON staking container |
| `.env.tron-payment-gateway` | TRON payment gateway | 664 | TRON payment gateway container |
| `.env.tron-secrets` | TRON-specific secrets | **600** | All TRON services |

---

## Node & Admin Services Environment Files

| File Name | Purpose | Permission | Required By |
|-----------|---------|------------|-------------|
| `.env.node` | Node management service | 664 | Node management container |

---

## File Locations

### Primary Location