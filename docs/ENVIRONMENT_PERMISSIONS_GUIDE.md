# LUCID Environment File Permissions Guide

## Overview

This guide explains the permission system for environment files in the LUCID project, ensuring proper security for sensitive configuration data while maintaining accessibility for regular environment files.

## Permission Categories

### Regular Environment Files (664 permissions)
**Permission**: `rw-rw-r--` (664)  
**Purpose**: Standard environment files for development, staging, production, and testing  
**Security Level**: Standard - readable by group and others

**Files with 664 permissions:**
- `env.development`
- `env.staging`
- `env.production`
- `env.test`
- `env.coordination.yml`
- `env.foundation`
- `env.core`
- `env.application`
- `env.support`
- `env.gui`
- `env.pi-build`
- `layer2.env`
- `layer2-simple.env`
- All service-specific environment files (`.env.api-gateway`, `.env.authentication`, etc.)

### Secure Secret Files (600 permissions)
**Permission**: `rw-------` (600)  
**Purpose**: Files containing secrets, passwords, API keys, or sensitive data  
**Security Level**: High - readable/writable only by owner

**Files with 600 permissions:**
- `.env.secrets`
- `.env.secure`
- `.env.tron-secrets`
- Any file with "secrets" in the name
- Files in `/configs/secrets/` directory

## File Locations

### Primary Environment Directory
```
/mnt/myssd/Lucid/Lucid/configs/environment/
├── env.development          # 664
├── env.staging              # 664
├── env.production           # 664
├── env.test                 # 664
├── env.coordination.yml     # 664
├── env.foundation           # 664
├── env.core                 # 664
├── env.application          # 664
├── env.support              # 664
├── env.gui                  # 664
├── env.pi-build             # 664
├── layer2.env               # 664
├── layer2-simple.env        # 664
├── .env.secrets             # 600
├── .env.secure              # 600
├── .env.tron-secrets         # 600
├── development/             # 664 (directory)
├── production/              # 664 (directory)
├── staging/                 # 664 (directory)
└── pi/                      # 664 (directory)
```

### Service-Specific Environment Files
```
/mnt/myssd/Lucid/Lucid/configs/environment/
├── .env.api-gateway         # 664
├── .env.api-server          # 664
├── .env.authentication      # 664
├── .env.authentication-service-distroless # 664
├── .env.orchestrator        # 664
├── .env.chunker             # 664
├── .env.merkle-builder      # 664
├── .env.tor-proxy           # 664
├── .env.tunnel-tools        # 664
├── .env.server-tools        # 664
├── .env.openapi-gateway     # 664
├── .env.openapi-server      # 664
├── .env.blockchain-api      # 664
├── .env.blockchain-governance # 664
├── .env.tron-client         # 664
├── .env.tron-payout-router  # 664
├── .env.tron-wallet-manager # 664
├── .env.tron-usdt-manager   # 664
├── .env.tron-staking        # 664
└── .env.tron-payment-gateway # 664
```

### Secrets Directory
```
/mnt/myssd/Lucid/Lucid/configs/secrets/
├── .env.secrets             # 600
├── .env.secure              # 600
└── .env.tron-secrets         # 600
```

### Additional Locations
```
/mnt/myssd/Lucid/Lucid/03-api-gateway/api/
└── *.env*                   # 664

/mnt/myssd/Lucid/Lucid/sessions/core/
└── *.env*                   # 664
```

## Scripts

### Setting Permissions
**Script**: `scripts/set-env-permissions.sh`  
**Purpose**: Sets appropriate permissions for all environment files  
**Usage**: 
```bash
# Run on Raspberry Pi
./scripts/set-env-permissions.sh
```

**Features**:
- Automatically detects file types and sets appropriate permissions
- Handles both individual files and directories
- Searches for files with "secrets" in the name
- Provides detailed logging and error handling
- Verifies file existence before setting permissions

### Verifying Permissions
**Script**: `scripts/verify-env-permissions.sh`  
**Purpose**: Verifies that all environment files have correct permissions  
**Usage**:
```bash
# Run on Raspberry Pi
./scripts/verify-env-permissions.sh
```

**Features**:
- Checks all environment files for correct permissions
- Provides detailed report of permission status
- Identifies files with incorrect permissions
- Reports missing files
- Returns exit code 0 for success, 1 for issues

## Security Considerations

### Why 664 for Regular Files?
- **Readable by group**: Allows team members to access configuration
- **Readable by others**: Enables system processes to read environment variables
- **Writable by owner and group**: Allows collaborative editing
- **Not executable**: Prevents accidental execution

### Why 600 for Secret Files?
- **Readable only by owner**: Prevents unauthorized access to sensitive data
- **Writable only by owner**: Prevents unauthorized modification
- **Not accessible by group or others**: Maximum security for secrets
- **Not executable**: Prevents accidental execution

## Best Practices

### File Naming Conventions
- Use `.env.secrets` for files containing secrets
- Use `.env.secure` for files with sensitive configuration
- Include "secrets" in filename for automatic 600 permission assignment
- Use descriptive names for service-specific files

### Permission Management
- Run permission scripts after creating new environment files
- Verify permissions before deployment
- Use the verification script in CI/CD pipelines
- Regularly audit file permissions

### Security Guidelines
- Never commit secret files to version control
- Use environment variable substitution for sensitive values
- Rotate secrets regularly
- Monitor file permission changes
- Use proper file ownership (chown)

## Troubleshooting

### Common Issues

**Permission Denied Errors**:
```bash
# Check current permissions
ls -la /mnt/myssd/Lucid/Lucid/configs/environment/

# Fix permissions
./scripts/set-env-permissions.sh
```

**Files Not Found**:
```bash
# Verify file paths
find /mnt/myssd/Lucid/Lucid -name "*.env*" -type f

# Check if files exist in expected locations
ls -la /mnt/myssd/Lucid/Lucid/configs/environment/
```

**Incorrect Permissions**:
```bash
# Verify current permissions
./scripts/verify-env-permissions.sh

# Fix permissions
./scripts/set-env-permissions.sh
```

### Manual Permission Setting

**Set Regular Environment File**:
```bash
chmod 664 /mnt/myssd/Lucid/Lucid/configs/environment/env.production
```

**Set Secret File**:
```bash
chmod 600 /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
```

**Set Directory Permissions**:
```bash
chmod 664 /mnt/myssd/Lucid/Lucid/configs/environment/
find /mnt/myssd/Lucid/Lucid/configs/environment/ -type f -name "*.env*" -exec chmod 664 {} \;
```

## Integration with CI/CD

### Pre-deployment Check
```bash
#!/bin/bash
# Check permissions before deployment
if ./scripts/verify-env-permissions.sh; then
    echo "Permissions verified, proceeding with deployment"
    # Continue with deployment
else
    echo "Permission issues detected, aborting deployment"
    exit 1
fi
```

### Post-deployment Verification
```bash
#!/bin/bash
# Verify permissions after deployment
./scripts/verify-env-permissions.sh
if [ $? -eq 0 ]; then
    echo "All permissions correctly set"
else
    echo "Permission issues detected, fixing..."
    ./scripts/set-env-permissions.sh
fi
```

## Monitoring and Auditing

### Regular Permission Audits
```bash
# Create audit log
./scripts/verify-env-permissions.sh > /var/log/lucid-permissions-audit.log 2>&1

# Check for permission changes
find /mnt/myssd/Lucid/Lucid/configs/ -name "*.env*" -type f -exec stat -c "%a %n" {} \; > /tmp/permissions-snapshot.txt
```

### Automated Monitoring
```bash
# Add to crontab for daily permission checks
0 2 * * * /mnt/myssd/Lucid/Lucid/scripts/verify-env-permissions.sh >> /var/log/lucid-permissions.log 2>&1
```

## Conclusion

Proper permission management is essential for maintaining security in the LUCID project. The provided scripts automate the process while ensuring that sensitive data remains protected and regular configuration files remain accessible. Regular verification and monitoring help maintain the security posture of the environment configuration system.
