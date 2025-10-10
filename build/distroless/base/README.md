# Lucid Base Distroless Images

This directory contains the base distroless Docker images for the Lucid project. These images provide the foundation for all other Lucid services and are optimized for security, minimal attack surface, and multi-platform support.

## Overview

The base distroless images are designed to:
- Provide a minimal, secure runtime environment
- Support both AMD64 (development) and ARM64 (Raspberry Pi) architectures
- Include essential Python packages and dependencies
- Follow distroless best practices for container security

## Available Base Images

### 1. `Dockerfile.base.distroless`
- **Purpose**: Standard base image with full Python ecosystem
- **Use Case**: General-purpose services requiring comprehensive Python libraries
- **Size**: Medium (includes full dependency stack)
- **Security**: High (distroless runtime)

### 2. `Dockerfile.python-base.distroless`
- **Purpose**: Python-optimized base image with essential packages
- **Use Case**: Python services with standard web frameworks and database connectivity
- **Size**: Medium (includes core Python packages)
- **Security**: High (distroless runtime)

### 3. `Dockerfile.alpine-base.distroless`
- **Purpose**: Ultra-minimal base image using Alpine Linux
- **Use Case**: Resource-constrained environments, embedded systems
- **Size**: Small (minimal dependencies)
- **Security**: Very High (Alpine + distroless)

## Building Base Images

### Windows (PowerShell)
```powershell
# Build all base images
.\build-base.ps1

# Build with specific options
.\build-base.ps1 -Platform "linux/arm64" -Push -Tag "v1.0.0"

# Build without cache
.\build-base.ps1 -NoCache
```

### Linux/macOS (Bash)
```bash
# Build all base images
./build-base.sh

# Build with specific options
./build-base.sh --platform "linux/arm64" --push --tag "v1.0.0"

# Build without cache
./build-base.sh --no-cache
```

### Environment Variables
- `PLATFORM`: Target platforms (default: `linux/amd64,linux/arm64`)
- `PUSH`: Push to registry (default: `false`)
- `NO_CACHE`: Build without cache (default: `false`)
- `REGISTRY`: Registry name (default: `lucid`)
- `TAG`: Image tag (default: `latest`)

## Image Specifications

### Base Requirements
All base images include:
- Python 3.11 runtime
- Essential cryptographic libraries
- Network communication packages
- Database connectivity packages
- Monitoring and logging utilities

### Security Features
- Non-root user execution
- Minimal attack surface
- No shell or package manager in runtime
- Distroless base images
- Multi-stage builds

### Multi-Platform Support
- **AMD64**: Development and production servers
- **ARM64**: Raspberry Pi and ARM-based devices

## Usage Examples

### Using Base Images in Service Dockerfiles
```dockerfile
FROM lucid/base:latest

# Copy application code
COPY src/ /app/src/
COPY requirements.txt /app/

# Install service-specific dependencies
RUN pip install -r requirements.txt

# Set application-specific environment
ENV SERVICE_NAME=my-service
ENV SERVICE_PORT=8000

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "src.main"]
```

### Docker Compose Integration
```yaml
version: '3.8'
services:
  my-service:
    build:
      context: .
      dockerfile: Dockerfile
    image: lucid/my-service:latest
    depends_on:
      - lucid-base
    networks:
      - lucid-network
```

## Registry Management

### Local Development
Images are built locally by default and can be used immediately.

### Registry Deployment
To push images to a registry:
```bash
# Set registry
export REGISTRY="your-registry.com/lucid"

# Build and push
./build-base.sh --push --tag "v1.0.0"
```

## Maintenance

### Updating Dependencies
1. Update `requirements.txt` with new package versions
2. Rebuild images with `--no-cache` flag
3. Test images in development environment
4. Deploy to registry with new tag

### Security Updates
1. Monitor for security advisories in base images
2. Update base image versions in Dockerfiles
3. Rebuild and test all dependent services
4. Deploy updates following standard procedures

## Troubleshooting

### Build Issues
- Ensure Docker Buildx is installed and configured
- Check available disk space for multi-platform builds
- Verify network connectivity for package downloads

### Runtime Issues
- Check container logs for Python import errors
- Verify environment variables are set correctly
- Ensure proper file permissions for application code

### Performance Issues
- Use appropriate base image for use case (alpine for minimal, standard for full features)
- Monitor resource usage and adjust container limits
- Consider using multi-stage builds for optimization

## Contributing

When adding new base images:
1. Follow naming convention: `Dockerfile.{name}-base.distroless`
2. Include comprehensive comments in Dockerfile
3. Update build scripts to include new images
4. Add documentation to this README
5. Test on both AMD64 and ARM64 platforms

## References

- [Distroless Images](https://github.com/GoogleContainerTools/distroless)
- [Docker Multi-Platform Builds](https://docs.docker.com/buildx/working-with-buildx/)
- [Python Docker Best Practices](https://pythonspeed.com/docker/)
- [Container Security Best Practices](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
