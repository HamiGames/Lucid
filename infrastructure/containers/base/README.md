# Lucid Base Images

This directory contains the foundation distroless base images for all Lucid services. These images provide a secure, minimal runtime environment optimized for production deployment.

## Overview

The base images are built using distroless containers, which provide:
- **Minimal Attack Surface**: No shell, package manager, or unnecessary binaries
- **Security**: Non-root user, immutable runtime environment
- **Performance**: Optimized for size and startup time
- **Multi-platform**: Support for both AMD64 and ARM64 architectures

## Images

### Python Base Image
- **Image**: `ghcr.io/hamigames/lucid/python-base:latest`
- **Base**: `gcr.io/distroless/python3-debian12:latest`
- **Size**: ~150MB
- **Dependencies**: FastAPI, Uvicorn, Pydantic, Motor, Redis, and more

### Java Base Image
- **Image**: `ghcr.io/hamigames/lucid/java-base:latest`
- **Base**: `gcr.io/distroless/java17-debian12:latest`
- **Size**: ~200MB
- **Dependencies**: Spring Boot, Spring Security, MongoDB, Redis, and more

## Quick Start

### Build All Images
```bash
# Using the foundation script
./scripts/foundation/build-distroless-base-images.sh

# Or using the local build script
./build-base-images.sh
```

### Build Individual Images
```bash
# Python base image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/hamigames/lucid/python-base:latest \
  -f Dockerfile.python-base \
  --push .

# Java base image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/hamigames/lucid/java-base:latest \
  -f Dockerfile.java-base \
  --push .
```

### Use in Your Dockerfile
```dockerfile
# Python service
FROM ghcr.io/hamigames/lucid/python-base:latest
COPY . /app
CMD ["python", "main.py"]

# Java service
FROM ghcr.io/hamigames/lucid/java-base:latest
COPY target/*.jar /app/app.jar
CMD ["java", "-jar", "app.jar"]
```

## Configuration

### Environment Variables
Copy `env.template` to `.env` and customize:
```bash
cp env.template .env
```

### Build Configuration
Edit `build.config.yml` for advanced build settings.

## Files

| File | Description |
|------|-------------|
| `Dockerfile.python-base` | Python distroless base image |
| `Dockerfile.java-base` | Java distroless base image |
| `requirements.txt` | Python dependencies |
| `pom.xml` | Maven configuration |
| `build.gradle` | Gradle configuration |
| `gradle.properties` | Gradle properties |
| `build-base-images.sh` | Local build script |
| `docker-compose.base.yml` | Development environment |
| `env.template` | Environment template |
| `build.config.yml` | Build configuration |
| `.dockerignore` | Docker ignore rules |

## Development

### Local Testing
```bash
# Start development environment
docker-compose -f docker-compose.base.yml up

# Test Python base
docker run --rm lucid-python-base:latest python -c "print('Hello from Python base')"

# Test Java base
docker run --rm lucid-java-base:latest java -version
```

### Build Optimization
- Use `--build-arg BUILDKIT_INLINE_CACHE=1` for cache optimization
- Enable parallel builds with `--build-arg BUILDKIT_PROGRESS=plain`
- Use multi-stage builds to minimize final image size

## Security Features

### Distroless Benefits
- **No Shell**: Cannot execute shell commands
- **No Package Manager**: Cannot install additional packages
- **Non-root User**: Runs as `nonroot:nonroot`
- **Minimal Dependencies**: Only required runtime libraries
- **Immutable**: Runtime environment cannot be modified

### Security Hardening
- All containers run as non-root user
- Minimal attack surface with no unnecessary binaries
- Regular security updates through base image updates
- Vulnerability scanning during build process

## Troubleshooting

### Build Issues
```bash
# Check Docker Buildx
docker buildx ls

# Inspect builder
docker buildx inspect lucid-builder

# Create new builder
docker buildx create --name lucid-builder --use
```

### Registry Issues
```bash
# Login to GitHub Container Registry
docker login ghcr.io --username hamigames

# Test registry access
docker pull ghcr.io/hamigames/lucid/python-base:latest
```

### Platform Issues
```bash
# Check platform support
docker buildx ls

# Build for specific platform
docker buildx build --platform linux/arm64 -t test:latest .
```

## Dependencies

### Required Tools
- Docker with BuildKit enabled
- Docker buildx plugin
- GitHub Container Registry access
- Git for version tagging

### Base Image Requirements
- `gcr.io/distroless/python3-debian12:latest`
- `gcr.io/distroless/java17-debian12:latest`

## Next Steps

After building base images:
1. Verify images in GitHub Container Registry
2. Update service Dockerfiles to use new base images
3. Test dependent service builds
4. Proceed to Phase 1 foundation services build

## Support

For issues or questions:
- Check the troubleshooting section
- Review build logs for specific errors
- Ensure all dependencies are installed
- Verify registry authentication
