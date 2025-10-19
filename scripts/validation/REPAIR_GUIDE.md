# LUCID Project Validation Repair Guide

This guide explains how to use the LUCID project validation repair scripts to automatically fix common validation failures.

## Overview

The LUCID project includes comprehensive validation scripts that check:
- Python build alignment (distroless compliance, TRON isolation, security)
- Electron GUI alignment (file structure, TypeScript, API integration)
- Configuration files and build systems

When validations fail, the repair scripts can automatically fix many common issues.

## Quick Start

### 1. Run Validation First
```bash
# Check what needs to be fixed
./scripts/validation/validate-project.sh --verbose
```

### 2. Run Repair Script
```bash
# Fix all validation issues
./scripts/validation/repair-project.sh

# Or fix specific issues
./scripts/validation/repair-project.sh --python-only
./scripts/validation/repair-project.sh --gui-only
```

### 3. Verify Fixes
```bash
# Run validation again to confirm fixes
./scripts/validation/validate-project.sh
```

## Repair Script Options

### Main Repair Script (`repair-project.sh`)

```bash
./scripts/validation/repair-project.sh [OPTIONS]
```

**Options:**
- `--python-only` - Fix only Python build alignment issues
- `--gui-only` - Fix only Electron GUI alignment issues  
- `--verbose` - Show detailed output
- `--dry-run` - Show what would be fixed without making changes
- `--project-root PATH` - Set project root directory
- `--help` - Show help message

### Direct Python Script (`repair-validation-failures.py`)

```bash
python3 scripts/validation/repair-validation-failures.py [OPTIONS]
```

**Options:**
- `--python-only` - Fix only Python build alignment issues
- `--gui-only` - Fix only Electron GUI alignment issues
- `--verbose` - Show detailed output
- `--dry-run` - Show what would be fixed without making changes
- `--project-root PATH` - Set project root directory

## What Gets Fixed

### Python Build Alignment Issues

#### 1. Missing Dockerfiles
- **Issue**: Service directories missing Dockerfiles
- **Fix**: Creates distroless-based Dockerfiles with security best practices
- **Template**: Uses `gcr.io/distroless/python3-debian12:arm64` base image

#### 2. Missing requirements.txt
- **Issue**: Python services missing dependency files
- **Fix**: Creates comprehensive requirements.txt with security updates
- **Includes**: FastAPI, SQLAlchemy, cryptography, and other core dependencies

#### 3. TRON Isolation Issues
- **Issue**: TRON code found outside payment-systems/tron/
- **Fix**: Creates proper TRON service structure in payment-systems/tron/
- **Files Created**:
  - `tron_service.py` - Main TRON service class
  - `__init__.py` - Package initialization
  - `requirements.txt` - TRON-specific dependencies

#### 4. Security Issues
- **Issue**: Use of `eval()`, `exec()`, unsafe input handling
- **Fix**: Replaces dangerous functions with safer alternatives
- **Improvements**:
  - Removes `eval()` and `exec()` calls
  - Adds input validation methods
  - Implements proper error handling

### Electron GUI Alignment Issues

#### 1. Missing Directory Structure
- **Issue**: electron-gui directory or subdirectories missing
- **Fix**: Creates complete directory structure
- **Directories Created**:
  - `main/` - Electron main process files
  - `renderer/` - GUI components (admin, developer, node, user)
  - `shared/` - Shared utilities and types
  - `configs/` - Configuration files

#### 2. Missing Main Process Files
- **Issue**: Core Electron files missing
- **Fix**: Creates essential main process files
- **Files Created**:
  - `main/index.ts` - Main Electron process
  - `main/tor-manager.ts` - Tor service management
  - `main/docker-manager.ts` - Docker service management
  - `main/preload.ts` - Secure IPC bridge

#### 3. Missing Shared Files
- **Issue**: Shared utilities and types missing
- **Fix**: Creates shared module files
- **Files Created**:
  - `shared/types.ts` - TypeScript type definitions
  - `shared/api-client.ts` - HTTP client utilities

#### 4. Missing Configuration Files
- **Issue**: Configuration files missing or incomplete
- **Fix**: Creates comprehensive configuration files
- **Files Created**:
  - `configs/tor.config.json` - Tor service configuration
  - `configs/docker.config.json` - Docker service configuration
  - `configs/env.development.json` - Development environment
  - `configs/env.production.json` - Production environment

#### 5. Missing Build System Files
- **Issue**: Build configuration missing
- **Fix**: Creates complete build system
- **Files Created**:
  - `package.json` - Node.js dependencies and scripts
  - `tsconfig.json` - TypeScript configuration
  - `webpack.common.js` - Webpack common configuration
  - `webpack.main.config.js` - Main process webpack config
  - `webpack.renderer.config.js` - Renderer process webpack config

#### 6. Missing Renderer Components
- **Issue**: GUI components missing for each interface type
- **Fix**: Creates React components for each interface
- **Components Created**:
  - `renderer/admin/App.tsx` - Admin interface
  - `renderer/developer/App.tsx` - Developer interface
  - `renderer/node/App.tsx` - Node interface
  - `renderer/user/App.tsx` - User interface

## Examples

### Example 1: Fix All Issues
```bash
# Run validation to see what's broken
./scripts/validation/validate-project.sh --verbose

# Fix all issues
./scripts/validation/repair-project.sh --verbose

# Verify fixes
./scripts/validation/validate-project.sh
```

### Example 2: Dry Run (See What Would Be Fixed)
```bash
# See what would be fixed without making changes
./scripts/validation/repair-project.sh --dry-run --verbose
```

### Example 3: Fix Only Python Issues
```bash
# Fix only Python build alignment issues
./scripts/validation/repair-project.sh --python-only --verbose
```

### Example 4: Fix Only GUI Issues
```bash
# Fix only Electron GUI alignment issues
./scripts/validation/repair-project.sh --gui-only --verbose
```

### Example 5: Custom Project Root
```bash
# Fix issues in a different project directory
./scripts/validation/repair-project.sh --project-root /path/to/lucid --verbose
```

## Troubleshooting

### Common Issues

#### 1. Permission Errors
```bash
# Make sure scripts are executable
chmod +x scripts/validation/repair-project.sh
chmod +x scripts/validation/repair-validation-failures.py
```

#### 2. Python Not Found
```bash
# Install Python 3.6+ if not available
# On Ubuntu/Debian:
sudo apt install python3 python3-pip

# On Windows:
# Download from python.org or use Windows Store
```

#### 3. Missing Dependencies
```bash
# Install required Python packages
pip3 install fastapi uvicorn sqlalchemy cryptography
```

#### 4. Node.js/Electron Issues
```bash
# Install Node.js and npm
# Then install Electron dependencies
cd electron-gui
npm install
```

### Manual Fixes

If the repair script can't fix an issue automatically:

1. **Check the repair report** for specific error messages
2. **Review the validation output** to understand what's failing
3. **Manually create missing files** using the templates in the repair script
4. **Check file permissions** and directory access
5. **Verify project structure** matches expected layout

### Getting Help

1. **Run with --verbose** for detailed output
2. **Use --dry-run** to see what would be changed
3. **Check the repair report** for specific error details
4. **Review validation output** for context

## File Templates

The repair script includes templates for common files. You can find these in the `templates` dictionary in `repair-validation-failures.py`:

- **Dockerfile**: Distroless-based container configuration
- **requirements.txt**: Python dependencies with security updates
- **package.json**: Node.js dependencies and scripts
- **tsconfig.json**: TypeScript configuration
- **Webpack configs**: Build system configuration
- **TypeScript files**: Main process and renderer components

## Best Practices

1. **Always run validation first** to understand what needs fixing
2. **Use --dry-run** to preview changes before applying them
3. **Run validation again** after repairs to verify fixes
4. **Keep backups** of important files before running repairs
5. **Review generated files** to ensure they meet your requirements
6. **Test the application** after repairs to ensure everything works

## Integration with CI/CD

The repair script can be integrated into CI/CD pipelines:

```bash
# In your CI pipeline
./scripts/validation/validate-project.sh || ./scripts/validation/repair-project.sh
./scripts/validation/validate-project.sh  # Verify fixes
```

This ensures that validation issues are automatically fixed in your build process.
