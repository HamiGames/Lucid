# LUCID Layer 2 Build Guide

# Distroless Image Build and Push Process

# Multi-platform builds for ARM64 Pi and AMD64 development

**Generated:** 2025-10-05T06:31:54Z
**Mode:** LUCID-STRICT Distroless Build
**Purpose:** Build and push Layer 2 distroless images to Docker Hub
**Target:** Pi 5 ARM64 with distroless security

---

## **OVERVIEW**

This guide provides step-by-step instructions for building and pushing Layer 2 distroless images to the Docker Hub registry.

### **Available Build Scripts**

- `scripts/verify-dockerfiles.ps1` - Verify Dockerfiles before building

- `scripts/build-layer2-distroless.ps1` - Build and push distroless images

- `scripts/build-layer2-complete.ps1` - Complete build process with verification

---

## **PREREQUISITES**

### **System Requirements**

- Docker with buildx support

- PowerShell 5.1 or later

- Docker Hub account and login

- Multi-platform build capability

### **Docker Setup**

```powershell

# Verify Docker buildx is available

docker buildx version

# Login to Docker Hub

docker login

# Verify login

docker info | Select-String "Username"

```

---

## **BUILD PROCESS**

### **Step 1: Verify Dockerfiles**

Before building, verify all Dockerfiles are correctly composed:

```powershell

# Verify all Dockerfiles

.\scripts\verify-dockerfiles.ps1

# Verify with verbose output

.\scripts\verify-dockerfiles.ps1 -Verbose

```

**Expected Output:**

```php

=== LUCID Layer 2 Dockerfile Verification ===

Verifying RDP Server Manager...
✅ Distroless base image correct: gcr.io/distroless/python3-debian12:nonroot
✅ Multi-stage build detected
✅ Dockerfile syntax directive present
✅ Metadata labels present
✅ Non-root user configured

Verifying xrdp Integration...
✅ Distroless base image correct: gcr.io/distroless/base-debian12:nonroot
✅ Multi-stage build detected
✅ Dockerfile syntax directive present
✅ Metadata labels present
✅ Non-root user configured

Verifying Contract Deployment...
✅ Distroless base image correct: gcr.io/distroless/python3-debian12:nonroot
✅ Multi-stage build detected
✅ Dockerfile syntax directive present
✅ Metadata labels present
✅ Non-root user configured

=== All Dockerfiles are valid ===
Ready to build Layer 2 distroless images

```php

### **Step 2: Build and Push Images**

#### **Complete Build Process (Recommended)**

```powershell

# Build and push all images with verification

.\scripts\build-layer2-complete.ps1

# Build with custom registry and tag

.\scripts\build-layer2-complete.ps1 -Registry "your-registry" -Tag "v1.0.0"

# Build with verbose output

.\scripts\build-layer2-complete.ps1 -Verbose

# Build without pushing (local only)

.\scripts\build-layer2-complete.ps1 -Push:$false

```php

#### **Direct Build Process**

```powershell

# Build and push without verification

.\scripts\build-layer2-distroless.ps1

# Build with custom parameters

.\scripts\build-layer2-distroless.ps1 -Registry "your-registry" -Repository "lucid" -Tag "latest" -Verbose

```php

---

## **BUILD CONFIGURATION**

### **Script Parameters**

| Parameter | Type | Default | Description |

|-----------|------|---------|-------------|

| `Registry` | String | `pickme` | Docker registry name |

| `Repository` | String | `lucid` | Repository name |

| `Tag` | String | `latest` | Image tag |

| `Push` | Switch | `$true` | Push images to registry |

| `NoCache` | Switch | `$true` | Build without cache |

| `Verbose` | Switch | `$false` | Verbose output |

| `SkipVerification` | Switch | `$false` | Skip Dockerfile verification |

### **Build Examples**

#### **Standard Build**

```powershell

.\scripts\build-layer2-complete.ps1

```

#### **Custom Registry Build**

```powershell

.\scripts\build-layer2-complete.ps1 -Registry "myregistry" -Repository "lucid" -Tag "v1.0.0"

```php

#### **Development Build**

```powershell

.\scripts\build-layer2-complete.ps1 -Tag "dev" -Verbose

```php

#### **Local Build Only**

```powershell

.\scripts\build-layer2-complete.ps1 -Push:$false

```

---

## **BUILD OUTPUT**

### **Expected Images**

The build process creates the following images:

```

pickme/lucid:rdp-server-manager
pickme/lucid:rdp-server-manager-latest
pickme/lucid:xrdp-integration
pickme/lucid:xrdp-integration-latest
pickme/lucid:contract-deployment
pickme/lucid:contract-deployment-latest

```

### **Multi-Platform Support**

All images are built for:

- `linux/amd64` - AMD64 development

- `linux/arm64` - ARM64 Pi 5 deployment

---

## **VERIFICATION**

### **Check Built Images**

```powershell

# List local images

docker images | Select-String "pickme/lucid"

# Check image manifest

docker manifest inspect pickme/lucid:rdp-server-manager
docker manifest inspect pickme/lucid:xrdp-integration
docker manifest inspect pickme/lucid:contract-deployment

```

### **Test Image Pull**

```powershell

# Test pulling images

docker pull pickme/lucid:rdp-server-manager
docker pull pickme/lucid:xrdp-integration
docker pull pickme/lucid:contract-deployment

```

---

## **TROUBLESHOOTING**

### **Common Issues**

#### **1. Docker Buildx Not Available**

```powershell

# Install Docker buildx

docker buildx install

# Verify installation

docker buildx version

```

#### **2. Docker Hub Login Issues**

```powershell

# Login to Docker Hub

docker login

# Verify login

docker info | Select-String "Username"

```

#### **3. Build Failures**

```powershell

# Check Docker daemon

docker info

# Check buildx builder

docker buildx ls

# Create new builder if needed

docker buildx create --name lucid-builder --use

```

#### **4. Network Issues**

```powershell

# Check internet connectivity

Test-NetConnection hub.docker.com

# Check DNS resolution

nslookup hub.docker.com

```bash

### **Debug Build Process**

```powershell

# Build with verbose output

.\scripts\build-layer2-complete.ps1 -Verbose

# Check build logs

docker buildx logs

# Inspect build cache

docker buildx du

```bash

---

## **DEPLOYMENT**

### **Pi 5 Deployment**

After successful build and push, deploy on Pi 5:

```bash

# SSH to Pi 5

ssh pickme@192.168.0.75

# Navigate to Lucid directory

cd /mnt/myssd/Lucid

# Pull latest images

docker pull pickme/lucid:rdp-server-manager
docker pull pickme/lucid:xrdp-integration
docker pull pickme/lucid:contract-deployment

# Deploy Layer 2 services

docker-compose -f infrastructure/compose/lucid-layer2-simple.yaml \
  --profile rdp-server \
  --profile blockchain-deployment \
  up -d

```

### **Local Development**

```powershell

# Deploy locally for testing

docker-compose -f infrastructure/compose/lucid-layer2-simple.yaml \
  --profile rdp-server \
  --profile blockchain-deployment \
  up -d

```

---

## **BEST PRACTICES**

### **1. Build Process**

- Always verify Dockerfiles before building

- Use `--no-cache` for clean builds

- Test images locally before pushing

- Use semantic versioning for tags

### **2. Registry Management**

- Use consistent registry naming

- Tag images with versions

- Keep latest tag updated

- Monitor registry usage

### **3. Security**

- Use distroless base images

- Run as non-root user

- Minimize attack surface

- Regular security updates

---

**This build guide provides complete instructions for building and pushing Layer 2 distroless images to Docker Hub registry.**
