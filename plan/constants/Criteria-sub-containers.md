# this file is to guide when checking for files, across the entire /Lucid Project

#**Directories to ignore**
##For file name searches related to prefixes ignore:
- `legacy_files/`
- `docs/`
- `.venv/`
- `.vscode/`
- `.unused_docs/`


# Use the following directories as the core alignment reference materials 
##**For files related to alignment USE:**
 - `plan/constants/`
 - `plan/disto`
 - `docs/archetecture`
 - `docs/verification/.verify/` 


# IGNORE the following directories as the core alignment reference materials 
## For files related to alignment Ignore:
- `docs/verification/.verify/.devcontainer/`

# Lucid YAML/YML Inventory
## Docker Compose – Service Scope
- `auth/docker-compose.yml`
- `sessions/docker-compose.yml`
- `RDP/docker-compose.yml`
- `node/docker-compose.yml`
- `03-api-gateway/docker-compose.yml`
- `admin/docker-compose.yml`
- `payment-systems/tron/docker-compose.yml`
- `docs/api/docker-compose.yml`
- `build/docker-compose.session-images.yml`
- `docker-compose.dev.yml`
- `docker-compose.pi.yml`
- `docker-compose.phase3.yml`

## Infrastructure Compose Bundles
- `infrastructure/compose/docker-compose.core.yaml`
- `infrastructure/compose/docker-compose.sessions.yaml`
- `infrastructure/compose/docker-compose.blockchain.yaml`
- `infrastructure/compose/docker-compose.payment-systems.yaml`
- `infrastructure/compose/docker-compose.integration.yaml`
- `infrastructure/compose/lucid-dev.yaml`

## Infrastructure/Docker Compose Variants
- `infrastructure/docker/compose/docker-compose.yml`
- `infrastructure/docker/compose/docker-compose.lucid-services.yml`
- `infrastructure/docker/compose/docker-compose.pi.yml`
- `infrastructure/docker/compose/docker-compose.prod.yml`
- `infrastructure/docker/compose/docker-compose.dev.yml`
- `infrastructure/docker/on-system-chain/docker-compose.yml`

## Distroless Profiles
- `configs/docker/distroless/distroless-config.yml`
- `configs/docker/distroless/distroless-runtime-config.yml`
- `configs/docker/distroless/distroless-development-config.yml`
- `configs/docker/distroless/distroless-security-config.yml`
- `configs/docker/distroless/test-runtime-config.yml`
- `infrastructure/docker/distroless/base/docker-compose.base.yml`

## Multi-stage Build Profiles
- `configs/docker/multi-stage/multi-stage-config.yml`
- `configs/docker/multi-stage/multi-stage-development-config.yml`
- `configs/docker/multi-stage/multi-stage-runtime-config.yml`
- `configs/docker/multi-stage/multi-stage-testing-config.yml`
- `configs/docker/multi-stage/multi-stage-build-config.yml`

## GUI / Packaging
- `configs/docker/docker-compose.gui-integration.yml`
- `electron-gui/electron-builder.yml`

## Service Configuration Manifests
- `configs/services/service-discovery.yml`
- `configs/services/session-management.yml`
- `configs/services/rdp-services.yml`
- `configs/services/node-management.yml`
- `configs/services/tron-payment.yml`
- `configs/services/database.yml`
- `configs/services/beta-sidecar.yml`
- `configs/services/auth-service.yml`
- `configs/services/blockchain-core.yml`
- `configs/services/api-gateway.yml`
- `configs/services/admin-interface.yml`
- `configs/services/gui-docker-manager.yml`
- `configs/services/gui-api-bridge.yml`

## Kubernetes Deployment Set
- `infrastructure/kubernetes/kustomization.yaml`
- `infrastructure/kubernetes/00-namespace.yaml`
- `infrastructure/kubernetes/01-configmaps/admin-interface-config.yaml`
- `infrastructure/kubernetes/01-configmaps/api-gateway-config.yaml`
- `infrastructure/kubernetes/01-configmaps/auth-service-config.yaml`
- `infrastructure/kubernetes/01-configmaps/blockchain-core-config.yaml`
- `infrastructure/kubernetes/01-configmaps/database-config.yaml`
- `infrastructure/kubernetes/01-configmaps/node-management-config.yaml`
- `infrastructure/kubernetes/01-configmaps/rdp-services-config.yaml`
- `infrastructure/kubernetes/01-configmaps/service-discovery-config.yaml`
- `infrastructure/kubernetes/01-configmaps/session-management-config.yaml`
- `infrastructure/kubernetes/01-configmaps/tron-payment-config.yaml`
- `infrastructure/kubernetes/02-secrets/jwt-secrets.yaml`
- `infrastructure/kubernetes/03-databases/elasticsearch.yaml`
- `infrastructure/kubernetes/03-databases/mongodb.yaml`
- `infrastructure/kubernetes/03-databases/redis.yaml`
- `infrastructure/kubernetes/04-auth/auth-service.yaml`
- `infrastructure/kubernetes/04-network/lucid-network-policies.yaml`
- `infrastructure/kubernetes/05-core/api-gateway.yaml`
- `infrastructure/kubernetes/05-core/blockchain-engine.yaml`
- `infrastructure/kubernetes/05-core/service-mesh.yaml`
- `infrastructure/kubernetes/06-application/node-management.yaml`
- `infrastructure/kubernetes/06-application/rdp-services.yaml`
- `infrastructure/kubernetes/06-application/session-management.yaml`
- `infrastructure/kubernetes/07-support/admin-interface.yaml`
- `infrastructure/kubernetes/07-support/tron-payment.yaml`
- `infrastructure/kubernetes/08-ingress/lucid-ingress.yaml`
- `infrastructure/kubernetes/patches/admin-interface-patch.yaml`
- `infrastructure/kubernetes/patches/api-gateway-patch.yaml`
- `infrastructure/kubernetes/patches/auth-service-patch.yaml`
- `infrastructure/kubernetes/patches/blockchain-engine-patch.yaml`
- `infrastructure/kubernetes/patches/node-management-patch.yaml`
- `infrastructure/kubernetes/patches/rdp-services-patch.yaml`
- `infrastructure/kubernetes/patches/service-mesh-controller-patch.yaml`
- `infrastructure/kubernetes/patches/session-management-patch.yaml`
- `infrastructure/kubernetes/patches/tron-payment-patch.yaml`

## Monitoring Stacks
- `ops/monitoring/prometheus.yml`
- `ops/monitoring/grafana/datasources.yml`
- `ops/monitoring/prometheus/prometheus.yml`
- `ops/monitoring/prometheus/alerts.yml`
- `ops/monitoring/lucid_rules.yml`
- `RDP/monitoring/prometheus.yml`
- `RDP/monitoring/grafana/datasources/prometheus.yml`
- `RDP/monitoring/alerts.yml`

## Service Mesh (Envoy Sidecar)
- `infrastructure/service-mesh/sidecar/envoy/config/bootstrap.yaml`
- `infrastructure/service-mesh/sidecar/envoy/config/cluster.yaml`
- `infrastructure/service-mesh/sidecar/envoy/config/listener.yaml`

## Build & Infrastructure Helpers
- `infrastructure/containers/base/build.config.yml`
- `infrastructure/containers/base/docker-compose.base.yml`
- `infrastructure/containers/storage/elasticsearch.yml`
- `configs/database/elasticsearch/elasticsearch.yml`
- `scripts/build/build-coordination.yml`
- `configs/integration/master-integration-config.yml`

## API/OpenAPI Specifications
- `docs/api/swagger-ui-config.yaml`
- `docs/api/openapi/api-gateway.yaml`
- `docs/api/openapi/auth-service.yaml`
- `docs/api/openapi/blockchain-core.yaml`
- `docs/api/openapi/admin-interface.yaml`
- `docs/api/openapi/node-management.yaml`
- `docs/api/openapi/rdp-services.yaml`
- `docs/api/openapi/session-management.yaml`
- `docs/api/openapi/tron-payment.yaml`
- `03-api-gateway/gateway/openapi.yaml`
- `03-api-gateway/gateway/openapi.override.yaml`
- `plan/API_plans/07-tron-payment-cluster/05_OPENAPI_SPEC.yaml`

## Cloud-init & Infrastructure Configs
- `ops/cloud-init/cloud-init.yml`
- `ops/cloud-init/lucid-gui-setup.yml`

## Other Utilities / Configs
- `.markdownlint.yaml`
- `configs/.pre-commit-config.yaml`
- `configs/.pre-comit-config.yaml`
- `configs/security/sbom-config.yml`
- `configs/logging/elasticsearch-logging.yml`
- `electron-gui/distroless/docker-compose.electron-gui.yml`

