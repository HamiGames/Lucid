# LUCID Project Regulations
# Docker Image and Deployment Standards
# Professional container security and deployment guidelines

**Effective Date:** 2025-10-06  
**Version:** 1.0.0  
**Scope:** All Lucid project components  
**Compliance:** Mandatory for all development and deployment  

---

## **REGULATION 1: DISTROLESS IMAGES ONLY**

### **1.1 Mandatory Distroless Base Images**
All Docker images in the Lucid project MUST use distroless base images:

#### **Approved Base Images**
```dockerfile
# Python applications
FROM gcr.io/distroless/python3-debian12:nonroot

# Node.js applications  
FROM gcr.io/distroless/nodejs20-debian12:nonroot

# System utilities and services
FROM gcr.io/distroless/base-debian12:nonroot

# Java applications (if needed)
FROM gcr.io/distroless/java17-debian12:nonroot
```

#### **Prohibited Base Images**
```dockerfile
# ❌ FORBIDDEN - Standard base images
FROM python:3.11-slim
FROM node:20-alpine
FROM ubuntu:22.04
FROM debian:12-slim

# ❌ FORBIDDEN - Full OS images
FROM ubuntu:latest
FROM centos:latest
FROM alpine:latest
```

### **1.2 Multi-Stage Build Requirements**
All Dockerfiles MUST use multi-stage builds:

```dockerfile
# Stage 1: Builder (temporary)
FROM python:3.11-slim AS builder
# Install dependencies and build artifacts

# Stage 2: Distroless runtime (final)
FROM gcr.io/distroless/python3-debian12:nonroot
# Copy only necessary artifacts from builder
```

### **1.3 Security Requirements**
- **Non-root user**: All containers MUST run as non-root user
- **Minimal attack surface**: Only essential binaries and libraries
- **No shell access**: No shell interpreters in runtime images
- **Read-only filesystem**: Where possible, use read-only root filesystem

---

## **REGULATION 2: YAML COMPOSITION ONLY**

### **2.1 No Build Contexts in Production**
All production Docker Compose files MUST use pre-built images:

```yaml
# ✅ CORRECT - Pull from registry
services:
  lucid-api:
    image: pickme/lucid:lucid-api
    pull_policy: always

# ❌ FORBIDDEN - Build contexts in production
services:
  lucid-api:
    build:
      context: ./api
      dockerfile: Dockerfile
```

### **2.2 Registry Standards**
All images MUST be stored in the project registry:

```yaml
# Registry format
image: pickme/lucid:<service-name>

# Examples
image: pickme/lucid:session-recorder
image: pickme/lucid:on-system-chain-client
image: pickme/lucid:tron-node-client
image: pickme/lucid:admin-ui
```

### **2.3 Pull Policy Requirements**
All services MUST use `pull_policy: always`:

```yaml
services:
  service-name:
    image: pickme/lucid:service-name
    pull_policy: always  # MANDATORY
```

---

## **REGULATION 3: IMAGE BUILDING PROCESS**

### **3.1 Build Scripts Only**
Image building MUST be done through dedicated build scripts:

#### **PowerShell Build Scripts**
```powershell
# scripts/build-all-modules.ps1
# scripts/build-layer1-distroless.ps1
# scripts/build-layer2-distroless.ps1
```

#### **Bash Build Scripts**
```bash
# scripts/build-all-modules.sh
# scripts/build-layer1-distroless.sh
# scripts/build-layer2-distroless.sh
```

### **3.2 Build Requirements**
- **Multi-platform**: All images MUST support `linux/amd64,linux/arm64`
- **No cache**: Production builds MUST use `--no-cache`
- **Registry push**: All builds MUST push to `pickme/lucid` registry
- **Verification**: All builds MUST include verification steps

### **3.3 Build Command Standards**
```bash
# Standard build command
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --no-cache \
  --push \
  --tag pickme/lucid:<service-name> \
  --file <dockerfile> \
  .
```

---

## **REGULATION 4: DEPLOYMENT COMPOSITION**

### **4.1 Layer-Based Organization**
All deployment files MUST follow layer organization:

```
infrastructure/compose/
├── lucid-dev.yaml              # Development environment
├── lucid-layer1-complete.yaml  # Layer 1: Core Infrastructure
├── lucid-layer2-complete.yaml  # Layer 2: Service Integration
└── lucid-layer3-complete.yaml  # Layer 3: UI and Production
```

### **4.2 Network Standards**
All compose files MUST use standardized networks:

```yaml
networks:
  lucid_core_net:
    name: lucid_core_net
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/24
          gateway: 172.21.0.1
```

### **4.3 Volume Standards**
All volumes MUST use consistent naming:

```yaml
volumes:
  lucid_mongo_data:
    name: lucid_mongo_data
    labels:
      - "org.lucid.layer=1"
      - "org.lucid.volume=mongodb"
```

---

## **REGULATION 5: COMPLIANCE ENFORCEMENT**

### **5.1 Pre-Deployment Checks**
Before any deployment, the following MUST be verified:

1. **No build contexts**: All services use `image:` not `build:`
2. **Distroless images**: All images use approved distroless base
3. **Pull policy**: All services have `pull_policy: always`
4. **Registry format**: All images use `pickme/lucid:` prefix
5. **Network consistency**: All networks use `lucid_core_net`

### **5.2 Validation Scripts**
```bash
# Validate compose files
docker-compose -f <compose-file> config --quiet

# Check for build contexts
grep -r "build:" infrastructure/compose/

# Verify distroless usage
grep -r "FROM gcr.io/distroless" */
```

### **5.3 Non-Compliance Consequences**
- **Development**: Build failures and deployment errors
- **Production**: Security vulnerabilities and compliance issues
- **Maintenance**: Increased complexity and technical debt

---

## **REGULATION 6: EXCEPTIONS AND SPECIAL CASES**

### **6.1 Development-Only Exceptions**
The following MAY use non-distroless images for development:

```yaml
# Development only - NOT for production
services:
  dev-tools:
    image: ubuntu:22.04  # Development tools only
    profiles: ["dev"]
```

### **6.2 Legacy System Integration**
Existing systems that cannot be converted to distroless:

```yaml
# Legacy integration - Document justification required
services:
  legacy-service:
    image: pickme/lucid:legacy-service
    # Must include security review and migration plan
```

### **6.3 Third-Party Services**
External services that cannot be controlled:

```yaml
# Third-party services - Use official images
services:
  mongodb:
    image: mongo:7.0  # Official MongoDB image
    pull_policy: always
```

---

## **REGULATION 7: DOCUMENTATION REQUIREMENTS**

### **7.1 Dockerfile Documentation**
Every Dockerfile MUST include:

```dockerfile
# LUCID <SERVICE_NAME> - SPEC-<NUMBER> <DESCRIPTION> (Distroless)
# Professional <description> for <purpose> with distroless security
# Multi-platform build for ARM64 Pi and AMD64 development

# syntax=docker/dockerfile:1.7
```

### **7.2 Compose File Documentation**
Every compose file MUST include:

```yaml
# LUCID <LAYER_NAME> - SPEC-<NUMBER> <DESCRIPTION>
# Complete <layer> implementation with all required modules
# Multi-platform deployment for ARM64 Pi and AMD64 development

version: '3.8'
```

### **7.3 Build Script Documentation**
Every build script MUST include:

```powershell
# LUCID <PURPOSE> Build Script
# <description> based on SPEC-<NUMBER> requirements
# Multi-platform build for ARM64 Pi and AMD64 development
```

---

## **REGULATION 8: IMPLEMENTATION TIMELINE**

### **8.1 Immediate Compliance (Effective Now)**
- All new Dockerfiles MUST use distroless base images
- All new compose files MUST use registry images only
- All build scripts MUST follow standardized format

### **8.2 Legacy Migration (30 days)**
- Convert all existing Dockerfiles to distroless
- Update all compose files to use registry images
- Remove all build contexts from production files

### **8.3 Full Compliance (60 days)**
- All images in registry are distroless
- All deployment files use composition only
- All documentation updated to reflect standards

---

## **REGULATION 9: MONITORING AND ENFORCEMENT**

### **9.1 Automated Checks**
```bash
# Check for non-distroless images
grep -r "FROM.*slim\|FROM.*alpine\|FROM.*ubuntu" */Dockerfile*

# Check for build contexts
grep -r "build:" infrastructure/compose/

# Verify pull policies
grep -r "pull_policy: always" infrastructure/compose/
```

### **9.2 Manual Reviews**
- All pull requests MUST be reviewed for compliance
- All deployments MUST be validated against regulations
- All security scans MUST pass distroless requirements

### **9.3 Continuous Improvement**
- Regular updates to distroless base images
- Optimization of multi-stage builds
- Enhancement of security configurations

---

## **REGULATION 10: VIOLATIONS AND REMEDIATION**

### **10.1 Violation Types**
1. **Critical**: Using non-distroless base images
2. **Major**: Build contexts in production compose files
3. **Minor**: Missing pull policies or documentation

### **10.2 Remediation Process**
1. **Immediate**: Fix critical violations before deployment
2. **Scheduled**: Address major violations in next sprint
3. **Documented**: Track minor violations for future improvement

### **10.3 Prevention Measures**
- Pre-commit hooks for compliance checking
- CI/CD pipeline validation
- Regular security audits and reviews

---

**This regulation is mandatory for all Lucid project development and deployment activities.**
