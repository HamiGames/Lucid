# TRON Payment Cluster - Expected Files List

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | TRON-API-FILES-001 |
| Version | 1.0.0 |
| Status | COMPLETE |
| Last Updated | 2025-01-10 |
| Owner | Lucid RDP Development Team |

---

## Overview

This document lists all expected files required for the TRON Payment Cluster API functions to operate properly. The files are organized by category and include both implementation files and configuration files.

---

## Core API Implementation Files

### 1. Main Application Files

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/main.py` | FastAPI application entry point | All services |
| `payment-systems/tron-payment-service/app/__init__.py` | Python package initialization | All services |
| `payment-systems/tron-payment-service/app/config.py` | Configuration management | All services |
| `payment-systems/tron-payment-service/app/database.py` | Database connection management | All services |
| `payment-systems/tron-payment-service/app/logger.py` | Logging configuration | All services |

### 2. TRON Client Service Files

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/services/tron_client.py` | TRON network client | lucid-tron-client |
| `payment-systems/tron-payment-service/services/tron_network.py` | TRON network operations | lucid-tron-client |
| `payment-systems/tron-payment-service/services/tron_transaction.py` | TRON transaction handling | lucid-tron-client |
| `payment-systems/tron-payment-service/services/tron_blockchain.py` | TRON blockchain operations | lucid-tron-client |

### 3. Payout Router Service Files

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/services/payout_router.py` | Payout router logic | lucid-payout-router |
| `payment-systems/tron-payment-service/services/payout_router_v0.py` | Non-KYC payout router | lucid-payout-router |
| `payment-systems/tron-payment-service/services/payout_router_kyc.py` | KYC-gated payout router | lucid-payout-router |
| `payment-systems/tron-payment-service/services/payout_batch.py` | Batch payout processing | lucid-payout-router |
| `payment-systems/tron-payment-service/services/payout_validation.py` | Payout validation logic | lucid-payout-router |

### 4. Wallet Manager Service Files

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/services/wallet_manager.py` | Wallet management logic | lucid-wallet-manager |
| `payment-systems/tron-payment-service/services/wallet_creation.py` | Wallet creation operations | lucid-wallet-manager |
| `payment-systems/tron-payment-service/services/wallet_balance.py` | Wallet balance operations | lucid-wallet-manager |
| `payment-systems/tron-payment-service/services/wallet_transaction.py` | Wallet transaction handling | lucid-wallet-manager |
| `payment-systems/tron-payment-service/services/hardware_wallet.py` | Hardware wallet integration | lucid-wallet-manager |

### 5. USDT Manager Service Files

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/services/usdt_manager.py` | USDT operations manager | lucid-usdt-manager |
| `payment-systems/tron-payment-service/services/usdt_transfer.py` | USDT transfer operations | lucid-usdt-manager |
| `payment-systems/tron-payment-service/services/usdt_balance.py` | USDT balance operations | lucid-usdt-manager |
| `payment-systems/tron-payment-service/services/usdt_approval.py` | USDT approval operations | lucid-usdt-manager |
| `payment-systems/tron-payment-service/services/usdt_contract.py` | USDT contract interactions | lucid-usdt-manager |

### 6. TRX Staking Service Files

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/services/trx_staking.py` | TRX staking operations | lucid-trx-staking |
| `payment-systems/tron-payment-service/services/staking_stake.py` | Staking operations | lucid-trx-staking |
| `payment-systems/tron-payment-service/services/staking_unstake.py` | Unstaking operations | lucid-trx-staking |
| `payment-systems/tron-payment-service/services/staking_rewards.py` | Staking rewards calculation | lucid-trx-staking |
| `payment-systems/tron-payment-service/services/staking_withdrawal.py` | Staking withdrawal operations | lucid-trx-staking |

### 7. Payment Gateway Service Files

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/services/payment_gateway.py` | Payment gateway logic | lucid-payment-gateway |
| `payment-systems/tron-payment-service/services/payment_processing.py` | Payment processing logic | lucid-payment-gateway |
| `payment-systems/tron-payment-service/services/payment_refund.py` | Payment refund operations | lucid-payment-gateway |
| `payment-systems/tron-payment-service/services/payment_reconciliation.py` | Payment reconciliation | lucid-payment-gateway |
| `payment-systems/tron-payment-service/services/payment_webhook.py` | Payment webhook handling | lucid-payment-gateway |

---

## API Route Files

### 1. TRON Network Routes

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/routes/tron_network.py` | TRON network endpoints | lucid-tron-client |
| `payment-systems/tron-payment-service/routes/tron_status.py` | TRON status endpoints | lucid-tron-client |
| `payment-systems/tron-payment-service/routes/tron_fees.py` | TRON fees endpoints | lucid-tron-client |

### 2. Wallet Routes

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/routes/wallets.py` | Wallet management endpoints | lucid-wallet-manager |
| `payment-systems/tron-payment-service/routes/wallet_balance.py` | Wallet balance endpoints | lucid-wallet-manager |
| `payment-systems/tron-payment-service/routes/wallet_transactions.py` | Wallet transaction endpoints | lucid-wallet-manager |

### 3. USDT Routes

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/routes/usdt_transfer.py` | USDT transfer endpoints | lucid-usdt-manager |
| `payment-systems/tron-payment-service/routes/usdt_balance.py` | USDT balance endpoints | lucid-usdt-manager |
| `payment-systems/tron-payment-service/routes/usdt_approval.py` | USDT approval endpoints | lucid-usdt-manager |

### 4. Payout Routes

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/routes/payouts.py` | Payout endpoints | lucid-payout-router |
| `payment-systems/tron-payment-service/routes/payout_batch.py` | Batch payout endpoints | lucid-payout-router |
| `payment-systems/tron-payment-service/routes/payout_history.py` | Payout history endpoints | lucid-payout-router |

### 5. Staking Routes

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/routes/staking.py` | Staking endpoints | lucid-trx-staking |
| `payment-systems/tron-payment-service/routes/staking_rewards.py` | Staking rewards endpoints | lucid-trx-staking |
| `payment-systems/tron-payment-service/routes/staking_withdrawal.py` | Staking withdrawal endpoints | lucid-trx-staking |

### 6. Payment Routes

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/routes/payments.py` | Payment endpoints | lucid-payment-gateway |
| `payment-systems/tron-payment-service/routes/payment_refund.py` | Payment refund endpoints | lucid-payment-gateway |
| `payment-systems/tron-payment-service/routes/payment_reconciliation.py` | Payment reconciliation endpoints | lucid-payment-gateway |
| `payment-systems/tron-payment-service/routes/payment_webhook.py` | Payment webhook endpoints | lucid-payment-gateway |

---

## Data Model Files

### 1. Pydantic Models

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/models/tron_network.py` | TRON network data models | All services |
| `payment-systems/tron-payment-service/models/wallet.py` | Wallet data models | All services |
| `payment-systems/tron-payment-service/models/usdt.py` | USDT data models | All services |
| `payment-systems/tron-payment-service/models/payout.py` | Payout data models | All services |
| `payment-systems/tron-payment-service/models/staking.py` | Staking data models | All services |
| `payment-systems/tron-payment-service/models/payment.py` | Payment data models | All services |
| `payment-systems/tron-payment-service/models/common.py` | Common data models | All services |
| `payment-systems/tron-payment-service/models/errors.py` | Error response models | All services |

### 2. Database Models

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/database/models/tron_network.py` | TRON network DB models | All services |
| `payment-systems/tron-payment-service/database/models/wallet.py` | Wallet DB models | All services |
| `payment-systems/tron-payment-service/database/models/usdt.py` | USDT DB models | All services |
| `payment-systems/tron-payment-service/database/models/payout.py` | Payout DB models | All services |
| `payment-systems/tron-payment-service/database/models/staking.py` | Staking DB models | All services |
| `payment-systems/tron-payment-service/database/models/payment.py` | Payment DB models | All services |

---

## Configuration Files

### 1. Environment Configuration

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/.env.example` | Environment variables template | All services |
| `payment-systems/tron-payment-service/.env.development` | Development environment | All services |
| `payment-systems/tron-payment-service/.env.production` | Production environment | All services |
| `payment-systems/tron-payment-service/.env.testing` | Testing environment | All services |

### 2. Service Configuration

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/config/tron_client.yml` | TRON client configuration | lucid-tron-client |
| `payment-systems/tron-payment-service/config/payout_router.yml` | Payout router configuration | lucid-payout-router |
| `payment-systems/tron-payment-service/config/wallet_manager.yml` | Wallet manager configuration | lucid-wallet-manager |
| `payment-systems/tron-payment-service/config/usdt_manager.yml` | USDT manager configuration | lucid-usdt-manager |
| `payment-systems/tron-payment-service/config/trx_staking.yml` | TRX staking configuration | lucid-trx-staking |
| `payment-systems/tron-payment-service/config/payment_gateway.yml` | Payment gateway configuration | lucid-payment-gateway |

---

## Docker Files

### 1. Dockerfiles

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/Dockerfile.tron-client` | TRON client container | lucid-tron-client |
| `payment-systems/tron-payment-service/Dockerfile.payout-router` | Payout router container | lucid-payout-router |
| `payment-systems/tron-payment-service/Dockerfile.wallet-manager` | Wallet manager container | lucid-wallet-manager |
| `payment-systems/tron-payment-service/Dockerfile.usdt-manager` | USDT manager container | lucid-usdt-manager |
| `payment-systems/tron-payment-service/Dockerfile.trx-staking` | TRX staking container | lucid-trx-staking |
| `payment-systems/tron-payment-service/Dockerfile.payment-gateway` | Payment gateway container | lucid-payment-gateway |

### 2. Docker Compose Files

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/docker-compose.yml` | Main docker compose | All services |
| `payment-systems/tron-payment-service/docker-compose.dev.yml` | Development compose | All services |
| `payment-systems/tron-payment-service/docker-compose.prod.yml` | Production compose | All services |
| `payment-systems/tron-payment-service/docker-compose.test.yml` | Testing compose | All services |

---

## Contract Files

### 1. Smart Contract ABIs

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/contracts/usdt_abi.json` | USDT contract ABI | lucid-usdt-manager |
| `payment-systems/tron-payment-service/contracts/payout_router_v0_abi.json` | PayoutRouterV0 ABI | lucid-payout-router |
| `payment-systems/tron-payment-service/contracts/payout_router_kyc_abi.json` | PayoutRouterKYC ABI | lucid-payout-router |
| `payment-systems/tron-payment-service/contracts/staking_abi.json` | Staking contract ABI | lucid-trx-staking |

### 2. Contract Addresses

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/contracts/addresses.json` | Contract addresses | All services |
| `payment-systems/tron-payment-service/contracts/addresses.mainnet.json` | Mainnet addresses | All services |
| `payment-systems/tron-payment-service/contracts/addresses.testnet.json` | Testnet addresses | All services |

---

## Security Files

### 1. Authentication & Authorization

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/security/auth.py` | Authentication logic | All services |
| `payment-systems/tron-payment-service/security/jwt_handler.py` | JWT token handling | All services |
| `payment-systems/tron-payment-service/security/permissions.py` | Permission management | All services |
| `payment-systems/tron-payment-service/security/rate_limiting.py` | Rate limiting logic | All services |

### 2. Encryption & Key Management

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/security/encryption.py` | Encryption utilities | All services |
| `payment-systems/tron-payment-service/security/key_management.py` | Key management | All services |
| `payment-systems/tron-payment-service/security/private_key_handler.py` | Private key handling | All services |

---

## Utility Files

### 1. Common Utilities

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/utils/validators.py` | Input validation utilities | All services |
| `payment-systems/tron-payment-service/utils/formatters.py` | Data formatting utilities | All services |
| `payment-systems/tron-payment-service/utils/converters.py` | Data conversion utilities | All services |
| `payment-systems/tron-payment-service/utils/constants.py` | Application constants | All services |
| `payment-systems/tron-payment-service/utils/helpers.py` | Helper functions | All services |

### 2. TRON Utilities

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/utils/tron_utils.py` | TRON-specific utilities | All services |
| `payment-systems/tron-payment-service/utils/address_utils.py` | TRON address utilities | All services |
| `payment-systems/tron-payment-service/utils/transaction_utils.py` | Transaction utilities | All services |
| `payment-systems/tron-payment-service/utils/balance_utils.py` | Balance calculation utilities | All services |

---

## Testing Files

### 1. Unit Tests

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/tests/test_tron_client.py` | TRON client tests | lucid-tron-client |
| `payment-systems/tron-payment-service/tests/test_payout_router.py` | Payout router tests | lucid-payout-router |
| `payment-systems/tron-payment-service/tests/test_wallet_manager.py` | Wallet manager tests | lucid-wallet-manager |
| `payment-systems/tron-payment-service/tests/test_usdt_manager.py` | USDT manager tests | lucid-usdt-manager |
| `payment-systems/tron-payment-service/tests/test_trx_staking.py` | TRX staking tests | lucid-trx-staking |
| `payment-systems/tron-payment-service/tests/test_payment_gateway.py` | Payment gateway tests | lucid-payment-gateway |

### 2. Integration Tests

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/tests/integration/test_api_endpoints.py` | API endpoint tests | All services |
| `payment-systems/tron-payment-service/tests/integration/test_database.py` | Database integration tests | All services |
| `payment-systems/tron-payment-service/tests/integration/test_tron_network.py` | TRON network integration tests | All services |

### 3. Test Configuration

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/tests/conftest.py` | Pytest configuration | All services |
| `payment-systems/tron-payment-service/tests/fixtures.py` | Test fixtures | All services |
| `payment-systems/tron-payment-service/tests/mocks.py` | Mock objects | All services |

---

## Monitoring & Logging Files

### 1. Health Checks

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/health/health_check.py` | Health check logic | All services |
| `payment-systems/tron-payment-service/health/tron_health.py` | TRON network health | lucid-tron-client |
| `payment-systems/tron-payment-service/health/database_health.py` | Database health | All services |

### 2. Metrics & Monitoring

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/monitoring/metrics.py` | Metrics collection | All services |
| `payment-systems/tron-payment-service/monitoring/prometheus.py` | Prometheus integration | All services |
| `payment-systems/tron-payment-service/monitoring/alerting.py` | Alerting logic | All services |

---

## Documentation Files

### 1. API Documentation

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/docs/openapi.yaml` | OpenAPI specification | All services |
| `payment-systems/tron-payment-service/docs/api_reference.md` | API reference documentation | All services |
| `payment-systems/tron-payment-service/docs/endpoints.md` | Endpoint documentation | All services |

### 2. User Documentation

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/docs/user_guide.md` | User guide | All services |
| `payment-systems/tron-payment-service/docs/developer_guide.md` | Developer guide | All services |
| `payment-systems/tron-payment-service/docs/deployment_guide.md` | Deployment guide | All services |

---

## Dependencies Files

### 1. Python Dependencies

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/requirements.txt` | Python dependencies | All services |
| `payment-systems/tron-payment-service/requirements-dev.txt` | Development dependencies | All services |
| `payment-systems/tron-payment-service/requirements-test.txt` | Testing dependencies | All services |
| `payment-systems/tron-payment-service/pyproject.toml` | Python project configuration | All services |

### 2. System Dependencies

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/system-requirements.txt` | System dependencies | All services |
| `payment-systems/tron-payment-service/apt-packages.txt` | APT packages | All services |

---

## Scripts & Automation

### 1. Build Scripts

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/scripts/build.sh` | Build script | All services |
| `payment-systems/tron-payment-service/scripts/build-distroless.sh` | Distroless build script | All services |
| `payment-systems/tron-payment-service/scripts/test.sh` | Test script | All services |

### 2. Deployment Scripts

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/scripts/deploy.sh` | Deployment script | All services |
| `payment-systems/tron-payment-service/scripts/deploy-pi.sh` | Raspberry Pi deployment | All services |
| `payment-systems/tron-payment-service/scripts/start.sh` | Start script | All services |
| `payment-systems/tron-payment-service/scripts/stop.sh` | Stop script | All services |

### 3. Maintenance Scripts

| File Path | Purpose | Container |
|-----------|---------|-----------|
| `payment-systems/tron-payment-service/scripts/backup.sh` | Backup script | All services |
| `payment-systems/tron-payment-service/scripts/restore.sh` | Restore script | All services |
| `payment-systems/tron-payment-service/scripts/cleanup.sh` | Cleanup script | All services |
| `payment-systems/tron-payment-service/scripts/monitor.sh` | Monitoring script | All services |

---

## File Summary

### Total File Count by Category

| Category | File Count |
|----------|------------|
| Core API Implementation | 35 |
| API Routes | 18 |
| Data Models | 14 |
| Configuration Files | 10 |
| Docker Files | 10 |
| Contract Files | 6 |
| Security Files | 7 |
| Utility Files | 9 |
| Testing Files | 9 |
| Monitoring & Logging | 6 |
| Documentation Files | 6 |
| Dependencies Files | 6 |
| Scripts & Automation | 12 |

**Total Expected Files: 148**

---

## File Dependencies

### Critical Dependencies (Must Exist First)

1. `payment-systems/tron-payment-service/app/config.py` - Configuration management
2. `payment-systems/tron-payment-service/app/database.py` - Database connections
3. `payment-systems/tron-payment-service/models/common.py` - Common data models
4. `payment-systems/tron-payment-service/utils/constants.py` - Application constants
5. `payment-systems/tron-payment-service/contracts/addresses.json` - Contract addresses

### Service Dependencies

- **TRON Client Service**: Requires contract ABIs and network configuration
- **Payout Router Service**: Requires TRON client and payout models
- **Wallet Manager Service**: Requires TRON client and wallet models
- **USDT Manager Service**: Requires TRON client and USDT contract ABI
- **TRX Staking Service**: Requires TRON client and staking contract ABI
- **Payment Gateway Service**: Requires all other services for orchestration

---

## File Validation Checklist

### Pre-Implementation Validation

- [ ] All directory structures exist
- [ ] Configuration files are properly templated
- [ ] Contract ABIs are available and valid
- [ ] Environment variables are documented
- [ ] Docker files reference correct base images
- [ ] Dependencies are properly specified
- [ ] Test files have proper fixtures

### Post-Implementation Validation

- [ ] All files compile without errors
- [ ] All imports resolve correctly
- [ ] All configuration files load properly
- [ ] All tests pass
- [ ] All containers build successfully
- [ ] All services start without errors
- [ ] All API endpoints respond correctly

---

## Notes

1. **File Naming Convention**: All files follow Python naming conventions (snake_case for files, PascalCase for classes)

2. **Container Isolation**: Each service container has its own set of files to maintain isolation

3. **Shared Dependencies**: Common files (models, utils, config) are shared across all containers

4. **Security**: All sensitive files (private keys, API keys) are excluded from version control

5. **Testing**: All implementation files have corresponding test files

6. **Documentation**: All API endpoints are documented in OpenAPI format

---

**Document Status**: [COMPLETE]  
**Last Review**: 2025-01-10  
**Next Review**: 2025-02-10
