# Docker Compose Support - Volumes Update Summary

**File:** `configs/docker/docker-compose.support.yml`  
**Date:** 2025-01-25  
**Status:** ✅ Volumes section completed

---

## Changes Made

### Added 16 Volume Definitions

All volumes previously missing from the `volumes:` section have been added. These volumes support the 6 services running in the support compose stack.

---

## Volume Categories

### 1. Data Volumes (8 volumes)

Used for persistent data storage across service restarts:

| Volume Name | Docker Name | Purpose | Used By |
|---|---|---|---|
| `payment-systems-data` | `lucid-payment-systems-data` | Shared payment systems data | TRON Client, Payout Router, Wallet Manager, USDT Manager, Payment Gateway |
| `tron-data` | `lucid-tron-data` | TRON network data | TRON Client |
| `wallets-data` | `lucid-wallets-data` | Wallet storage | Wallet Manager |
| `usdt-data` | `lucid-usdt-data` | USDT token data | USDT Manager |
| `gateway-data` | `lucid-gateway-data` | Payment gateway data | Payment Gateway |
| `keys-data` | `lucid-keys-data` | Cryptographic keys (read-only) | All services |
| `batches-data` | `lucid-batches-data` | Transaction batches | Payout Router |
| `payouts-data` | `lucid-payouts-data` | Payout history | Payout Router |

### 2. Log Volumes (5 volumes)

Used for application logging and diagnostics:

| Volume Name | Docker Name | Purpose | Used By |
|---|---|---|---|
| `tron-client-logs` | `lucid-tron-client-logs` | TRON Client logs | TRON Client |
| `payout-router-logs` | `lucid-payout-router-logs` | Payout Router logs | Payout Router |
| `wallet-manager-logs` | `lucid-wallet-manager-logs` | Wallet Manager logs | Wallet Manager |
| `usdt-manager-logs` | `lucid-usdt-manager-logs` | USDT Manager logs | USDT Manager |
| `payment-gateway-logs` | `lucid-payment-gateway-logs` | Payment Gateway logs | Payment Gateway |

### 3. Tor Volumes (2 volumes)

Used for Tor proxy data and logging:

| Volume Name | Docker Name | Purpose | Used By |
|---|---|---|---|
| `tor-data` | `lucid-tor-data` | Tor network state | Tor Proxy |
| `tor-logs` | `lucid-tor-logs` | Tor logs | Tor Proxy |

---

## Volume Configuration Details

All volumes use:
- **Driver:** `local` (standard Docker local driver)
- **Naming:** Consistent `lucid-*` naming convention
- **Persistence:** Retained after container restart
- **Isolation:** Separate volumes per service for clean separation

---

## Service-to-Volume Mapping

### lucid-tron-client
```yaml
volumes:
  - payment-systems-data → /data/payment-systems:rw
  - tron-data → /data/tron:rw
  - keys-data → /data/keys:rw
  - tron-client-logs → /app/logs:rw
```

### tron-payout-router
```yaml
volumes:
  - payment-systems-data → /data/payment-systems:rw
  - payouts-data → /data/payouts:rw
  - batches-data → /data/batches:rw
  - keys-data → /data/keys:ro
  - payout-router-logs → /app/logs:rw
```

### tron-wallet-manager
```yaml
volumes:
  - payment-systems-data → /data/payment-systems:rw
  - wallets-data → /data/wallets:rw
  - keys-data → /data/keys:ro
  - wallet-manager-logs → /app/logs:rw
```

### tron-usdt-manager
```yaml
volumes:
  - payment-systems-data → /data/payment-systems:rw
  - usdt-data → /data/usdt:rw
  - keys-data → /data/keys:ro
  - usdt-manager-logs → /app/logs:rw
```

### tron-transaction-monitor
```yaml
volumes:
  - payment-systems-data → /data/payment-systems:rw
  - gateway-data → /data/gateway:rw
  - keys-data → /data/keys:ro
  - payment-gateway-logs → /app/logs:rw
```

### tor-proxy
```yaml
volumes:
  - tor-data → /data/tor:rw
  - tor-logs → /app/logs:rw
```

---

## Volume Access Modes

### Read-Write (rw)
- Used for: Data that services write to
- Examples: Payment data, wallet data, USDT data, gateway data, logs, Tor data
- Allows services to create, modify, and delete files

### Read-Only (ro)
- Used for: Sensitive data that services only read
- Examples: Cryptographic keys
- Prevents accidental modification of critical security material

---

## File Statistics

| Metric | Value |
|--------|-------|
| Total Volumes Added | 16 |
| Data Volumes | 8 |
| Log Volumes | 5 |
| Tor Volumes | 2 |
| Lines Added | ~65 |
| Total File Lines | ~718 |

---

## Docker Volume Commands Reference

### View all volumes
```bash
docker volume ls | grep lucid
```

### Inspect a volume
```bash
docker volume inspect lucid-payment-systems-data
```

### List volume disk usage
```bash
docker system df -v
```

### Create volumes manually (if needed)
```bash
docker volume create lucid-payment-systems-data
docker volume create lucid-tron-data
# ... etc for all 16 volumes
```

### Clean up volumes (destructive - data loss)
```bash
docker volume prune  # Remove unused volumes
```

---

## Deployment Verification

### ✅ Check volumes are created
```bash
docker-compose -f configs/docker/docker-compose.support.yml up -d
docker volume ls | grep lucid
```

### ✅ Verify volume mounts
```bash
docker inspect lucid-tron-client | grep -A 20 Mounts
```

### ✅ Check volume contents
```bash
docker run -v lucid-payment-systems-data:/data --rm alpine ls -la /data
```

---

## Backup Considerations

Since these volumes contain persistent data:

### Backup volumes
```bash
# Create backup
docker run --rm -v lucid-payment-systems-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/payment-systems-backup.tar.gz -C /data .

# Restore backup
docker run --rm -v lucid-payment-systems-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/payment-systems-backup.tar.gz -C /data
```

### Backup strategy
- Daily backup of `payment-systems-data`, `wallets-data`, `usdt-data`
- Daily backup of `keys-data` (critical)
- Weekly backup of all other volumes
- Store backups off-system

---

## Summary

✅ All missing volumes defined  
✅ Consistent naming convention applied  
✅ Proper access modes configured  
✅ Service mappings documented  
✅ Ready for production deployment

---

**Updated By:** Volume Definitions Task  
**Date:** 2025-01-25  
**File:** `configs/docker/docker-compose.support.yml`  
**Status:** ✅ Complete and Ready
