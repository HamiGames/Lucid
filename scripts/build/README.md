# Lucid Build Scripts

This directory contains the build and push scripts for the Lucid RDP system Docker containers. The scripts are organized by phases and implement the complete Docker build process as specified in the `docker-build-process-plan.md`.

## Scripts Overview

### Master Orchestration
- **`master-build-orchestration.sh`** - Runs all phases in sequence with comprehensive error handling and progress tracking

### Individual Phase Scripts
- **`pre-build-phase.sh`** - Pre-Build Phase (Steps 1-4): Environment setup, base images
- **`phase1-foundation-services.sh`** - Phase 1 (Steps 5-9): Foundation Services (MongoDB, Redis, Elasticsearch, Auth)
- **`phase2-core-services.sh`** - Phase 2 (Steps 10-17): Core Services (API Gateway, Service Mesh, Blockchain)
- **`phase3-application-services.sh`** - Phase 3 (Steps 18-27): Application Services (Sessions, RDP, Node Management)
- **`phase4-support-services.sh`** - Phase 4 (Steps 28-35): Support Services (Admin Interface, TRON Payment)

## Usage

### Run All Phases (Recommended)
```bash
./scripts/build/master-build-orchestration.sh
```

### Run Individual Phases
```bash
# Pre-Build Phase
./scripts/build/pre-build-phase.sh

# Phase 1: Foundation Services
./scripts/build/phase1-foundation-services.sh

# Phase 2: Core Services
./scripts/build/phase2-core-services.sh

# Phase 3: Application Services
./scripts/build/phase3-application-services.sh

# Phase 4: Support Services
./scripts/build/phase4-support-services.sh
```

### Command Line Options
All scripts support the following options:
```bash
--platform PLATFORM    Target platform (default: linux/arm64)
--registry REGISTRY     Registry name (default: pickme/lucid)
--tag TAG              Image tag (default: latest)
--help                 Show help message
```

## Prerequisites

### System Requirements
- Docker Desktop with BuildKit enabled
- Docker Hub account with credentials configured
- 20GB+ free disk space
- Stable internet connection

### Environment Setup
The scripts automatically:
1. Generate environment configuration files using `scripts/config/generate-all-env.sh`
2. Create necessary directories and validate prerequisites
3. Setup Docker Buildx builder for ARM64 platform
4. Load environment variables from generated `.env` files

## Build Process

### Phase Dependencies
Each phase depends on the previous phase being completed:
- **Pre-Build** → **Phase 1** → **Phase 2** → **Phase 3** → **Phase 4**

### Container Images Built
The scripts build and push the following container images to Docker Hub:

#### Pre-Build Phase
- `pickme/lucid/lucid-base:python-distroless-arm64`
- `pickme/lucid/lucid-base:java-distroless-arm64`

#### Phase 1: Foundation Services
- `pickme/lucid/lucid-mongodb:latest-arm64`
- `pickme/lucid/lucid-redis:latest-arm64`
- `pickme/lucid/lucid-elasticsearch:latest-arm64`
- `pickme/lucid/lucid-auth-service:latest-arm64`

#### Phase 2: Core Services
- `pickme/lucid/lucid-api-gateway:latest-arm64`
- `pickme/lucid/lucid-service-mesh-controller:latest-arm64`
- `pickme/lucid/lucid-blockchain-engine:latest-arm64`
- `pickme/lucid/lucid-session-anchoring:latest-arm64`
- `pickme/lucid/lucid-block-manager:latest-arm64`
- `pickme/lucid/lucid-data-chain:latest-arm64`

#### Phase 3: Application Services
- `pickme/lucid/lucid-session-pipeline:latest-arm64`
- `pickme/lucid/lucid-session-recorder:latest-arm64`
- `pickme/lucid/lucid-chunk-processor:latest-arm64`
- `pickme/lucid/lucid-session-storage:latest-arm64`
- `pickme/lucid/lucid-session-api:latest-arm64`
- `pickme/lucid/lucid-rdp-server-manager:latest-arm64`
- `pickme/lucid/lucid-xrdp-integration:latest-arm64`
- `pickme/lucid/lucid-session-controller:latest-arm64`
- `pickme/lucid/lucid-resource-monitor:latest-arm64`
- `pickme/lucid/lucid-node-management:latest-arm64`

#### Phase 4: Support Services
- `pickme/lucid/lucid-admin-interface:latest-arm64`
- `pickme/lucid/lucid-tron-client:latest-arm64`
- `pickme/lucid/lucid-payout-router:latest-arm64`
- `pickme/lucid/lucid-wallet-manager:latest-arm64`
- `pickme/lucid/lucid-usdt-manager:latest-arm64`
- `pickme/lucid/lucid-trx-staking:latest-arm64`
- `pickme/lucid/lucid-payment-gateway:latest-arm64`

## Features

### Error Handling
- Comprehensive error handling with detailed logging
- Build failure recovery and user prompts
- Image existence checking to avoid duplicate builds
- Push verification to ensure images are available in registry

### Security
- TRON isolation verification in Phase 2
- Distroless container builds for minimal attack surface
- Non-root user execution
- Secure environment variable handling

### Monitoring
- Real-time build progress tracking
- Detailed build logs in `build/logs/`
- Build duration and performance metrics
- Success/failure reporting with actionable next steps

### Integration
- Automatic Docker Compose file generation
- Deployment script preparation
- Integration test script creation
- Performance benchmark setup

## File Structure

```
scripts/build/
├── README.md                           # This file
├── master-build-orchestration.sh       # Master orchestration script
├── pre-build-phase.sh                  # Pre-Build phase script
├── phase1-foundation-services.sh       # Phase 1 script
├── phase2-core-services.sh             # Phase 2 script
├── phase3-application-services.sh      # Phase 3 script
└── phase4-support-services.sh          # Phase 4 script
```

## Output Files

### Build Logs
- Location: `build/logs/`
- Format: `{service-name}-build.log`
- Content: Detailed build output and error messages

### Docker Compose Files
- `configs/docker/docker-compose.foundation.yml` - Phase 1 services
- `configs/docker/docker-compose.core.yml` - Phase 2 services
- `configs/docker/docker-compose.application.yml` - Phase 3 services
- `configs/docker/docker-compose.support.yml` - Phase 4 services
- `configs/docker/docker-compose.master.yml` - All services consolidated

### Deployment Scripts
- `scripts/deployment/deploy-phase1-pi.sh` - Phase 1 deployment
- `scripts/deployment/deploy-phase2-pi.sh` - Phase 2 deployment
- `scripts/deployment/deploy-phase3-pi.sh` - Phase 3 deployment
- `scripts/deployment/deploy-phase4-pi.sh` - Phase 4 deployment

### Test Scripts
- `tests/integration/phase1/run_phase1_tests.sh` - Phase 1 integration tests
- `tests/integration/phase2/run_phase2_tests.sh` - Phase 2 integration tests
- `tests/integration/phase3/run_phase3_tests.sh` - Phase 3 integration tests
- `tests/integration/phase4/run_phase4_tests.sh` - Phase 4 integration tests
- `tests/integration/final/run_final_integration_test.sh` - Final system test

## Troubleshooting

### Common Issues

#### Docker Buildx Not Available
```bash
# Create and use a new builder
docker buildx create --name lucid-pi-builder --use
docker buildx inspect --bootstrap
```

#### Docker Hub Authentication
```bash
# Login to Docker Hub
docker login
```

#### Insufficient Disk Space
```bash
# Clean up Docker system
docker system prune -a -f
docker builder prune -a -f
```

#### Build Failures
1. Check build logs in `build/logs/`
2. Verify Dockerfile paths and context directories
3. Ensure all dependencies are available
4. Check Docker Hub connectivity

### Getting Help
- Check individual script help: `./script-name.sh --help`
- Review build logs for detailed error messages
- Verify prerequisites and environment setup

## Next Steps

After successful build completion:
1. Deploy to Raspberry Pi using deployment scripts
2. Run integration tests to verify functionality
3. Execute performance benchmarks
4. Use master Docker Compose for production deployment

## Compliance

All scripts implement the requirements from:
- `docker-build-process-plan.md`
- `docker-build-process.plan.md`
- API build progress documentation
- Distroless container architecture specifications
- TRON isolation requirements