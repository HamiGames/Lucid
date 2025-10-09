# LUCID Compliance Guide
# How to follow project regulations for Docker images and deployment
# Professional development standards for the Lucid project

**Version:** 1.0.0  
**Effective Date:** 2025-10-06  
**Scope:** All developers and contributors  

---

## **QUICK START**

### **For New Developers**
1. Read the [Project Regulations](PROJECT_REGULATIONS.md)
2. Run compliance validation: `.\scripts\validate-compliance.ps1`
3. Build compliant images: `.\scripts\build-compliant.ps1`
4. Deploy with compose files: `docker-compose -f infrastructure/compose/lucid-layer1-complete.yaml up -d`

### **For Existing Code**
1. Check compliance: `.\scripts\validate-compliance.ps1`
2. Fix issues: `.\scripts\enforce-compliance.ps1 -Action fix`
3. Rebuild images: `.\scripts\build-compliant.ps1`
4. Update deployments: Use compose files with registry images

---

## **CORE PRINCIPLES**

### **1. Distroless Images Only**
```dockerfile
# ✅ CORRECT - Distroless base
FROM gcr.io/distroless/python3-debian12:nonroot

# ❌ WRONG - Standard base
FROM python:3.11-slim
```

### **2. YAML Composition Only**
```yaml
# ✅ CORRECT - Pull from registry
services:
  my-service:
    image: pickme/lucid:my-service
    pull_policy: always

# ❌ WRONG - Build context
services:
  my-service:
    build:
      context: ./my-service
      dockerfile: Dockerfile
```

### **3. Registry Standards**
- **Registry**: `pickme/lucid`
- **Format**: `pickme/lucid:<service-name>`
- **Pull Policy**: `always`
- **Multi-platform**: `linux/amd64,linux/arm64`

---

## **DEVELOPMENT WORKFLOW**

### **Step 1: Create Distroless Dockerfile**
```dockerfile
# LUCID MY-SERVICE - SPEC-1B Description (Distroless)
# Professional service description for purpose with distroless security
# Multi-platform build for ARM64 Pi and AMD64 development

# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS builder

# Build dependencies and artifacts
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Distroless runtime
FROM gcr.io/distroless/python3-debian12:nonroot

# Copy artifacts from builder
COPY --from=builder /app /app

# Non-root user and security
USER nonroot
WORKDIR /app

# Service entrypoint
ENTRYPOINT ["/usr/local/bin/python3.11", "/app/main.py"]
```

### **Step 2: Create Compose File**
```yaml
# LUCID Layer X - SPEC-1B Description
# Complete layer implementation with all required modules
# Multi-platform deployment for ARM64 Pi and AMD64 development

version: '3.8'

networks:
  lucid_core_net:
    name: lucid_core_net
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/24
          gateway: 172.21.0.1

volumes:
  lucid_data:
    name: lucid_data
    labels:
      - "org.lucid.layer=1"
      - "org.lucid.volume=data"

services:
  my-service:
    image: pickme/lucid:my-service
    pull_policy: always
    networks:
      - lucid_core_net
    volumes:
      - lucid_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### **Step 3: Build and Deploy**
```powershell
# Validate compliance
.\scripts\validate-compliance.ps1

# Build compliant images
.\scripts\build-compliant.ps1 -Push

# Deploy with compose
docker-compose -f infrastructure/compose/lucid-layer1-complete.yaml up -d
```

---

## **COMPLIANCE CHECKLIST**

### **Dockerfile Compliance**
- [ ] Uses distroless base image (`gcr.io/distroless/*`)
- [ ] Multi-stage build with builder stage
- [ ] Non-root user (`nonroot` or specific UID)
- [ ] Proper documentation header
- [ ] Syntax directive (`# syntax=docker/dockerfile:1.7`)
- [ ] No unnecessary packages or tools
- [ ] Minimal attack surface

### **Compose File Compliance**
- [ ] No `build:` contexts
- [ ] All services use `image:` with registry format
- [ ] All services have `pull_policy: always`
- [ ] Standardized network names (`lucid_core_net`)
- [ ] Proper volume naming (`lucid_*_data`)
- [ ] Health checks for all services
- [ ] Proper documentation header

### **Build Process Compliance**
- [ ] Multi-platform builds (`linux/amd64,linux/arm64`)
- [ ] No-cache builds (`--no-cache`)
- [ ] Registry push to `pickme/lucid`
- [ ] Build verification and testing
- [ ] Compliance validation before build

---

## **COMMON VIOLATIONS AND FIXES**

### **Violation 1: Non-Distroless Base Image**
```dockerfile
# ❌ VIOLATION
FROM python:3.11-slim

# ✅ FIX
FROM gcr.io/distroless/python3-debian12:nonroot
```

### **Violation 2: Build Context in Compose**
```yaml
# ❌ VIOLATION
services:
  my-service:
    build:
      context: ./my-service
      dockerfile: Dockerfile

# ✅ FIX
services:
  my-service:
    image: pickme/lucid:my-service
    pull_policy: always
```

### **Violation 3: Missing Pull Policy**
```yaml
# ❌ VIOLATION
services:
  my-service:
    image: pickme/lucid:my-service

# ✅ FIX
services:
  my-service:
    image: pickme/lucid:my-service
    pull_policy: always
```

### **Violation 4: Non-Standard Network Names**
```yaml
# ❌ VIOLATION
networks:
  my_network:
    name: my_network

# ✅ FIX
networks:
  lucid_core_net:
    name: lucid_core_net
```

---

## **AUTOMATION SCRIPTS**

### **Validation Script**
```powershell
# Check compliance
.\scripts\validate-compliance.ps1

# Check with verbose output
.\scripts\validate-compliance.ps1 -Verbose
```

### **Enforcement Script**
```powershell
# Validate compliance
.\scripts\enforce-compliance.ps1 -Action validate

# Fix compliance issues
.\scripts\enforce-compliance.ps1 -Action fix

# Enforce compliance
.\scripts\enforce-compliance.ps1 -Action enforce
```

### **Build Script**
```powershell
# Build all compliant images
.\scripts\build-compliant.ps1

# Build with custom registry
.\scripts\build-compliant.ps1 -Registry "myregistry" -Repository "lucid"

# Build without pushing
.\scripts\build-compliant.ps1 -Push:$false
```

---

## **TROUBLESHOOTING**

### **Common Issues**

#### **1. Compliance Validation Fails**
```powershell
# Check specific violations
.\scripts\validate-compliance.ps1 -Verbose

# Fix automatically
.\scripts\enforce-compliance.ps1 -Action fix
```

#### **2. Build Failures**
```powershell
# Check Docker buildx
docker buildx version

# Check Docker Hub login
docker login

# Verify registry access
docker pull pickme/lucid:test
```

#### **3. Deployment Issues**
```powershell
# Validate compose files
docker-compose -f infrastructure/compose/lucid-layer1-complete.yaml config

# Check network connectivity
docker network ls | grep lucid
```

### **Debug Commands**
```powershell
# Check for build contexts
grep -r "build:" infrastructure/compose/

# Check for non-distroless images
grep -r "FROM.*slim\|FROM.*alpine" */Dockerfile*

# Verify pull policies
grep -r "pull_policy: always" infrastructure/compose/
```

---

## **BEST PRACTICES**

### **1. Development**
- Always use distroless base images
- Test locally with simple builds first
- Validate compliance before committing
- Use multi-stage builds for complex dependencies

### **2. Building**
- Use `--no-cache` for production builds
- Build for multiple platforms
- Verify images before pushing
- Tag images with semantic versions

### **3. Deployment**
- Use compose files for orchestration
- Pull images from registry
- Use standardized networks and volumes
- Include health checks for all services

### **4. Maintenance**
- Regular compliance audits
- Update distroless base images
- Monitor for security vulnerabilities
- Keep documentation current

---

## **RESOURCES**

### **Documentation**
- [Project Regulations](PROJECT_REGULATIONS.md) - Complete regulation details
- [Build Guide](LAYER2_BUILD_GUIDE.md) - Layer-specific build instructions
- [Deployment Guide](LAYER2_SIMPLE_DEPLOYMENT.md) - Deployment procedures

### **Scripts**
- `scripts/validate-compliance.ps1` - Compliance validation
- `scripts/enforce-compliance.ps1` - Compliance enforcement
- `scripts/build-compliant.ps1` - Compliant image building

### **Examples**
- `infrastructure/compose/lucid-layer1-complete.yaml` - Layer 1 deployment
- `infrastructure/compose/lucid-layer2-complete.yaml` - Layer 2 deployment
- `infrastructure/compose/docker-compose.yml` - Main deployment

---

**This guide ensures all Lucid project development follows professional standards and security best practices.**
