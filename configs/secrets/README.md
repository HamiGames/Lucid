# Lucid Secrets Management

## Overview

This directory contains the secret management configuration and documentation for the Lucid blockchain system. All secrets are managed securely with encryption, rotation, and audit logging.

## Security Principles

### 🔐 Never Commit Secrets
- **NEVER** commit `.secrets` files to version control
- Use `.secrets.example` as a template only
- All actual secrets must be stored securely outside the repository

### 🔄 Regular Rotation
- JWT secrets: Every 90 days
- Database passwords: Every 180 days  
- TRON private keys: Every 365 days
- Admin secrets: Every 90 days
- Session secrets: Every 30 days

### 🛡️ Encryption at Rest
- All secrets encrypted with AES-256-GCM
- Key derivation using PBKDF2 with 100,000 iterations
- Separate encryption keys for different secret categories

## Directory Structure

```
configs/secrets/
├── .secrets.example          # Template file (safe to commit)
├── .secrets                  # Actual secrets (NEVER commit)
├── .secrets.encrypted        # Encrypted secrets backup
├── README.md                 # This documentation
└── rotation-log/             # Secret rotation audit logs
    ├── jwt-rotation.log
    ├── database-rotation.log
    └── tron-rotation.log
```

## Secret Categories

### 1. JWT Secrets
- **Purpose**: Authentication token signing
- **Rotation**: 90 days
- **Format**: 256-bit base64 encoded
- **Usage**: API Gateway, Authentication service

### 2. Database Secrets
- **Purpose**: MongoDB, Redis, Elasticsearch authentication
- **Rotation**: 180 days
- **Format**: Strong passwords (32+ characters)
- **Usage**: All database connections

### 3. TRON Payment Secrets
- **Purpose**: TRON network integration (isolated cluster)
- **Rotation**: 365 days
- **Format**: Encrypted private keys
- **Usage**: TRON payment processing only

### 4. Hardware Wallet Secrets
- **Purpose**: Hardware wallet integration
- **Rotation**: 180 days
- **Format**: Application IDs and certificates
- **Usage**: Authentication service

### 5. Service Mesh Secrets
- **Purpose**: Inter-service communication
- **Rotation**: 90 days
- **Format**: mTLS certificates and JWT secrets
- **Usage**: Cross-cluster integration

### 6. Admin Interface Secrets
- **Purpose**: Admin dashboard authentication
- **Rotation**: 90 days
- **Format**: JWT secrets and API keys
- **Usage**: Admin interface cluster

### 7. Blockchain Secrets
- **Purpose**: Lucid blockchain consensus
- **Rotation**: 180 days
- **Format**: Validator private keys
- **Usage**: Blockchain core cluster

### 8. Session Management Secrets
- **Purpose**: Session encryption and signing
- **Rotation**: 30 days
- **Format**: AES-256 encryption keys
- **Usage**: Session management cluster

### 9. RDP Service Secrets
- **Purpose**: RDP connection authentication
- **Rotation**: 90 days
- **Format**: Passwords and session keys
- **Usage**: RDP services cluster

### 10. Node Management Secrets
- **Purpose**: Node operator authentication
- **Rotation**: 90 days
- **Format**: Private keys and tokens
- **Usage**: Node management cluster

## Secret Generation

### Automated Generation
Use the provided scripts for secure secret generation:

```bash
# Generate all secrets
./scripts/secrets/generate-secrets.sh

# Generate specific secret types
./scripts/secrets/generate-secrets.sh --type jwt
./scripts/secrets/generate-secrets.sh --type database
./scripts/secrets/generate-secrets.sh --type tron
```

### Manual Generation
For manual secret generation:

```bash
# JWT Secret (256-bit)
openssl rand -base64 64

# Database Password (32+ characters)
openssl rand -base64 48

# API Key (32 bytes)
openssl rand -hex 32

# Private Key (4096-bit RSA)
openssl genrsa -out private.key 4096
```

## Secret Rotation

### Automatic Rotation
Secrets are automatically rotated based on their category:

```bash
# Check rotation status
./scripts/secrets/rotate-secrets.sh --check

# Force rotation
./scripts/secrets/rotate-secrets.sh --force

# Rotate specific type
./scripts/secrets/rotate-secrets.sh --type jwt
```

### Manual Rotation
For manual rotation:

1. **Backup current secrets**:
   ```bash
   ./scripts/secrets/encrypt-secrets.sh --backup
   ```

2. **Generate new secrets**:
   ```bash
   ./scripts/secrets/generate-secrets.sh --type <secret-type>
   ```

3. **Update services**:
   ```bash
   ./scripts/secrets/rotate-secrets.sh --type <secret-type>
   ```

4. **Verify rotation**:
   ```bash
   ./scripts/secrets/rotate-secrets.sh --verify
   ```

## Secret Encryption

### Encryption Process
All secrets are encrypted before storage:

```bash
# Encrypt secrets
./scripts/secrets/encrypt-secrets.sh

# Decrypt secrets (for service use)
./scripts/secrets/encrypt-secrets.sh --decrypt

# Backup encrypted secrets
./scripts/secrets/encrypt-secrets.sh --backup
```

### Encryption Configuration
- **Algorithm**: AES-256-GCM
- **Key Derivation**: PBKDF2 with 100,000 iterations
- **Salt**: Random 32-byte salt per secret
- **IV**: Random 12-byte IV per encryption

## Environment Integration

### Development Environment
For development, use the example template:

```bash
# Copy template
cp .secrets.example .secrets

# Edit with development values
nano .secrets
```

### Production Environment
For production, use secure secret management:

```bash
# Load from secure vault
./scripts/secrets/generate-secrets.sh --vault

# Use environment variables
export JWT_SECRET_KEY=$(vault kv get -field=jwt_secret secret/lucid)
```

## Security Compliance

### Audit Logging
All secret operations are logged:

- Secret generation
- Secret rotation
- Secret access
- Failed authentication attempts
- Security violations

### Access Control
- Secrets directory: 700 permissions
- Secret files: 600 permissions
- Scripts: 755 permissions
- Logs: 644 permissions

### Backup and Recovery
- Encrypted backups stored securely
- Multiple backup locations
- Regular backup verification
- Disaster recovery procedures

## Troubleshooting

### Common Issues

#### 1. Secret Not Found
```bash
# Check if secrets file exists
ls -la .secrets

# Regenerate if missing
./scripts/secrets/generate-secrets.sh
```

#### 2. Invalid Secret Format
```bash
# Validate secret format
./scripts/secrets/generate-secrets.sh --validate

# Regenerate with correct format
./scripts/secrets/generate-secrets.sh --type <secret-type>
```

#### 3. Service Authentication Failed
```bash
# Check secret rotation status
./scripts/secrets/rotate-secrets.sh --check

# Rotate if expired
./scripts/secrets/rotate-secrets.sh --type <secret-type>
```

#### 4. Encryption/Decryption Errors
```bash
# Check encryption key
./scripts/secrets/encrypt-secrets.sh --check-key

# Re-encrypt secrets
./scripts/secrets/encrypt-secrets.sh --re-encrypt
```

### Log Files
Check rotation logs for issues:

```bash
# JWT rotation logs
tail -f rotation-log/jwt-rotation.log

# Database rotation logs
tail -f rotation-log/database-rotation.log

# TRON rotation logs
tail -f rotation-log/tron-rotation.log
```

## Best Practices

### 1. Secret Generation
- Use cryptographically secure random generators
- Generate secrets with sufficient entropy
- Use different secrets for different environments
- Never reuse secrets across services

### 2. Secret Storage
- Encrypt all secrets at rest
- Use secure key management systems
- Implement proper access controls
- Regular security audits

### 3. Secret Rotation
- Rotate secrets regularly
- Implement automated rotation where possible
- Maintain secret history for rollback
- Test rotation procedures

### 4. Secret Distribution
- Use secure channels for secret distribution
- Implement secret versioning
- Monitor secret usage
- Log all secret access

### 5. Incident Response
- Have secret rotation procedures ready
- Maintain emergency secret access
- Document incident response procedures
- Regular security drills

## Compliance Standards

### Security Standards
- **NIST SP 800-57**: Key management guidelines
- **FIPS 140-2**: Cryptographic module standards
- **ISO 27001**: Information security management
- **SOC 2**: Security and availability controls

### Audit Requirements
- All secret operations logged
- Regular security assessments
- Compliance monitoring
- Incident reporting

## Support

For secret management support:

1. **Documentation**: Check this README and inline comments
2. **Scripts**: Use `--help` flag with any script
3. **Logs**: Check rotation logs for errors
4. **Security**: Report security issues immediately

## Version History

- **v1.0.0**: Initial secret management implementation
- **v1.1.0**: Added TRON payment secrets
- **v1.2.0**: Enhanced encryption and rotation
- **v1.3.0**: Added audit logging and compliance

---

**⚠️ SECURITY WARNING**: This directory contains sensitive information. Never commit actual secrets to version control. Always use the example template and generate real secrets securely.
