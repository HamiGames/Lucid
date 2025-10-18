# Lucid Distroless Build Scripts

This directory contains scripts for building the Lucid project as distroless Docker images without using the devcontainer.

## 📁 Scripts Overview

### 1. `build-distroless.ps1` - Full Build Script
Complete build script that sets up and builds all Lucid services as distroless images.

**Features:**
- ✅ Docker and Buildx verification
- ✅ Network creation (lucid-dev_lucid_core, lucid-dev_lucid_net)
- ✅ Automatic Dockerfile and requirements.txt generation
- ✅ Multi-platform builds (AMD64 + ARM64)
- ✅ Registry push support
- ✅ Comprehensive build reporting

**Usage:**
```powershell
# Basic build
.\scripts\build\build-distroless.ps1

# Build and push to registry
.\scripts\build\build-distroless.ps1 -PushToRegistry

# Build specific platform only
.\scripts\build\build-distroless.ps1 -Platform "linux/amd64"

# Force build without confirmation
.\scripts\build\build-distroless.ps1 -Force
```

### 2. `quick-build.ps1` - Single Service Build
Quick build script for individual services.

**Usage:**
```powershell
# Build API service
.\scripts\build\quick-build.ps1 -Service api

# Build GUI service
.\scripts\build\quick-build.ps1 -Service gui

# Build with custom tag
.\scripts\build\quick-build.ps1 -Service blockchain -Tag "v1.0.0"
```

### 3. `setup-networks.ps1` - Network Setup
Creates the required Docker networks for Lucid services.

**Usage:**
```powershell
# Setup networks
.\scripts\build\setup-networks.ps1

# Force setup without confirmation
.\scripts\build\setup-networks.ps1 -Force
```

## 🌐 Network Configuration

The scripts create two networks:

### lucid-dev_lucid_net
- **Subnet:** 172.20.0.0/16
- **Gateway:** 172.20.0.1
- **Purpose:** Main development network for services

### lucid-dev_lucid_core
- **Subnet:** 172.21.0.0/16
- **Gateway:** 172.21.0.1
- **Purpose:** Core services network

## 🏗️ Build Process

### Automatic File Generation
The build script automatically creates:

1. **Dockerfile** for each service with:
   - Multi-stage build (builder + distroless runtime)
   - Python 3.11 base with security optimizations
   - Health checks
   - Non-root user execution
   - Proper environment variables

2. **requirements.txt** with common dependencies:
   - FastAPI and Uvicorn
   - Pydantic and validation
   - MongoDB drivers
   - Cryptography and security
   - HTTP clients

### Service Structure
```
src/
├── api/
│   ├── Dockerfile (auto-generated)
│   ├── requirements.txt (auto-generated)
│   └── ... (source code)
├── gui/
│   ├── Dockerfile (auto-generated)
│   ├── requirements.txt (auto-generated)
│   └── ... (source code)
└── ... (other services)
```

## 🚀 Running Built Images

### Single Service
```bash
# Run API service
docker run --rm \
  --network lucid-dev_lucid_net \
  --ip 172.20.0.100 \
  -p 8081:8080 \
  pickme/lucid/api:latest

# Run GUI service
docker run --rm \
  --network lucid-dev_lucid_net \
  --ip 172.20.0.101 \
  -p 8083:8080 \
  pickme/lucid/gui:latest
```

### Multiple Services
```bash
# Run with both networks
docker run --rm \
  --network lucid-dev_lucid_net \
  --network lucid-dev_lucid_core \
  pickme/lucid/api:latest
```

### Docker Compose
```yaml
version: '3.8'
services:
  api:
    image: pickme/lucid/api:latest
    networks:
      - lucid-dev_lucid_net
    ipv4_address: 172.20.0.100
    ports:
      - "8081:8080"
  
  gui:
    image: pickme/lucid/gui:latest
    networks:
      - lucid-dev_lucid_net
    ipv4_address: 172.20.0.101
    ports:
      - "8083:8080"

networks:
  lucid-dev_lucid_net:
    external: true
```

## 📋 Prerequisites

1. **Docker Desktop** running
2. **Docker Buildx** available
3. **PowerShell** (Windows) or PowerShell Core (Linux/macOS)
4. **Network access** for pulling base images

## 🔧 Customization

### Custom Registry
```powershell
.\scripts\build\build-distroless.ps1 -Registry "your-registry.com/lucid"
```

### Custom Builder
```powershell
.\scripts\build\build-distroless.ps1 -BuilderName "custom-builder"
```

### Platform-Specific Builds
```powershell
# AMD64 only (for development)
.\scripts\build\build-distroless.ps1 -Platform "linux/amd64"

# ARM64 only (for Raspberry Pi)
.\scripts\build\build-distroless.ps1 -Platform "linux/arm64"

# Both platforms
.\scripts\build\build-distroless.ps1 -Platform "linux/amd64,linux/arm64"
```

## 🐛 Troubleshooting

### Common Issues

1. **Docker not running**
   ```
   ❌ Docker is not running or not accessible
   ```
   **Solution:** Start Docker Desktop

2. **Buildx builder not found**
   ```
   ⚠️ Builder 'lucid-pi' not found, creating...
   ```
   **Solution:** Script will auto-create the builder

3. **Network already exists**
   ```
   ℹ️ Network 'lucid-dev_lucid_net' already exists
   ```
   **Solution:** This is normal, networks are reused

4. **Permission denied**
   ```
   ❌ Permission denied
   ```
   **Solution:** Run PowerShell as Administrator

### Debug Mode
Add `-Verbose` to see detailed output:
```powershell
.\scripts\build\build-distroless.ps1 -Verbose
```

## 📊 Build Output

The build script provides comprehensive output:
- ✅ Success indicators
- ⚠️ Warnings and info
- ❌ Error messages
- 📊 Build summary
- 🌐 Network information
- 🚀 Run command examples

## 🔒 Security Features

Built images include:
- **Distroless base** - Minimal attack surface
- **Non-root user** - Security best practices
- **Health checks** - Container monitoring
- **Minimal dependencies** - Reduced vulnerabilities
- **Multi-stage builds** - No build tools in runtime

## 📈 Performance

- **Multi-platform builds** - AMD64 + ARM64 support
- **Layer caching** - Faster subsequent builds
- **Optimized images** - Minimal size and startup time
- **Parallel builds** - Multiple services simultaneously

## 🤝 Contributing

To add new services:
1. Create service directory in `src/`
2. Run the build script to auto-generate files
3. Customize Dockerfile and requirements.txt as needed
4. Test the build with `quick-build.ps1`

## 📚 Additional Resources

- [Docker Distroless Images](https://github.com/GoogleContainerTools/distroless)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker Buildx](https://docs.docker.com/build/buildx/)
- [Docker Networks](https://docs.docker.com/network/)
