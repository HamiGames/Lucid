# Build Scripts

This directory contains build automation scripts for the Lucid project's distroless container builds.

## Scripts Overview

### `build-distroless.ps1` - Windows PowerShell Build Script

Windows PowerShell script for building distroless images with multi-platform support.

**Usage:**
```powershell
.\build-distroless.ps1 [OPTIONS]
```

**Options:**
- `-Services <services>` - Services to build (comma-separated or 'all')
- `-Platform <platform>` - Target platforms (comma-separated)
- `-Registry <registry>` - Container registry (default: ghcr.io)
- `-ImageName <name>` - Image name prefix (default: HamiGames/Lucid)
- `-Tag <tag>` - Image tag (default: latest)
- `-Push` - Push images to registry
- `-NoCache` - Disable build cache
- `-Verbose` - Enable verbose output
- `-Help` - Show help message

**Examples:**
```powershell
# Build all services
.\build-distroless.ps1

# Build specific services and push
.\build-distroless.ps1 -Services "gui,blockchain" -Push

# Build for Raspberry Pi only
.\build-distroless.ps1 -Platform "linux/arm64" -Tag "v1.0.0" -Push

# Build with verbose output and no cache
.\build-distroless.ps1 -Services "rdp" -NoCache -Verbose
```

### `build-distroless.sh` - Linux Shell Build Script

Linux shell script for building distroless images with multi-platform support.

**Usage:**
```bash
./build-distroless.sh [OPTIONS]
```

**Options:**
- `-s, --services <services>` - Services to build (comma-separated or 'all')
- `-p, --platform <platform>` - Target platforms (comma-separated)
- `-r, --registry <registry>` - Container registry (default: ghcr.io)
- `-i, --image-name <name>` - Image name prefix (default: HamiGames/Lucid)
- `-t, --tag <tag>` - Image tag (default: latest)
- `--push` - Push images to registry
- `--no-cache` - Disable build cache
- `-v, --verbose` - Enable verbose output
- `-h, --help` - Show help message

**Examples:**
```bash
# Build all services
./build-distroless.sh

# Build specific services and push
./build-distroless.sh --services "gui,blockchain" --push

# Build for Raspberry Pi only
./build-distroless.sh --platform "linux/arm64" --tag "v1.0.0" --push

# Build with verbose output and no cache
./build-distroless.sh --services "rdp" --no-cache --verbose
```

### `optimize-layers.py` - Layer Optimization Script

Python script for analyzing and optimizing Docker image layers for better caching and smaller sizes.

**Usage:**
```bash
python optimize-layers.py --service <service_name> [OPTIONS]
```

**Options:**
- `--service <name>` - Service name to optimize (required)
- `--image <name>` - Full image name (overrides service-based naming)
- `--registry <registry>` - Container registry (default: ghcr.io)
- `--project-name <name>` - Project name (default: HamiGames/Lucid)
- `--output-dir <dir>` - Output directory for reports (default: build/optimization)
- `--generate-dockerfile` - Generate optimized Dockerfile
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Analyze GUI service layers
python optimize-layers.py --service gui

# Analyze with custom image name
python optimize-layers.py --service blockchain --image "custom/blockchain:latest"

# Generate optimized Dockerfile
python optimize-layers.py --service rdp --generate-dockerfile

# Analyze with verbose output
python optimize-layers.py --service node --verbose
```

## Build Process

### 1. Prerequisites

- Docker with Buildx support
- Access to container registry (for pushing)
- Proper authentication configured

### 2. Build Flow

1. **Prerequisites Check** - Verify Docker and Buildx are available
2. **Buildx Initialization** - Set up multi-platform builder
3. **Base Image Build** - Build distroless base image first
4. **Service Image Build** - Build individual service images
5. **Image Testing** - Test built images (if not pushing)
6. **Summary Report** - Display build results

### 3. Optimization Process

1. **Image Analysis** - Analyze existing image layers
2. **Strategy Generation** - Generate optimization strategies
3. **Report Creation** - Create detailed optimization report
4. **Dockerfile Generation** - Generate optimized Dockerfile (optional)

## Output Files

### Build Scripts Output
- Built Docker images (local or registry)
- Build logs and status reports
- Cache files for faster subsequent builds

### Optimization Script Output
- `{service}_analysis.json` - Detailed analysis results
- `{service}_optimization_report.md` - Optimization recommendations
- `Dockerfile.{service}.optimized` - Optimized Dockerfile (if requested)

## Best Practices

### Build Optimization
1. **Use Build Cache** - Enable caching for faster builds
2. **Parallel Builds** - Build multiple services in parallel when possible
3. **Platform Targeting** - Build only for required platforms
4. **Layer Optimization** - Use multi-stage builds and layer consolidation

### Image Optimization
1. **Regular Analysis** - Run layer optimization regularly
2. **Base Image Updates** - Keep base images updated
3. **Dependency Cleanup** - Remove unnecessary packages and caches
4. **Multi-stage Builds** - Use separate build and runtime stages

## Troubleshooting

### Common Issues

1. **Buildx Not Available**
   ```bash
   # Install Docker Buildx
   docker buildx install
   ```

2. **Registry Authentication**
   ```bash
   # Login to registry
   docker login ghcr.io
   ```

3. **Platform Not Supported**
   ```bash
   # Check supported platforms
   docker buildx ls
   ```

4. **Memory Issues**
   - Reduce parallel builds
   - Use smaller base images
   - Optimize Dockerfile layers

### Debug Mode

Use `--verbose` flag for detailed logging:
```bash
./build-distroless.sh --services gui --verbose
python optimize-layers.py --service gui --verbose
```

## Integration

These scripts are designed to integrate with:
- GitHub Actions workflows (`.github/workflows/build-distroless.yml`)
- CI/CD pipelines
- Local development environments
- Raspberry Pi deployment workflows

## Support

For issues or questions:
1. Check the verbose logs for detailed error information
2. Verify prerequisites are met
3. Ensure proper Docker and Buildx configuration
4. Review the optimization reports for improvement suggestions
