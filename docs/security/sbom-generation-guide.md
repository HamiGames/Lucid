# Lucid API - SBOM Generation Guide

## Overview

This guide explains how to generate, verify, and manage Software Bills of Materials (SBOMs) for the Lucid API project. SBOMs are critical for supply chain security and compliance.

## Prerequisites

### Required Tools

1. **Syft** - For SBOM generation
   ```bash
   curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
   ```

2. **jq** - For JSON processing
   ```bash
   # Ubuntu/Debian
   sudo apt-get install jq
   
   # macOS
   brew install jq
   
   # CentOS/RHEL
   sudo yum install jq
   ```

3. **Docker** - For container operations
   ```bash
   # Install Docker Desktop or Docker Engine
   ```

## SBOM Generation

### Basic Usage

Generate SBOMs for Phase 1 containers:

```bash
# Generate SBOMs for all Phase 1 containers
./scripts/security/generate-sbom.sh --phase 1

# Archive old SBOMs before generating new ones
./scripts/security/generate-sbom.sh --phase 1 --archive
```

### Supported Formats

The script generates SBOMs in multiple formats:

- **SPDX JSON** (`.spdx-json`) - Industry standard format
- **CycloneDX JSON** (`.cyclonedx.json`) - OWASP standard format  
- **Syft JSON** (`.syft.json`) - Syft native format

### Output Structure

```
build/sbom/
├── phase1/
│   ├── mongodb-sbom.spdx-json
│   ├── mongodb-sbom.cyclonedx.json
│   ├── mongodb-sbom.syft.json
│   ├── redis-sbom.spdx-json
│   ├── redis-sbom.cyclonedx.json
│   ├── redis-sbom.syft.json
│   ├── elasticsearch-sbom.spdx-json
│   ├── elasticsearch-sbom.cyclonedx.json
│   ├── elasticsearch-sbom.syft.json
│   ├── auth-service-sbom.spdx-json
│   ├── auth-service-sbom.cyclonedx.json
│   ├── auth-service-sbom.syft.json
│   └── sbom_summary.json
└── archive/
    └── phase1_20250114_143022/
        └── [archived SBOMs]
```

## SBOM Verification

### Verify Generated SBOMs

```bash
# Verify all SBOMs in Phase 1 directory
./scripts/security/verify-sbom.sh --all

# Verify SBOMs in specific directory
./scripts/security/verify-sbom.sh --directory build/sbom/phase1
```

### Verification Checks

The verification script performs:

1. **JSON Validation** - Ensures valid JSON format
2. **Required Fields** - Checks for mandatory SBOM fields
3. **Package Count** - Verifies packages are listed
4. **Critical Packages** - Checks for essential components
5. **Format Compliance** - Validates format-specific requirements

## Vulnerability Scanning

### Scan Containers

```bash
# Scan all Phase 1 containers
./scripts/security/scan-vulnerabilities.sh --analyze

# Scan specific container
./scripts/security/scan-vulnerabilities.sh --container lucid-auth-service:latest

# Clean old scans before scanning
./scripts/security/scan-vulnerabilities.sh --clean --analyze
```

### Scan Results

Scan results are stored in:

```
build/security-scans/
├── trivy/
│   ├── mongodb-scan.json
│   ├── mongodb-scan.table
│   ├── mongodb-scan.sarif
│   ├── redis-scan.json
│   ├── redis-scan.table
│   ├── redis-scan.sarif
│   └── ...
└── reports/
    ├── vulnerability_summary.json
    └── security_compliance_report.json
```

## Security Compliance

### Run Compliance Check

```bash
# Run comprehensive security compliance check
./scripts/security/security-compliance-check.sh
```

### Compliance Scoring

The compliance check evaluates:

1. **SBOM Generation** (25 points)
   - SBOM files present
   - Multiple formats generated
   - Proper structure

2. **Vulnerability Scanning** (30 points)
   - Scan results available
   - Critical vulnerabilities = 0
   - High vulnerabilities ≤ 10

3. **Container Security** (25 points)
   - Distroless base images
   - Multi-stage builds
   - Security best practices

4. **Security Configuration** (20 points)
   - Security scripts present
   - Documentation available
   - Proper configuration

### Compliance Levels

- **EXCELLENT**: 90-100%
- **GOOD**: 80-89%
- **ACCEPTABLE**: 70-79%
- **NEEDS IMPROVEMENT**: 60-69%
- **FAILED**: 0-59%

## Integration with CI/CD

### GitHub Actions Integration

Add to your workflow:

```yaml
name: Security Compliance
on: [push, pull_request]

jobs:
  security-compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install dependencies
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
          sudo apt-get install jq
          curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
      
      - name: Build containers
        run: docker-compose build
      
      - name: Generate SBOMs
        run: ./scripts/security/generate-sbom.sh --phase 1
      
      - name: Scan vulnerabilities
        run: ./scripts/security/scan-vulnerabilities.sh --analyze
      
      - name: Check compliance
        run: ./scripts/security/security-compliance-check.sh
```

## Troubleshooting

### Common Issues

1. **Syft not found**
   ```bash
   # Install Syft
   curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
   ```

2. **jq not found**
   ```bash
   # Install jq
   sudo apt-get install jq
   ```

3. **Trivy not found**
   ```bash
   # Install Trivy
   curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
   ```

4. **Container not found**
   ```bash
   # Build containers first
   docker-compose build
   ```

### Debug Mode

Enable debug output:

```bash
# Set debug environment variable
export DEBUG=1

# Run with verbose output
./scripts/security/generate-sbom.sh --phase 1
```

## Best Practices

### SBOM Management

1. **Generate regularly** - Create SBOMs for each release
2. **Verify integrity** - Always verify generated SBOMs
3. **Archive old versions** - Keep historical SBOMs
4. **Multiple formats** - Generate in multiple standard formats

### Vulnerability Management

1. **Scan frequently** - Run scans on every build
2. **Address critical issues** - Fix CRITICAL vulnerabilities immediately
3. **Track trends** - Monitor vulnerability counts over time
4. **Document exceptions** - Justify any accepted vulnerabilities

### Compliance

1. **Set thresholds** - Define acceptable risk levels
2. **Monitor scores** - Track compliance over time
3. **Automate checks** - Integrate with CI/CD pipeline
4. **Regular reviews** - Review and update policies

## Future Enhancements

### Planned Features

1. **Container Image Signing** - Using Cosign
2. **SLSA Provenance** - Supply chain attestations
3. **Automated Notifications** - Email/Slack alerts
4. **Trend Analysis** - Historical vulnerability tracking
5. **Policy Enforcement** - Automated policy checks

### Integration Opportunities

1. **Container Registry** - Scan on push
2. **Security Scanners** - Additional scanning tools
3. **Compliance Frameworks** - SOC2, ISO27001
4. **Risk Assessment** - Automated risk scoring

## References

- [SPDX Specification](https://spdx.dev/)
- [CycloneDX Specification](https://cyclonedx.org/)
- [Syft Documentation](https://github.com/anchore/syft)
- [Trivy Documentation](https://github.com/aquasecurity/trivy)
- [OWASP SBOM](https://owasp.org/www-project-software-bill-of-materials/)