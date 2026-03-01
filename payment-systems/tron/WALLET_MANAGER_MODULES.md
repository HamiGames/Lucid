# TRON Wallet Manager Container - Module Documentation

**Version:** 1.0.0  
**Last Updated:** 2025-01-27  
**Container:** `tron-wallet-manager`  
**Purpose:** Complete wallet management service for TRON payments

---

## Overview

This document describes all modules created for the `tron-wallet-manager` container, following Lucid architecture design patterns from `build/docs/`.

---

## Created Modules

### 1. **Wallet Repository** (`repositories/wallet_repository.py`)

**Purpose:** MongoDB persistence layer for wallet data

**Features:**
- Async MongoDB operations using Motor
- Connection pooling with configurable settings
- Wallet CRUD operations
- Transaction history storage
- Indexed queries for performance
- Proper error handling

**Key Methods:**
- `create_wallet()` - Create new wallet
- `get_wallet()` - Get wallet by ID
- `get_wallet_by_address()` - Get wallet by address
- `update_wallet()` - Update wallet data
- `delete_wallet()` - Soft delete wallet
- `list_wallets()` - List wallets with filters
- `create_transaction()` - Store transaction record
- `list_transactions()` - Get transaction history

---

### 2. **Wallet Backup Service** (`services/wallet_backup.py`)

**Purpose:** Automated backup and recovery of wallet data

**Features:**
- Encrypted backup storage (AES-256-GCM)
- Automated periodic backups
- Backup retention management
- Recovery from backup files
- Background cleanup tasks

**Key Methods:**
- `create_backup()` - Create encrypted backup
- `restore_backup()` - Restore from backup
- `list_backups()` - List available backups
- `delete_backup()` - Remove backup file

---

### 3. **Wallet Audit Service** (`services/wallet_audit.py`)

**Purpose:** Comprehensive audit logging for security and compliance

**Features:**
- Action-based audit logging
- Severity levels (LOW, MEDIUM, HIGH, CRITICAL)
- IP address and user agent tracking
- Success/failure tracking
- Security event detection
- Indexed queries for fast retrieval

**Audit Actions:**
- CREATE_WALLET, UPDATE_WALLET, DELETE_WALLET
- EXPORT_WALLET, IMPORT_WALLET
- SIGN_TRANSACTION, VIEW_BALANCE
- VIEW_PRIVATE_KEY, BACKUP_WALLET, RESTORE_WALLET

**Key Methods:**
- `log_action()` - Log audit event
- `get_audit_logs()` - Retrieve audit logs with filters
- `get_security_events()` - Get high/critical severity events

---

### 4. **Transaction History Service** (`services/wallet_transaction_history.py`)

**Purpose:** Track and manage wallet transaction history

**Features:**
- Transaction storage and retrieval
- Status tracking (pending, confirmed, failed)
- Date range filtering
- Transaction statistics
- Indexed queries

**Key Methods:**
- `add_transaction()` - Add transaction to history
- `get_transaction_history()` - Get history with filters
- `update_transaction_status()` - Update transaction status
- `get_transaction_stats()` - Get statistics

---

### 5. **Wallet Validator** (`services/wallet_validator.py`)

**Purpose:** Validate wallet addresses, private keys, and transaction data

**Features:**
- TRON address format validation
- Private key format validation
- Address/key matching verification
- Amount validation
- Wallet data structure validation

**Key Methods:**
- `validate_address()` - Validate TRON address
- `validate_private_key()` - Validate private key format
- `validate_address_and_key_match()` - Verify address matches key
- `validate_amount()` - Validate transaction amount
- `validate_wallet_data()` - Validate wallet structure

---

### 6. **Access Control Service** (`services/wallet_access_control.py`)

**Purpose:** Role-based access control (RBAC) for wallet operations

**Features:**
- Role-based permissions (ADMIN, USER, VIEWER, OPERATOR)
- Wallet-level access control
- Access expiration support
- Access revocation
- Permission checking

**Roles & Permissions:**
- **ADMIN:** Full access to all operations
- **OPERATOR:** Create, update, sign transactions, view balance
- **USER:** View wallet, sign transactions, view balance
- **VIEWER:** View wallet and balance only

**Key Methods:**
- `check_wallet_access()` - Check user permission
- `grant_wallet_access()` - Grant access to wallet
- `revoke_wallet_access()` - Revoke access
- `get_wallet_users()` - Get users with access
- `get_user_wallets()` - Get user's wallets

---

### 7. **Wallet Recovery Service** (`services/wallet_recovery.py`)

**Purpose:** Wallet recovery mechanisms

**Features:**
- Recovery code generation
- Backup-based recovery
- Private key-based recovery
- Recovery code expiration
- Recovery tracking

**Key Methods:**
- `create_recovery_code()` - Generate recovery code
- `recover_wallet_from_backup()` - Restore from backup
- `recover_wallet_from_private_key()` - Recover from private key
- `list_recovery_codes()` - List recovery codes

---

### 8. **Main Application** (`wallet_manager_main.py`)

**Purpose:** FastAPI application entry point

**Features:**
- Lifespan management (startup/shutdown)
- Service initialization
- Health check endpoint
- CORS middleware
- Integration of all modules

**Startup Sequence:**
1. Initialize MongoDB repository
2. Initialize backup service
3. Initialize audit service
4. Initialize transaction history service
5. Initialize validator service
6. Initialize access control service
7. Initialize recovery service
8. Initialize wallet manager service

**Shutdown Sequence:**
1. Stop wallet manager service
2. Stop backup service
3. Disconnect from MongoDB

---

### 9. **Entrypoint Script** (`wallet_manager_entrypoint.py`)

**Purpose:** Container entrypoint for distroless container

**Features:**
- Python-based entrypoint (no shell scripts)
- Environment variable configuration
- Path setup for imports
- Error handling with diagnostics
- Uvicorn server startup

**Configuration:**
- Reads `WALLET_MANAGER_PORT` or `SERVICE_PORT` (default: 8093)
- Binds to `0.0.0.0` (all interfaces)
- Uses `LOG_LEVEL` environment variable

---

## Database Collections

The wallet manager uses the following MongoDB collections:

1. **wallets** - Wallet data
2. **wallet_transactions** - Transaction records
3. **wallet_audit_logs** - Audit trail
4. **wallet_transaction_history** - Transaction history
5. **wallet_access_control** - Access control records
6. **wallet_recovery** - Recovery codes and records

---

## Environment Variables

### Required
- `MONGODB_URL` or `MONGODB_URI` - MongoDB connection string
- `WALLET_ENCRYPTION_KEY` or `ENCRYPTION_KEY` - Encryption key for backups

### Optional
- `MONGODB_DATABASE` - Database name (default: `lucid_payments`)
- `BACKUP_DIRECTORY` - Backup storage path (default: `/data/wallets/backups`)
- `BACKUP_INTERVAL` - Backup interval in seconds (default: 3600)
- `RETENTION_DAYS` - Backup retention days (default: 30)
- `WALLET_MANAGER_PORT` - Service port (default: 8093)
- `LOG_LEVEL` - Logging level (default: INFO)

---

## Integration with Existing Containers

The wallet manager integrates with:

- **lucid-mongodb** - Database storage
- **lucid-redis** - Caching (via wallet_manager service)
- **lucid-tron-client** - TRON network operations
- **api-gateway** - API routing

---

## Security Features

1. **Encryption:** AES-256-GCM for wallet backups
2. **Access Control:** RBAC with role-based permissions
3. **Audit Logging:** Comprehensive audit trail
4. **Validation:** Input validation for all operations
5. **Recovery:** Secure recovery mechanisms
6. **No Sensitive Data Exposure:** All sensitive data from `.env.*` files

---

## File Structure

```
payment-systems/tron/
├── repositories/
│   ├── __init__.py
│   └── wallet_repository.py
├── services/
│   ├── wallet_manager.py (existing)
│   ├── wallet_backup.py
│   ├── wallet_audit.py
│   ├── wallet_transaction_history.py
│   ├── wallet_validator.py
│   ├── wallet_access_control.py
│   └── wallet_recovery.py
├── wallet_manager_main.py
├── wallet_manager_entrypoint.py
└── WALLET_MANAGER_MODULES.md
```

---

## Next Steps

1. Update Dockerfile to use `wallet_manager_entrypoint.py` as entrypoint
2. Ensure all environment variables are configured in `.env.tron-wallet-manager`
3. Test container startup and health checks
4. Verify integration with existing containers
5. Run integration tests

---

## References

- `build/docs/mod-design-template.md` - Module design patterns
- `build/docs/session-api-design.md` - API design patterns
- `build/docs/session-processor-design.md` - Service patterns
- `configs/docker/docker-compose.support.yml` - Container configuration

