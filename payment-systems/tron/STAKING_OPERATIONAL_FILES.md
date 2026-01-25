# TRON Staking Service - Operational Files & Compliance

**Service:** tron-staking (TRX Staking Service)  
**Container Name:** tron-staking  
**Port:** 8096 (STAKING_PORT)  
**Image:** pickme/lucid-trx-staking:latest-arm64  
**Status:** ✅ Production Ready

---

## 📋 Core Application Files

### **staking_main.py** ✅
- **Location:** `payment-systems/tron/staking_main.py`
- **Purpose:** Main FastAPI application for TRX staking service
- **Functions:**
  - FastAPI app initialization
  - Service lifecycle management (startup/shutdown)
  - API router integration
  - Health check endpoints
  - Metrics and status endpoints
- **Dependencies:**
  - fastapi
  - uvicorn
  - TRXStakingService
  - staking API router
- **Endpoints Configured:**
  - `/api/v1/tron/staking` (staking operations)
  - `/health` (health check)
  - `/health/live` (liveness probe)
  - `/health/ready` (readiness probe)
  - `/metrics` (Prometheus metrics)
  - `/status` (service status)
  - `/` (root endpoint)

### **trx_staking_entrypoint.py** ✅
- **Location:** `payment-systems/tron/trx_staking_entrypoint.py`
- **Purpose:** Container entry point script
- **Features:**
  - UTF-8 encoding for distroless containers
  - Environment variable configuration
  - Service name detection (SERVICE_NAME = 'tron-staking')
  - Port configuration (STAKING_PORT fallback to 8096)
  - Error handling and validation
  - Python path setup
- **Environment Variables:**
  - SERVICE_PORT (optional, uses STAKING_PORT)
  - STAKING_PORT (default: 8096)
  - SERVICE_HOST (default: 0.0.0.0)
  - WORKERS (default: 1)
  - LOG_LEVEL (default: INFO)

### **Dockerfile.trx-staking** ✅
- **Location:** `payment-systems/tron/Dockerfile.trx-staking`
- **Base Image:** python:3.11-slim-bookworm (distroless for runtime)
- **Build Stages:** 2 (builder + distroless runtime)
- **Key Features:**
  - Multi-stage build for minimal runtime image
  - Python 3.11 standardization
  - Distroless image support
  - Non-root user (65532:65532)
  - Health check endpoint (/health)
  - Package verification
  - Environment configuration
- **CMD:** `/opt/venv/bin/python3 trx_staking_entrypoint.py`
- **Ports:** 8096

### **env.staking.template** ✅
- **Location:** `payment-systems/tron/env.staking.template`
- **Purpose:** Environment configuration template
- **Variables:**
  - STAKING_PORT=8096
  - LOG_LEVEL=INFO
  - TRON_HTTP_ENDPOINT
  - TRON_API_KEY
  - TRONGRID_API_KEY
  - MONGODB_URL (for staking records)
  - REDIS_URL (for caching)
  - Security and encryption variables

---

## 🔌 API Support Files

### **staking.py (API Router)** ✅
- **Location:** `payment-systems/tron/api/staking.py`
- **Prefix:** `/api/v1/tron/staking`
- **Endpoints:** 12+ endpoints
- **Operations:**
  - Freeze balance (stake TRX)
  - Unfreeze balance (unstake TRX)
  - Vote for witnesses
  - Delegate resources
  - Undelegate resources
  - Claim rewards
  - Get staking status
  - Get reward information
  - List staking records
  - Get staking statistics
  - Get resource information
  - Get staking history

### **Data Models** ✅
- **Location:** `payment-systems/tron/models/staking.py` [NEW]
- **Models Included:**
  - `FreezeBalanceRequest` - Freeze balance request
  - `UnfreezeBalanceRequest` - Unfreeze request
  - `StakingRecord` - Staking record model
  - `StakingResponse` - Operation response
  - `StakingListResponse` - List response
  - `RewardInfo` - Reward information
  - `StakingStatsResponse` - Statistics response
  - `VoteWitnessRequest` - Vote request
  - `DelegateResourceRequest` - Delegation request
  - `ClaimRewardRequest` - Claim reward request
  - `ResourceDelegate` - Delegation record
  - `WithdrawRewardRequest` - Withdrawal request
  - `ResourceInfo` - Resource information
  - `StakingHistoryResponse` - History response
  - Enums: `StakingResourceType`, `StakingOperationType`, `StakingStatusType`

---

## 🔧 Service Layer

### **trx_staking.py (Service)** ✅
- **Location:** `payment-systems/tron/services/trx_staking.py`
- **Class:** `TRXStakingService`
- **Key Methods:**
  - `freeze_balance()` - Freeze TRX for staking
  - `unfreeze_balance()` - Unfreeze staked TRX
  - `vote_witness()` - Vote for witness
  - `delegate_resource()` - Delegate resources
  - `undelegate_resource()` - Undelegate resources
  - `claim_reward()` - Claim staking rewards
  - `get_staking_status()` - Get staking status
  - `get_reward_info()` - Get reward information
  - `list_stakings()` - List all staking records
  - `get_staking_stats()` - Get statistics
  - `get_resource_info()` - Get resource info
  - `get_service_stats()` - Get service statistics
  - `initialize()` - Service initialization
  - `stop()` - Service shutdown

---

## 📊 Database & Dependencies

### **Database Collections** (MongoDB)
- staking_records - Main staking data
- staking_rewards - Reward tracking
- resource_delegations - Resource delegation data
- voting_history - Witness voting history

### **Cache** (Redis)
- staking_stats:{address} - Address staking stats
- rewards:{address} - Address rewards cache
- resource_info:{address} - Resource information cache

### **Python Dependencies**
- fastapi==0.104.1
- uvicorn[standard]==0.24.0
- tronpy==0.12.0
- motor==3.3.0
- pymongo==4.6.0
- redis==5.0.0
- pydantic==2.5.0
- httpx==0.25.0

---

## 🏥 Health Checks

### **/health** (Main Health Endpoint)
```json
{
  "status": "healthy|degraded|unhealthy",
  "service": "tron-staking",
  "timestamp": "ISO8601",
  "service_initialized": true/false,
  "staking": {
    "total_staking_records": int,
    "active_staking_records": int,
    "total_staked_trx": float,
    "total_resource_records": int
  }
}
```

### **/health/live** (Liveness Probe)
- Returns 200 if service process is running
- Used by container orchestration for process restart

### **/health/ready** (Readiness Probe)
- Returns 200 if service is ready to receive traffic
- Checks database connection and service initialization

---

## 📈 Metrics & Monitoring

### **Prometheus Metrics** (/metrics endpoint)
- `staking_requests_total` - Total staking requests
- `staking_freezes_total` - Total freeze operations
- `staking_unfreezes_total` - Total unfreeze operations
- `staking_rewards_claimed_total` - Total rewards claimed
- `staking_active_records` - Active staking records
- `staking_total_trx_staked` - Total TRX staked
- `staking_operation_duration_seconds` - Operation duration

### **Service Status** (/status endpoint)
- Service state (running/error/degraded)
- Uptime
- Database connectivity
- Staking statistics
- Recent operations

---

## 🔒 Security Features

### **Authentication**
- JWT token validation (via API Gateway)
- Address validation (TRON format)
- Private key handling (encrypted, optional)

### **Authorization**
- User wallet ownership validation
- Operation-level permissions
- Rate limiting per address

### **Data Protection**
- Encrypted sensitive data (private keys)
- MongoDB connection security
- HTTPS in production
- Secure random number generation for operation IDs

### **Audit & Logging**
- All operations logged
- Failed operations tracked
- Transaction hashes recorded
- Timestamp tracking
- Error logging with context

---

## 📁 File Checklist

### Required Operational Files ✅
- [x] staking_main.py - Main application
- [x] trx_staking_entrypoint.py - Entry point
- [x] Dockerfile.trx-staking - Container definition
- [x] env.staking.template - Configuration template

### Required API Files ✅
- [x] api/staking.py - API router (12+ endpoints)
- [x] models/staking.py - Data models [NEW]

### Required Service Files ✅
- [x] services/trx_staking.py - Business logic

### Docker Compose Integration ✅
- [x] Service defined in docker-compose.support.yml
- [x] Health check configured
- [x] Environment variables configured
- [x] Port mapping configured
- [x] Volume mapping configured

---

## 🚀 Deployment Checklist

### Pre-Deployment ✅
- [x] All files present and verified
- [x] Python syntax checked
- [x] Dependencies documented
- [x] Port configuration verified
- [x] Environment variables defined
- [x] Health checks configured

### Build & Test ✅
- [x] Dockerfile builds successfully
- [x] Dependencies install correctly
- [x] Health endpoint responds
- [x] API endpoints accessible

### Production Deployment ✅
- [x] Docker image built and tagged
- [x] docker-compose configuration ready
- [x] Environment variables set
- [x] Volume permissions configured
- [x] Network connectivity verified
- [x] Monitoring configured

---

## 📝 Operational Procedures

### Starting the Service
```bash
docker-compose -f configs/docker/docker-compose.support.yml up tron-staking
```

### Checking Service Health
```bash
curl http://localhost:8096/health
```

### Viewing Service Logs
```bash
docker-compose logs -f tron-staking
```

### Restarting the Service
```bash
docker-compose -f configs/docker/docker-compose.support.yml restart tron-staking
```

### Scaling the Service
```bash
docker-compose -f configs/docker/docker-compose.support.yml up -d --scale tron-staking=3
```

---

## ⚠️ Common Issues & Troubleshooting

### Service Won't Start
- **Check:** Environment variables are set correctly
- **Check:** Port 8096 is available
- **Check:** MongoDB connection string is valid
- **Solution:** Verify docker-compose configuration

### Health Check Failing
- **Check:** MongoDB connection
- **Check:** Redis connection (if used)
- **Check:** TRON network connectivity
- **Solution:** Check service logs and dependencies

### Staking Operations Failing
- **Check:** Account has sufficient TRX
- **Check:** Private key is valid (if required)
- **Check:** Address is valid TRON format
- **Solution:** Review operation logs for error details

---

## 📞 Support & Documentation

- **Main App:** `payment-systems/tron/staking_main.py`
- **API Reference:** `payment-systems/tron/api/staking.py`
- **Service Implementation:** `payment-systems/tron/services/trx_staking.py`
- **Configuration:** `configs/environment/env.staking.template`
- **Docker Config:** `configs/docker/docker-compose.support.yml`

---

## ✅ Compliance & Standards

- ✅ Follows LUCID architecture patterns
- ✅ Python 3.11 standardized
- ✅ Distroless container compatible
- ✅ No hardcoded values
- ✅ Environment variable driven
- ✅ Health checks implemented
- ✅ Metrics collection enabled
- ✅ Logging configured
- ✅ Non-root user (65532:65532)
- ✅ Multi-stage Docker build

---

**Last Updated:** 2026-01-25  
**Status:** ✅ PRODUCTION READY  
**API Endpoints:** 12+  
**Data Models:** 14 models + 3 enums  
**Service Methods:** 15+
