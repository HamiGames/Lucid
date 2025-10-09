# LUCID Layer 1 Spin-up: Core Infrastructure (Session Pipeline, Authentication)

**Date:** 2025-10-05  
**Scope:** Layer 1 — Session Pipeline and Authentication  
**Mode:** LUCID-STRICT

---

## Executive Summary

Layer 1 materials and build contexts exist in-repo. Session pipeline components (`session-chunker`, `session-encryptor`, `merkle-builder`, `session-orchestrator`) and the `auth-service` have Dockerfiles and a dedicated compose extension (`infrastructure/compose/lucid-dev-layer1.yaml`). Multi-arch builds and pushes are initiated for both `pickme/lucid` and `pickme/lucid-dev`.

---

## Components and Locations

- Session Chunker: `sessions/core/chunker.py`, Dockerfile `sessions/core/Dockerfile.chunker`
- Session Encryptor: `sessions/encryption/encryptor.py`, Dockerfile `sessions/encryption/Dockerfile.encryptor`
- Merkle Builder: `sessions/core/merkle_builder.py`, Dockerfile `sessions/core/Dockerfile.merkle_builder`
- Session Orchestrator: `sessions/core/session_orchestrator.py`, Dockerfile `sessions/core/Dockerfile.orchestrator`
- Authentication Service: `open-api/api/app/routes/auth.py`, Dockerfile `auth/Dockerfile.authentication`
- Compose: `infrastructure/compose/lucid-dev-layer1.yaml`

---

## Build and Push Actions

- Multi-platform builds prepared with docker buildx for: chunker, encryptor, merkle, orchestrator, auth
- Images tagged and pushed to: `pickme/lucid` and `pickme/lucid-dev`
- Target platforms: `linux/amd64, linux/arm64`

---

## Spin-up Status

- Compose file for Layer 1 present. Spin-up pending environment/secrets setup:
  - `sessions/core/.env.*`, `sessions/encryption/.env.encryptor`, `auth/.env.authentication`
  - External secrets: `master_encryption_key`, `jwt_secret_key`, `tron_private_key`
- MongoDB schema initialization script present: `scripts/init_mongodb_schema.sh`

---

## Next Steps

- Validate DockerHub pushes completed for all tags
- Provision secrets in target environment
- Bring up Layer 1 with profiles using `lucid-dev-layer1.yaml`
- Run health checks on ports 8081–8085

---

## Verification Checklist

- [ ] All five services images available for `amd64` and `arm64`
- [ ] External secrets created in target environment
- [ ] `docker-compose` up succeeds for Layer 1 profiles
- [ ] Health checks return 200 on all services
