# Lucid Environment Setup Documentation

## Overview
This document describes the fixed environment setup system for the Lucid project, addressing the issues with Windows-based paths, incorrect file locations, and inconsistent naming.

## Issues Fixed

### 1. Windows-based Code Context
- **Problem**: Scripts were using Windows-style paths and commands
- **Solution**: Updated all scripts to use Linux/Unix paths and commands
- **Files**: All scripts now use proper Linux path separators and commands

### 2. Incorrect File Paths
- **Problem**: .env files were being created in wrong locations
- **Solution**: Implemented global path variables and correct directory structure
- **New Structure**:
  - Project Root: `/mnt/myssd/Lucid/Lucid/`
  - Environment Files: `/mnt/myssd/Lucid/Lucid/configs/environment/`
  - Scripts Config: `/mnt/myssd/Lucid/Lucid/scripts/config/`
  - Scripts: `/mnt/myssd/Lucid/Lucid/scripts/`

### 3. Missing Global Path Variables
- **Problem**: No centralized path management
- **Solution**: Created global path configuration system
- **Files**: `scripts/config/lucid-paths.conf` contains all path variables

### 4. Inconsistent .env File Naming
- **Problem**: Mixed naming conventions for environment files
- **Solution**: Standardized to `.env.*` format
- **Files**: All environment files now use consistent naming

## Script Architecture

### 1. Master Setup Script
**File**: `scripts/setup-lucid-env.sh`
**Purpose**: Master script that orchestrates the entire environment setup
**Usage**: 
```bash
bash scripts/setup-lucid-env.sh
```

### 2. Path Setup Script
**File**: `scripts/config/setup-paths.sh`
**Purpose**: Creates directory structure and global path configuration
**Features**:
- Creates all required directories
- Generates `lucid-paths.conf` with global path variables
- Creates environment file templates
- Validates directory structure

### 3. Environment Generation Script
**File**: `sessions/core/generate-env.sh`
**Purpose**: Generates secure environment files for Session Core services
**Features**:
- Generates cryptographically secure values
- Creates `.env.orchestrator`, `.env.chunker`, `.env.merkle_builder`
- Saves secrets to `.env.sessions.secrets`
- Validates all placeholders are replaced

## Directory Structure

```
/mnt/myssd/Lucid/Lucid/
├── configs/
│   └── environment/
│       ├── .env.orchestrator
│       ├── .env.chunker
│       ├── .env.merkle_builder
│       ├── .env.sessions.secrets
│       ├── .env.secure.template
│       └── .env.application.template
├── scripts/
│   ├── setup-lucid-env.sh
│   └── config/
│       ├── setup-paths.sh
│       └── lucid-paths.conf
└── sessions/
    └── core/
        └── generate-env.sh
```

## Usage Instructions

### Quick Setup
Run the master script to set up everything:
```bash
bash scripts/setup-lucid-env.sh
```

### Manual Setup
If you prefer to run steps individually:

1. **Setup Paths**:
   ```bash
   bash scripts/config/setup-paths.sh
   ```

2. **Generate Environment Files**:
   ```bash
   bash sessions/core/generate-env.sh
   ```

### Using Path Configuration
To use the global path variables in other scripts:
```bash
# Load path configuration
source scripts/config/lucid-paths.conf

# Use the variables
echo "Project root: $PROJECT_ROOT"
echo "Environment config: $ENV_CONFIG_DIR"
```

## Environment Files Generated

### 1. `.env.orchestrator`
- Session orchestrator service configuration
- Port: 8090
- Database: MongoDB (lucid_sessions)
- Cache: Redis

### 2. `.env.chunker`
- Session chunker service configuration
- Port: 8092
- Database: MongoDB (lucid_chunks)
- Cache: Redis

### 3. `.env.merkle_builder`
- Merkle tree builder service configuration
- Port: 8094
- Database: MongoDB (lucid_merkle)
- Cache: Redis

### 4. `.env.sessions.secrets`
- Contains all generated secure values
- **WARNING**: Keep this file secure (chmod 600)
- **WARNING**: Never commit to version control

## Security Features

### Generated Secure Values
- **MongoDB Password**: 32-byte base64 encoded
- **Redis Password**: 32-byte base64 encoded
- **JWT Secret**: 64-byte base64 encoded
- **Encryption Key**: 256-bit hex key
- **Session Secret**: 32-byte base64 encoded
- **HMAC Key**: 32-byte base64 encoded
- **Signing Key**: 256-bit hex key

### Security Best Practices
- All secrets are cryptographically secure
- Secrets file has restricted permissions (600)
- Placeholders are validated and replaced
- No hardcoded secrets in templates

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Ensure scripts are executable: `chmod +x script-name.sh`
   - Check directory permissions

2. **Path Not Found**
   - Verify project root path is correct
   - Run `setup-paths.sh` first

3. **Placeholders Not Replaced**
   - Check if secure values were generated
   - Verify sed command compatibility

4. **Missing Directories**
   - Run `setup-paths.sh` to create directory structure
   - Check parent directory permissions

### Validation Commands

Check if all files exist:
```bash
ls -la /mnt/myssd/Lucid/Lucid/configs/environment/
```

Check script permissions:
```bash
ls -la scripts/setup-lucid-env.sh
ls -la scripts/config/setup-paths.sh
ls -la sessions/core/generate-env.sh
```

## Maintenance

### Regular Tasks
1. **Rotate Secrets**: Regenerate environment files periodically
2. **Backup Secrets**: Keep secure backup of `.env.sessions.secrets`
3. **Update Templates**: Modify templates as needed
4. **Monitor Logs**: Check script execution logs

### Adding New Services
1. Add new service configuration to `generate-env.sh`
2. Update path configuration if needed
3. Test with new service environment file
4. Update documentation

## Support

For issues or questions:
1. Check this documentation first
2. Verify all paths are correct for your system
3. Ensure all required directories exist
4. Check script permissions and execution rights
