# Authentication Cluster Expected Files

## File Path: `plan/API_plans/09-authentication-cluster/06-expected-files.md`

## Overview

This document provides a comprehensive listing of all files required for the operation of the Authentication Cluster API system. Files are organized by category with descriptions and key dependencies.

## Core Service Files

### Main Services
| File Path | Purpose | Key Dependencies |
|-----------|---------|------------------|
| `auth/authentication_service.py` | Main authentication engine implementing TRON signature verification, token generation, and user authentication | FastAPI, PyJWT, hashlib, user_manager, session_manager |
| `auth/user_manager.py` | User lifecycle and profile management including creation, retrieval, updates, and deletion | MongoDB, pymongo |
| `auth/hardware_wallet.py` | Hardware wallet integration for Ledger, Trezor, and KeepKey devices with signature verification | hidapi, cryptography |
| `auth/session_manager.py` | JWT token and session handling including creation, validation, and revocation | Redis, MongoDB, PyJWT |
| `auth/permissions.py` | Role-based access control (RBAC) engine for permission management | MongoDB |

## Middleware Components

### Request Processing Middleware
| File Path | Purpose | Key Dependencies |
|-----------|---------|------------------|
| `auth/middleware/auth_middleware.py` | Authentication middleware for token validation and user context injection | PyJWT, FastAPI |
| `auth/middleware/rate_limit.py` | Rate limiting middleware to prevent abuse and brute force attacks | Redis, FastAPI |
| `auth/middleware/audit_log.py` | Audit logging middleware for security event tracking and compliance | MongoDB, logging |

## Data Models

### Schema Definitions
| File Path | Purpose | Key Dependencies |
|-----------|---------|------------------|
| `auth/models/user.py` | User data models and schemas including UserProfile, Permission structures | Pydantic, MongoDB |
| `auth/models/session.py` | Session data models for SessionInfo and token management | Pydantic, datetime |
| `auth/models/hardware_wallet.py` | Hardware wallet models for device information and status tracking | Pydantic |

## Utility Modules

### Helper Functions
| File Path | Purpose | Key Dependencies |
|-----------|---------|------------------|
| `auth/utils/crypto.py` | Cryptographic utilities for TRON signature verification and Ed25519 operations | cryptography, hashlib |
| `auth/utils/validators.py` | Input validation for TRON addresses, signatures, and API parameters | Pydantic, re |
| `auth/utils/exceptions.py` | Custom exception classes for authentication and authorization errors | FastAPI, HTTPException |

## Test Files

### Unit Tests
| File Path | Purpose | Coverage Target |
|-----------|---------|-----------------|
| `auth/tests/test_auth.py` | Authentication service unit tests including login, logout, and token operations | Authentication flows |
| `auth/tests/test_user_manager.py` | User management unit tests for CRUD operations | User lifecycle |
| `auth/tests/test_hardware_wallet.py` | Hardware wallet integration unit tests for device connection and verification | Wallet operations |
| `auth/tests/test_session_manager.py` | Session manager unit tests for token and session handling | Session management |

### Integration Tests
| File Path | Purpose | Coverage Target |
|-----------|---------|-----------------|
| `auth/tests/test_database_integration.py` | MongoDB integration tests for data persistence | Database operations |
| `auth/tests/test_redis_integration.py` | Redis integration tests for caching and rate limiting | Redis operations |

### Performance & Security Tests
| File Path | Purpose | Coverage Target |
|-----------|---------|-----------------|
| `auth/tests/test_performance.py` | Load and performance tests for concurrent authentication | Scalability |
| `auth/tests/test_memory.py` | Memory usage tests for session and token management | Resource efficiency |
| `auth/tests/test_security.py` | Security tests for brute force protection and token expiration | Security controls |

## Configuration Files

### Container & Deployment
| File Path | Purpose | Description |
|-----------|---------|-------------|
| `Dockerfile` | Multi-stage distroless container image definition | Uses `gcr.io/distroless/python3-debian11` base |
| `docker-compose.yml` | Production deployment configuration with Beta sidecar | Includes auth service, MongoDB, Redis, and sidecar |
| `docker-compose.test.yml` | Test environment configuration | Isolated test databases and services |

### Dependency Management
| File Path | Purpose | Key Contents |
|-----------|---------|--------------|
| `requirements.txt` | Python package dependencies | fastapi==0.104.1, uvicorn==0.24.0, pydantic==2.5.0, PyJWT==2.8.0, pymongo==4.6.0, redis==5.0.1, hidapi==0.14.0, cryptography==41.0.8 |

### Testing Configuration
| File Path | Purpose | Description |
|-----------|---------|-------------|
| `pytest.ini` | Test framework configuration | Coverage target 95%, async support, test discovery patterns |

### CI/CD Pipeline
| File Path | Purpose | Description |
|-----------|---------|-------------|
| `.github/workflows/test-auth.yml` | GitHub Actions test pipeline | Automated testing on push/PR with MongoDB and Redis services |

## Package Initialization Files

### Python Package Structure
| File Path | Purpose |
|-----------|---------|
| `auth/__init__.py` | Main authentication package initialization |
| `auth/middleware/__init__.py` | Middleware package initialization |
| `auth/models/__init__.py` | Data models package initialization |
| `auth/utils/__init__.py` | Utilities package initialization |
| `auth/tests/__init__.py` | Tests package initialization |

## Environment & Documentation

### Configuration & Documentation
| File Path | Purpose | Key Contents |
|-----------|---------|--------------|
| `.env.example` | Environment variables template | LUCID_AUTH_SECRET_KEY, LUCID_AUTH_TOKEN_EXPIRE_MINUTES, LUCID_AUTH_HARDWARE_WALLET_ENABLED, LUCID_AUTH_RATE_LIMIT_PER_MINUTE, LUCID_AUTH_MONGODB_URL, LUCID_AUTH_REDIS_URL |
| `README.md` | Service documentation | Setup instructions, API endpoints, deployment guide |

## File Count Summary

| Category | File Count |
|----------|------------|
| Core Services | 5 files |
| Middleware | 3 files |
| Data Models | 3 files |
| Utilities | 3 files |
| Unit Tests | 4 files |
| Integration Tests | 2 files |
| Performance/Security Tests | 3 files |
| Configuration Files | 5 files |
| Package Init Files | 5 files |
| Environment/Documentation | 2 files |
| **Total** | **35 files** |

## Directory Structure Overview

```
auth/
├── __init__.py
├── authentication_service.py
├── user_manager.py
├── hardware_wallet.py
├── session_manager.py
├── permissions.py
├── middleware/
│   ├── __init__.py
│   ├── auth_middleware.py
│   ├── rate_limit.py
│   └── audit_log.py
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── session.py
│   └── hardware_wallet.py
├── utils/
│   ├── __init__.py
│   ├── crypto.py
│   ├── validators.py
│   └── exceptions.py
└── tests/
    ├── __init__.py
    ├── test_auth.py
    ├── test_user_manager.py
    ├── test_hardware_wallet.py
    ├── test_session_manager.py
    ├── test_database_integration.py
    ├── test_redis_integration.py
    ├── test_performance.py
    ├── test_memory.py
    └── test_security.py

Configuration Files (Root Level):
├── Dockerfile
├── requirements.txt
├── pytest.ini
├── docker-compose.yml
├── docker-compose.test.yml
├── .env.example
├── README.md
└── .github/
    └── workflows/
        └── test-auth.yml
```

## Implementation Priority

### Phase 1 - Core Infrastructure
1. Core service files (`authentication_service.py`, `user_manager.py`, `session_manager.py`)
2. Data models (`user.py`, `session.py`)
3. Utility modules (`crypto.py`, `validators.py`, `exceptions.py`)

### Phase 2 - Security & Features
1. Hardware wallet integration (`hardware_wallet.py`)
2. Permissions engine (`permissions.py`)
3. Middleware components (all three middleware files)

### Phase 3 - Testing & Deployment
1. Unit tests (core test files)
2. Integration tests (database and Redis tests)
3. Configuration files (Dockerfile, docker-compose files)
4. CI/CD pipeline configuration

### Phase 4 - Optimization & Documentation
1. Performance and security tests
2. Documentation and README
3. Environment configuration templates

## Dependencies Matrix

### External Service Dependencies
- **MongoDB** (port 27017) - User data and session storage
- **Redis** (port 6379) - Token blacklist and rate limiting
- **TRON Node** (port 8091) - Address verification

### Python Package Dependencies
- **FastAPI** 0.104.1 - Web framework
- **Uvicorn** 0.24.0 - ASGI server
- **Pydantic** 2.5.0 - Data validation
- **PyJWT** 2.8.0 - JWT token handling
- **pymongo** 4.6.0 - MongoDB driver
- **redis** 5.0.1 - Redis client
- **hidapi** 0.14.0 - Hardware wallet communication
- **cryptography** 41.0.8 - Cryptographic operations

## Notes

- All files use distroless container base image for enhanced security
- Hardware wallet support is optional via environment variable
- All API endpoints require proper authentication except login
- Rate limiting is enforced at middleware level
- Audit logging is mandatory for all operations
- JWT tokens use HS256 algorithm with rotating keys
- Session data is stored in both MongoDB (persistent) and Redis (cache)

