# this file contains the the names of the docker-compose files need in the /Lucid Project folders.

##*yaml & yml folders required per section*
##**Core production deployment (phase-based)**
'''
configs\docker\docker-compose.foundation.yml
configs\docker\docker-compose.core.yml
configs\docker\docker-compose.application.yml
configs\docker\docker-compose.support.yml
configs\docker\docker-compose.all.yml
'''
##**Individual service compose**
'''
auth\docker-compose.yml
sessions\docker-compose.yml
RDP\docker-compose.yml
node\docker-compose.yml
03-api-gateway\docker-compose.yml
admin\docker-compose.yml
payment-systems\tron\docker-compose.yml
'''
##**Infrastructure compose**
'''
infrastructure\compose\docker-compose.core.yaml
infrastructure\compose\docker-compose.sessions.yaml
infrastructure\compose\docker-compose.blockchain.yaml
infrastructure\compose\docker-compose.payment-systems.yaml
infrastructure\compose\docker-compose.integration.yaml
infrastructure\compose\lucid-dev.yaml
'''

##**Docker/compose**
'''
infrastructure\docker\compose\docker-compose.yml
infrastructure\docker\compose\docker-compose.lucid-services.yml
infrastructure\docker\compose\docker-compose.pi.yml
infrastructure\docker\compose\docker-compose.prod.yml
infrastructure\docker\compose\docker-compose.dev.yml
infrastructure\docker\on-system-chain\docker-compose.yml
Distroless
'''

##**Distroless**
'''
configs\docker\distroless\distroless-config.yml
configs\docker\distroless\distroless-runtime-config.yml
configs\docker\distroless\distroless-development-config.yml
configs\docker\distroless\distroless-security-config.yml
configs\docker\distroless\test-runtime-config.yml
infrastructure\docker\distroless\base\docker-compose.base.yml
'''

##**Multi-stage**
'''
configs\docker\multi-stage\multi-stage-config.yml
configs\docker\multi-stage\multi-stage-development-config.yml
configs\docker\multi-stage\multi-stage-runtime-config.yml
configs\docker\multi-stage\multi-stage-testing-config.yml
configs\docker\multi-stage\multi-stage-build-config.yml
'''

##**GUI**
'''
configs\docker\docker-compose.gui-integration.yml

electron-gui\electron-builder.yml
'''

##**Service configs**
'''
configs\services\service-discovery.yml
configs\services\session-management.yml
configs\services\rdp-services.yml
configs\services\node-management.yml
configs\services\tron-payment.yml
configs\services\database.yml
configs\services\beta-sidecar.yml
configs\services\auth-service.yml
configs\services\blockchain-core.yml
configs\services\api-gateway.yml
configs\services\admin-interface.yml
configs\services\gui-docker-manager.yml
configs\services\gui-api-bridge.yml
'''

##**Kubernetes**
'''
infrastructure\kubernetes\kustomization.yaml
infrastructure\kubernetes\00-namespace.yaml
'''

##**Monitoring**
'''
ops\monitoring\prometheus.yml
ops\monitoring\grafana\datasources.yml
ops\monitoring\prometheus\prometheus.yml
ops\monitoring\prometheus\alerts.yml
ops\monitoring\lucid_rules.yml
RDP\monitoring\prometheus.yml
RDP\monitoring\grafana\datasources\prometheus.yml
RDP\monitoring\alerts.yml
'''

##**Service mesh**
'''
infrastructure\service-mesh\sidecar\envoy\config\cluster.yaml
infrastructure\service-mesh\sidecar\envoy\config\listener.yaml
infrastructure\service-mesh\sidecar\envoy\config\bootstrap.yaml
'''

##**Build & infra**
'''
infrastructure\containers\base\docker-compose.base.yml
infrastructure\containers\base\build.config.yml
infrastructure\containers\storage\elasticsearch.yml
configs\database\elasticsearch\elasticsearch.yml
scripts\build\build-coordination.yml
'''

##**API/OpenAPI**
'''
docs\api\swagger-ui-config.yaml
docs\api\openapi\auth-service.yaml
docs\api\openapi\tron-payment.yaml
docs\api\openapi\admin-interface.yaml
docs\api\openapi\node-management.yaml
docs\api\openapi\rdp-services.yaml
docs\api\openapi\session-management.yaml
docs\api\openapi\blockchain-core.yaml
docs\api\openapi\api-gateway.yaml
03-api-gateway\gateway\openapi.yaml
03-api-gateway\gateway\openapi.override.yaml
plan\API_plans\07-tron-payment-cluster\05_OPENAPI_SPEC.yaml
docs\api\docker-compose.yml
'''

##**Development**
'''
docker-compose.dev.yml
docker-compose.pi.yml
docker-compose.phase3.yml
configs\integration\master-integration-config.yml
'''



##**Utilities**
'''
.markdownlint.yaml
configs\.pre-commit-config.yaml
configs\.pre-comit-config.yaml
'''