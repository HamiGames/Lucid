# LUCID Project Validation Scripts

This directory contains comprehensive validation scripts for the LUCID project to ensure alignment with the build plan and API specifications.

## Overview

The validation system consists of three main components:

1. **Python Build Alignment Validator** - Validates Python files against the lucid-container-build-plan.plan.md
2. **Electron GUI Alignment Validator** - Validates the electron-gui directory structure and files
3. **Complete Validation Runner** - Orchestrates both validations and generates comprehensive reports

## Scripts

### 1. `validate-python-build-alignment.py`

Validates all Python files against the build plan requirements:

- **Distroless Compliance**: Ensures code is compatible with distroless containers
- **TRON Isolation**: Verifies TRON code is properly isolated to payment-systems/tron/
- **Docker Requirements**: Checks for proper Dockerfile configuration
- **Security Compliance**: Identifies potential security issues
- **Performance Requirements**: Flags performance anti-patterns
- **API Specification Alignment**: Ensures FastAPI best practices

**Usage:**
```bash
python scripts/validation/validate-python-build-alignment.py [--verbose] [--fix]
```

### 2. `validate-electron-gui-alignment.py`

Validates the electron-gui directory structure and files:

- **File Structure**: Ensures all required directories and files exist
- **TypeScript/React Components**: Validates component structure and best practices
- **API Integration**: Checks for proper API endpoint configuration
- **Configuration Files**: Validates JSON configs and environment files
- **Build System**: Ensures proper package.json, webpack, and TypeScript configs
- **Tor Integration**: Validates Tor manager and configuration
- **Docker Integration**: Checks Docker service integration
- **Security Compliance**: Identifies security anti-patterns

**Usage:**
```bash
python scripts/validation/validate-electron-gui-alignment.py [--verbose] [--fix]
```

### 3. `run-complete-validation.py`

Orchestrates both validations and generates comprehensive reports:

- Runs both Python and GUI validations
- Generates summary and detailed reports
- Saves results to `validation-report.json`
- Provides overall project status

**Usage:**
```bash
python scripts/validation/run-complete-validation.py [--verbose] [--python-only] [--gui-only]
```

### 4. `validate-project.sh`

Convenient shell script wrapper for easy execution:

- Cross-platform compatibility
- Color-coded output
- Help system
- Error handling

**Usage:**
```bash
./scripts/validation/validate-project.sh [--python-only] [--gui-only] [--verbose]
```

## Quick Start

### Run All Validations
```bash
./scripts/validation/validate-project.sh
```

### Run Only Python Validation
```bash
./scripts/validation/validate-project.sh --python-only
```

### Run Only GUI Validation
```bash
./scripts/validation/validate-project.sh --gui-only
```

### Run with Verbose Output
```bash
./scripts/validation/validate-project.sh --verbose
```

## Validation Criteria

### Python Build Alignment

#### Distroless Compliance
- ✅ No shell commands (`subprocess.run`, `os.system`)
- ✅ No shell=True usage
- ✅ Distroless-compatible alternatives

#### TRON Isolation
- ✅ No TRON imports in blockchain core
- ✅ TRON code isolated to `payment-systems/tron/`
- ✅ Proper separation of concerns

#### Docker Requirements
- ✅ Dockerfile exists for each service
- ✅ Uses distroless base image (`gcr.io/distroless/python3-debian12:arm64`)
- ✅ Non-root user configuration
- ✅ Multi-stage builds

#### Security Compliance
- ✅ No `eval()` or `exec()` usage
- ✅ Proper input validation
- ✅ Secure coding practices

#### Performance Requirements
- ✅ No infinite loops
- ✅ Efficient algorithms
- ✅ Proper resource management

### Electron GUI Alignment

#### File Structure
- ✅ `main/` directory with core files
- ✅ `renderer/` with admin, developer, node, user GUIs
- ✅ `shared/` with common utilities
- ✅ `configs/` with configuration files

#### TypeScript/React Components
- ✅ Proper React imports
- ✅ TypeScript type safety
- ✅ Component best practices
- ✅ Error handling

#### API Integration
- ✅ Proper API endpoint configuration
- ✅ HTTP client error handling
- ✅ Authentication integration

#### Build System
- ✅ `package.json` with required dependencies
- ✅ Webpack configurations
- ✅ TypeScript configurations
- ✅ Electron builder configuration

## Output

### Console Output
- Color-coded status indicators
- Detailed error messages
- Suggestions for fixes
- Summary statistics

### Report Files
- `validation-report.json` - Detailed JSON report
- Console output with line-by-line results
- File-specific validation results

## Exit Codes

- `0` - All validations passed
- `1` - Some validations failed
- `2` - Script execution error

## Requirements

- Python 3.6 or higher
- Access to project files
- Proper file permissions

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x scripts/validation/validate-project.sh
   ```

2. **Python Not Found**
   ```bash
   # Install Python 3.6+ or use python3
   python3 scripts/validation/run-complete-validation.py
   ```

3. **File Not Found**
   - Ensure you're in the LUCID project root directory
   - Check that all required files exist

4. **Import Errors**
   - Ensure all Python dependencies are installed
   - Check Python path configuration

### Debug Mode

Run with verbose output to see detailed information:
```bash
./scripts/validation/validate-project.sh --verbose
```

## Contributing

When adding new validation rules:

1. Update the appropriate validator class
2. Add new validation methods
3. Update the report generation
4. Test with various file types
5. Update this documentation

## Support

For issues or questions:
1. Check the console output for specific error messages
2. Review the `validation-report.json` file
3. Run with `--verbose` for detailed information
4. Ensure all project files are properly structured

---

**Note**: These validation scripts are designed to work with the LUCID project structure as defined in the build plan. They may need updates if the project structure changes significantly.
