# Legacy Dockerfiles Archive

## Overview

This directory contains archived legacy Dockerfiles that were replaced by modern distroless builds for improved security and performance.

## Migration Details

**Migration Date:** January 9, 2025
**Migration Reason:** Standardization on distroless builds for enhanced security and Pi optimization

## Archived Files

### Gateway Service

- **File:** `gateway/Dockerfile.gateway`

- **Original Location:** `03-api-gateway/gateway/Dockerfile.gateway`

- **Replaced By:** `03-api-gateway/gateway/Dockerfile` (distroless version)

### API Service

- **File:** `api/Dockerfile.api`

- **Original Location:** `03-api-gateway/api/Dockerfile.api`

- **Replaced By:** `03-api-gateway/api/Dockerfile` (distroless version)

## Key Differences

### Legacy Builds

- Full Alpine/Debian base images with package managers

- Larger attack surface with unnecessary tools

- Standard multi-stage builds

- More complex dependency management

### Distroless Builds

- Minimal runtime images (gcr.io/distroless/*)

- Reduced attack surface (no shell, package managers, or unnecessary binaries)

- Optimized for Raspberry Pi deployment

- Enhanced security with non-root user execution

- Professional metadata and labeling

## Benefits of Distroless Migration

1. **Security Enhancement**

   - Minimal attack surface

   - No shell access in runtime containers

   - Reduced CVE exposure

1. **Performance Optimization**

   - Smaller image sizes

   - Faster container startup

   - Better resource utilization on Pi

1. **Professional Standards**

   - Industry best practices

   - Better container scanning results

   - Compliance with security policies

## Rollback Procedure

If rollback is needed:

1. **Copy legacy files back:**

   ```bash

   cp 03-api-gateway/legacy/gateway/Dockerfile.gateway 03-api-gateway/gateway/
   cp 03-api-gateway/legacy/api/Dockerfile.api 03-api-gateway/api/

   ```

1. **Rename current distroless files:**

   ```bash

   mv 03-api-gateway/gateway/Dockerfile 03-api-gateway/gateway/Dockerfile.distroless
   mv 03-api-gateway/api/Dockerfile 03-api-gateway/api/Dockerfile.distroless

   ```

1. **Update any build scripts or compose files** to reference the legacy Dockerfiles

## Technical Notes

- Legacy files maintain full functionality

- Both versions use multi-stage builds

- Distroless versions include Pi-specific optimizations

- All security headers and configurations preserved in distroless builds

## Contact

For questions about this migration, contact the Lucid Development Team.
