# Lucid Session Docker Images

This directory contains the build configurations and scripts for the Lucid Session management Docker images, specifically designed for ARM64 architecture (Raspberry Pi).

## Docker Images

The following Docker images are built and configured:

1. **Session Pipeline** (`pickme/lucid-session-pipeline:latest-arm64`)
   - Port: 8083
   - Purpose: Manages session processing pipeline with state machine
   - Dockerfile: `sessions/Dockerfile.pipeline`

2. **Session Recorder** (`pickme/lucid-session-recorder:latest-arm64`)
   - Port: 8084
   - Purpose: Records sessions with hardware acceleration for Pi 5
   - Dockerfile: `sessions/Dockerfile.recorder`

3. **Chunk Processor** (`pickme/lucid-chunk-processor:latest-arm64`)
   - Port: 8085
   - Purpose: Processes data chunks with compression and encryption
   - Dockerfile: `sessions/Dockerfile.processor`

4. **Session Storage** (`pickme/lucid-session-storage:latest-arm64`)
   - Port: 8086
   - Purpose: Manages session data storage and retrieval
   - Dockerfile: `sessions/Dockerfile.storage`

5. **Session API** (`pickme/lucid-session-api:latest-arm64`)
   - Port: 8087
   - Purpose: API gateway for session management services
   - Dockerfile: `sessions/Dockerfile.api`

## Build Scripts

### Individual Build Scripts

- `build/scripts/build-session-pipeline.sh` - Build Session Pipeline image
- `build/scripts/build-session-recorder.sh` - Build Session Recorder image
- `build/scripts/build-chunk-processor.sh` - Build Chunk Processor image
- `build/scripts/build-session-storage.sh` - Build Session Storage image
- `build/scripts/build-session-api.sh` - Build Session API image

### Master Build Script

- `build/scripts/build-all-session-images.sh` - Build all session images

## Usage

### Build All Images

```bash
# From project root
./build/scripts/build-all-session-images.sh
```

### Build Individual Image

```bash
# Example: Build Session Pipeline
./build/scripts/build-session-pipeline.sh
```

### Run with Docker Compose

```bash
# Start all session services
docker-compose -f build/docker-compose.session-images.yml up -d

# Stop all session services
docker-compose -f build/docker-compose.session-images.yml down
```

## Architecture

All images are built using:
- **Base**: Multi-stage distroless builds
- **Platform**: ARM64 (linux/arm64)
- **Python**: 3.11-slim builder, distroless runtime
- **Security**: Distroless base images for minimal attack surface

## Port Configuration

- Session Pipeline: 8083
- Session Recorder: 8084
- Chunk Processor: 8085
- Session Storage: 8086
- Session API: 8087

## Environment Variables

Each service supports the following environment variables:

- `SERVICE_NAME` - Service identifier
- `PORT` - Service port
- `HOST` - Bind host (default: 0.0.0.0)
- `LOG_LEVEL` - Logging level (INFO, DEBUG, etc.)
- `DEBUG` - Debug mode (true/false)
- `PYTHONPATH` - Python path
- `PYTHONUNBUFFERED` - Python output buffering

## Health Checks

All services include health checks that verify HTTP endpoints are responding correctly.

## Volumes

The Docker Compose configuration includes persistent volumes for:
- Session data
- Recording data
- Chunk data
- Processed data
- Storage data
- Log files

## Networks

All services are connected via the `lucid-session-network` bridge network for internal communication.

## Build Requirements

- Docker with buildx support
- ARM64 platform support (for cross-compilation)
- Sufficient disk space for multi-stage builds
- Network access for pulling base images

## Troubleshooting

### Build Issues

1. **Platform not supported**: Ensure Docker buildx is installed and configured
2. **Out of space**: Clean up Docker images and build cache
3. **Network issues**: Check internet connectivity for base image pulls

### Runtime Issues

1. **Port conflicts**: Ensure ports 8083-8087 are available
2. **Permission issues**: Check volume mount permissions
3. **Health check failures**: Verify service endpoints are responding

## Development

For development and testing:

```bash
# Build and test individual service
docker build --platform linux/arm64 -t test-session-pipeline -f sessions/Dockerfile.pipeline .

# Run with debug logging
docker run -e LOG_LEVEL=DEBUG -e DEBUG=true -p 8083:8083 test-session-pipeline
```

## Production Deployment

For production deployment on Raspberry Pi:

1. Build all images using the provided scripts
2. Use Docker Compose for orchestration
3. Configure persistent volumes for data storage
4. Set up monitoring and logging
5. Configure network security and access controls
