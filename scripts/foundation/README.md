# Lucid Foundation Scripts

**Phase 1: Foundation Setup - Step 1**  
**Based on**: BUILD_REQUIREMENTS_GUIDE.md - Section 1, Step 1

## Overview

This directory contains the foundation initialization and validation scripts for the Lucid project. These scripts are the first step in the build process and establish the core development environment.

## Files Created

### 1. `configs/environment/foundation.env`
**Purpose**: Foundation phase environment configuration  
**Location**: `configs/environment/foundation.env`

Contains all environment variables needed for Phase 1 (Foundation Setup):
- Docker configuration (BuildKit, networks)
- Python environment settings
- MongoDB, Redis, Elasticsearch configuration
- Authentication service settings
- Storage paths
- Logging configuration
- Security settings
- Development tools configuration

### 2. `scripts/foundation/initialize-project.sh`
**Purpose**: Initialize the Lucid project environment  
**Location**: `scripts/foundation/initialize-project.sh`

**Actions Performed**:
- ✓ Verify Docker BuildKit enabled
- ✓ Setup lucid-dev network (172.20.0.0/16)
- ✓ Setup lucid-network-isolated (172.21.0.0/16) for TRON services
- ✓ Initialize Python 3.11+ environment
- ✓ Configure git hooks and linting
- ✓ Create required directory structure

**Usage**:
```bash
./scripts/foundation/initialize-project.sh
```

**Validation**:
```bash
docker network ls | grep lucid-dev
```

### 3. `scripts/foundation/validate-environment.sh`
**Purpose**: Validate the project environment after initialization  
**Location**: `scripts/foundation/validate-environment.sh`

**Validation Checks**:
- ✓ Required tools installed (docker, git, python3)
- ✓ Docker daemon running
- ✓ Docker BuildKit available
- ✓ Docker networks configured correctly
- ✓ Python 3.11+ installed
- ✓ Git repository initialized
- ✓ Git hooks configured
- ✓ Directory structure exists
- ✓ Configuration files present
- ✓ Script permissions correct

**Usage**:
```bash
./scripts/foundation/validate-environment.sh
```

**Exit Codes**:
- `0` = Validation passed
- `1` = Validation failed

## Quick Start

### Step 1: Initialize the Environment
```bash
cd /path/to/Lucid
./scripts/foundation/initialize-project.sh
```

This will:
1. Verify your system has the required tools
2. Enable Docker BuildKit
3. Create Docker networks (lucid-dev and lucid-network-isolated)
4. Setup Python virtual environment
5. Configure Git hooks for linting
6. Create required directories

### Step 2: Validate the Environment
```bash
./scripts/foundation/validate-environment.sh
```

This will run comprehensive checks and provide a detailed report of your environment status.

### Step 3: Review Configuration
```bash
# Edit the foundation environment file
nano configs/environment/foundation.env

# Set required secrets:
# - MONGODB_PASSWORD
# - MONGODB_ROOT_PASSWORD
# - JWT_SECRET_KEY
# - REDIS_PASSWORD (optional)
```

## Environment Variables

### Critical Variables to Set

Before proceeding to Step 2, ensure these variables are set in `configs/environment/foundation.env`:

```bash
# MongoDB Authentication
MONGODB_PASSWORD=<secure_password>
MONGODB_ROOT_PASSWORD=<secure_root_password>

# JWT Authentication
JWT_SECRET_KEY=<generate_secure_key>

# Optional but recommended
REDIS_PASSWORD=<secure_password>
```

### Generate Secure Keys

```bash
# Generate JWT secret key
openssl rand -hex 32

# Generate MongoDB passwords
openssl rand -base64 32
```

## Docker Networks

### Main Development Network
- **Name**: `lucid-dev`
- **Subnet**: `172.20.0.0/16`
- **Gateway**: `172.20.0.1`
- **Purpose**: All core Lucid services (Clusters 01-06, 08-10)

### Isolated Network
- **Name**: `lucid-network-isolated`
- **Subnet**: `172.21.0.0/16`
- **Internal**: Yes (no external access)
- **Purpose**: TRON Payment services only (Cluster 07)

## Directory Structure Created

```
Lucid/
├── configs/
│   └── environment/
│       └── foundation.env          # Foundation configuration
├── scripts/
│   └── foundation/
│       ├── initialize-project.sh   # Initialization script
│       ├── validate-environment.sh # Validation script
│       └── README.md               # This file
├── data/                           # Data storage
│   ├── mongodb/                    # MongoDB data
│   ├── redis/                      # Redis data
│   ├── elasticsearch/              # Elasticsearch data
│   ├── chunks/                     # Session chunks
│   ├── sessions/                   # Session metadata
│   ├── merkle/                     # Merkle trees
│   └── blocks/                     # Blockchain blocks
├── logs/                           # Application logs
└── backups/                        # Database backups
```

## Troubleshooting

### Docker Network Already Exists
If the network already exists with different settings:
```bash
docker network rm lucid-dev
./scripts/foundation/initialize-project.sh
```

### Docker BuildKit Not Available
Ensure Docker version >= 19.03:
```bash
docker version
```

Update Docker if needed, then:
```bash
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

### Python Version Too Old
Install Python 3.11+:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11

# macOS (Homebrew)
brew install python@3.11
```

### Permission Denied on Scripts
Make scripts executable:
```bash
chmod +x scripts/foundation/*.sh
```

## Next Steps

After successful initialization and validation:

1. **Step 2: MongoDB Database Infrastructure**
   - Location: `database/`
   - Files to create:
     - `database/config/mongod.conf`
     - `database/schemas/*.js`
     - `scripts/database/create_indexes.js`

2. **Step 3: Redis & Elasticsearch Setup**
   - Configure Redis cluster
   - Setup Elasticsearch indices

3. **Step 4: Authentication Service Core**
   - Build authentication service
   - Implement TRON signature verification
   - Hardware wallet integration

Refer to `plan/API_plans/00-master-architecture/13-BUILD_REQUIREMENTS_GUIDE.md` for detailed instructions.

## References

- [BUILD_REQUIREMENTS_GUIDE.md](../../plan/API_plans/00-master-architecture/13-BUILD_REQUIREMENTS_GUIDE.md)
- [Master Build Plan](../../plan/API_plans/00-master-architecture/01-MASTER_BUILD_PLAN.md)
- [Master API Architecture](../../plan/API_plans/00-master-architecture/00-master-api-architecture.md)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the validation output for specific errors
3. Consult the BUILD_REQUIREMENTS_GUIDE.md
4. Check project documentation in `docs/`

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-10-14  
**Status**: ACTIVE

