# Lucid API - SBOM Generation Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | LUCID-SEC-SBOM-001 |
| Version | 1.0.0 |
| Status | ACTIVE |
| Last Updated | 2025-10-14 |
| Owner | Security Team |

---

## Overview

This guide provides comprehensive instructions for generating, verifying, and managing Software Bill of Materials (SBOM) for all Lucid API containers. SBOM generation is a critical component of our supply chain security and compliance strategy.

### What is an SBOM?

A Software Bill of Materials (SBOM) is a formal, machine-readable inventory of all components, libraries, and dependencies used in a software application. It provides transparency into the software supply chain and enables vulnerability tracking and compliance verification.

### Why SBOMs are Critical

1. **Vulnerability Management**: Quickly identify which containers are affected by newly discovered CVEs
2. **License Compliance**: Track all software licenses used in production
3. **Supply Chain Security**: Understand and verify all dependencies
4. **Incident Response**: Rapidly assess impact of security incidents
5. **Regulatory Compliance**: Meet requirements for NTIA, CISA, and other regulatory frameworks

---

## SBOM Standards

### Supported Formats

Lucid API generates SBOMs in multiple industry-standard formats:

#### 1. SPDX-JSON (Primary Format)
- **Standard**: Software Package Data Exchange (SPDX) 2.3
- **Format**: JSON
- **Use Case**: Vulnerability scanning, compliance
- **Specification**: https://spdx.github.io/spdx-spec/

#### 2. CycloneDX-JSON
- **Standard**: CycloneDX 1.4
- **Format**: JSON
- **Use Case**: OWASP dependency tracking, security analysis
- **Specification**: https://cyclonedx.org/

#### 3. Syft-JSON (Internal)
- **Standard**: Anchore Syft native format
- **Format**: JSON
- **Use Case**: Detailed analysis, debugging

---

## Prerequisites

### Required Tools

Install the following tools before generating SBOMs:

#### 1. Syft (SBOM Generator)
```bash
# Install Syft
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# Verify installation
syft version
```

#### 2. Grype (Vulnerability Scanner)
```bash
# Install Grype
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# Verify installation
grype version
```

#### 3. Trivy (Container Scanner)
```bash
# Install Trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Verify installation
trivy version
```

#### 4. jq (JSON Processor)
```bash
# On Ubuntu/Debian
sudo apt-get install jq

# On macOS
brew install jq

# Verify installation
jq --version
```

### Required Permissions

- Docker access to pull and inspect images
- Write access to `build/sbom/` directory
- Network access to pull container images

---

## SBOM Generation

### Quick Start

Generate SBOMs for Phase 1 (Foundation) containers:

```bash
# Navigate to project root
cd /path/to/Lucid

# Generate Phase 1 SBOMs (default)
./scripts/security/generate-sbom.sh

# Or explicitly specify Phase 1
./scripts/security/generate-sbom.sh --phase 1
```

### Generate SBOMs for All Phases

```bash
# Generate SBOMs for all containers across all phases
./scripts/security/generate-sbom.sh --all
```

### Generate SBOM for Single Container

```bash
# Generate SBOM for specific container
./scripts/security/generate-sbom.sh lucid-auth-service latest

# With custom format
./scripts/security/generate-sbom.sh --format cyclonedx-json lucid-api-gateway latest
```

### Phase-Specific Generation

```bash
# Phase 1: Foundation (MongoDB, Redis, Elasticsearch, Auth)
./scripts/security/generate-sbom.sh --phase 1

# Phase 2: Core Services (API Gateway, Blockchain)
./scripts/security/generate-sbom.sh --phase 2

# Phase 3: Application Services (Sessions, RDP, Nodes)
./scripts/security/generate-sbom.sh --phase 3

# Phase 4: Support Services (Admin, TRON Payment)
./scripts/security/generate-sbom.sh --phase 4
```

---

## SBOM Directory Structure

Generated SBOMs are organized by phase:

```
build/sbom/
├── phase1/
│   ├── lucid-mongodb-latest-sbom.spdx-json
│   ├── lucid-mongodb-latest-sbom.cyclonedx.json
│   ├── lucid-mongodb-latest-sbom.syft.json
│   ├── lucid-mongodb-summary.txt
│   ├── lucid-redis-latest-sbom.spdx-json
│   ├── lucid-elasticsearch-latest-sbom.spdx-json
│   └── lucid-auth-service-latest-sbom.spdx-json
├── phase2/
│   ├── lucid-api-gateway-latest-sbom.spdx-json
│   ├── lucid-blockchain-engine-latest-sbom.spdx-json
│   └── ...
├── phase3/
│   ├── lucid-session-pipeline-latest-sbom.spdx-json
│   └── ...
├── phase4/
│   ├── lucid-admin-interface-latest-sbom.spdx-json
│   ├── lucid-tron-client-latest-sbom.spdx-json
│   └── ...
├── reports/
│   └── sbom-generation-report-20251014_143025.txt
└── archive/
    └── 20251014_143025/
        └── ...
```

---

## SBOM Verification

### Verify All SBOMs

```bash
# Verify all generated SBOMs
./scripts/security/verify-sbom.sh --all
```

### Verify Single SBOM

```bash
# Verify specific SBOM file
./scripts/security/verify-sbom.sh build/sbom/phase1/lucid-auth-service-latest-sbom.spdx-json
```

### Verification Checks

The verification script checks:

1. **Valid JSON Format**: Ensures SBOM is well-formed JSON
2. **Package Count**: Verifies SBOM contains packages
3. **File Size**: Checks for suspiciously small files
4. **Structure Validation**: Confirms required SBOM fields exist

---

## Vulnerability Scanning

### Scan Containers with Trivy

```bash
# Scan specific container
./scripts/security/scan-vulnerabilities.sh --container lucid-auth-service

# Scan all Phase 1 containers
./scripts/security/scan-vulnerabilities.sh --phase 1

# Scan all containers
./scripts/security/scan-vulnerabilities.sh --all
```

### Scan SBOMs with Grype

```bash
# Scan all generated SBOMs
./scripts/security/scan-vulnerabilities.sh --sboms
```

### Vulnerability Scan Output

Scans generate detailed reports:

```
build/security-scans/
├── trivy/
│   ├── lucid-auth-service-trivy-20251014_143025.json
│   └── ...
├── grype/
│   ├── lucid-auth-service-grype-20251014_143025.json
│   └── ...
└── reports/
    └── vulnerability-report-20251014_143025.md
```

---

## Security Compliance Check

### Run Full Compliance Check

```bash
# Run comprehensive security compliance verification
./scripts/security/security-compliance-check.sh
```

### Compliance Checks Performed

1. **SBOM Generation**: Verifies all required SBOMs exist
2. **CVE Vulnerability Scanning**: Checks for critical vulnerabilities
3. **Container Security**: Validates distroless images, non-root users
4. **TRON Isolation**: Ensures TRON code is properly isolated
5. **Authentication Security**: Verifies JWT, hardware wallet, RBAC
6. **Documentation**: Checks for required security documentation
7. **CI/CD Integration**: Validates security scanning in pipelines
8. **Secrets Management**: Verifies proper secrets handling

### Compliance Report

```
build/compliance/reports/
└── security-compliance-20251014_143025.md
```

---

## CI/CD Integration

### GitHub Actions Workflow

Add SBOM generation to your GitHub Actions workflow:

```yaml
name: Build and Generate SBOM

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build-and-sbom:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Build container
        run: |
          docker build -t lucid-auth-service:latest -f auth/Dockerfile .
      
      - name: Install Syft
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
      
      - name: Generate SBOM
        run: |
          ./scripts/security/generate-sbom.sh lucid-auth-service latest
      
      - name: Install Grype
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin
      
      - name: Scan for vulnerabilities
        run: |
          grype sbom:build/sbom/phase1/lucid-auth-service-latest-sbom.spdx-json
      
      - name: Upload SBOM artifacts
        uses: actions/upload-artifact@v3
        with:
          name: sboms
          path: build/sbom/
```

---

## SBOM Best Practices

### 1. Generate SBOMs on Every Build

Always generate SBOMs as part of your container build process:

```bash
# Build container
docker build -t lucid-auth-service:latest .

# Generate SBOM immediately
./scripts/security/generate-sbom.sh lucid-auth-service latest

# Scan for vulnerabilities
./scripts/security/scan-vulnerabilities.sh --container lucid-auth-service
```

### 2. Version Your SBOMs

Include version tags in SBOM filenames:

```bash
# Generate SBOM with version
./scripts/security/generate-sbom.sh lucid-auth-service v1.2.3
```

### 3. Archive Historical SBOMs

Keep historical SBOMs for compliance and forensics:

- SBOMs are automatically archived in `build/sbom/archive/`
- Configure retention period in `configs/security/sbom-config.yml`

### 4. Automate Vulnerability Scanning

Set up automated daily scans:

```bash
# Add to crontab for daily scans at 2 AM
0 2 * * * /path/to/Lucid/scripts/security/scan-vulnerabilities.sh --all
```

### 5. Fail Builds on Critical CVEs

Configure your CI/CD to fail on critical vulnerabilities:

```yaml
- name: Scan and fail on critical
  run: |
    ./scripts/security/scan-vulnerabilities.sh --container lucid-auth-service
    # Script exits with non-zero on critical CVEs
```

---

## Troubleshooting

### Issue: Syft Not Found

**Solution**:
```bash
# Install Syft
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# Verify
syft version
```

### Issue: Container Image Not Found

**Solution**:
```bash
# Pull the image first
docker pull lucid/lucid-auth-service:latest

# Or build it locally
docker build -t lucid/lucid-auth-service:latest -f auth/Dockerfile .

# Then generate SBOM
./scripts/security/generate-sbom.sh lucid-auth-service latest
```

### Issue: SBOM Generation Fails

**Solution**:
```bash
# Run with verbose output
set -x
./scripts/security/generate-sbom.sh lucid-auth-service latest

# Check Syft directly
syft lucid/lucid-auth-service:latest -o spdx-json
```

### Issue: Permission Denied

**Solution**:
```bash
# Make script executable
chmod +x scripts/security/generate-sbom.sh
chmod +x scripts/security/verify-sbom.sh
chmod +x scripts/security/scan-vulnerabilities.sh
chmod +x scripts/security/security-compliance-check.sh

# Create SBOM directory
mkdir -p build/sbom
```

---

## SBOM Maintenance

### Regular Updates

1. **Weekly**: Generate fresh SBOMs for all containers
2. **On Dependency Changes**: Regenerate SBOMs when dependencies update
3. **Before Releases**: Generate and scan SBOMs before production deployment
4. **Security Advisories**: Scan SBOMs when new CVEs are published

### Cleanup Old SBOMs

```bash
# Archive is managed automatically
# Configure retention in configs/security/sbom-config.yml

# Manual cleanup (keeps last 90 days)
find build/sbom/archive -type d -mtime +90 -exec rm -rf {} +
```

---

## Compliance Requirements

### NTIA Minimum Elements

Our SBOMs include all NTIA-required minimum elements:

1. ✅ **Supplier Name**: Container image provider
2. ✅ **Component Name**: Package/library names
3. ✅ **Version**: Package versions
4. ✅ **Dependencies**: Full dependency tree
5. ✅ **Author**: SBOM creator information
6. ✅ **Timestamp**: Generation timestamp
7. ✅ **SBOM Serial Number**: Unique identifier

### CISA Requirements

Compliant with CISA software supply chain guidance:

- ✅ Machine-readable format (SPDX, CycloneDX)
- ✅ Automated generation
- ✅ Vulnerability scanning integration
- ✅ Version control and archiving

---

## References

### Standards Documentation

- [SPDX Specification](https://spdx.github.io/spdx-spec/)
- [CycloneDX Specification](https://cyclonedx.org/)
- [NTIA SBOM Minimum Elements](https://www.ntia.gov/report/2021/minimum-elements-software-bill-materials-sbom)
- [CISA Software Supply Chain](https://www.cisa.gov/sbom)

### Tools Documentation

- [Syft Documentation](https://github.com/anchore/syft)
- [Grype Documentation](https://github.com/anchore/grype)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)

### Project Documentation

- [Master Build Plan](../../plan/API_plans/00-master-architecture/01-MASTER_BUILD_PLAN.md)
- [Build Requirements Guide](../../plan/API_plans/00-master-architecture/13-BUILD_REQUIREMENTS_GUIDE.md)
- [Security Compliance Guide](./security-compliance-guide.md)

---

## Support

For questions or issues related to SBOM generation:

1. Check this guide first
2. Review error messages in `build/sbom/reports/`
3. Check tool versions: `syft version`, `grype version`, `trivy version`
4. Review configuration: `configs/security/sbom-config.yml`
5. Contact security team: security@lucid.io

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-10-14  
**Next Review**: 2025-11-14

