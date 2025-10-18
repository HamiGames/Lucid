# TRON Payment Isolation Guide

## Overview

This document provides detailed guidance on implementing TRON as a payment-only system within the Lucid RDP architecture, ensuring complete isolation from blockchain operations.

## Architectural Separation

### TRON Service Scope
The TRON service (`tron-payment-service`) is strictly limited to payment operations and must never participate in blockchain consensus, session anchoring, or governance.

### Service Boundaries
```
┌─────────────────────────────────────────────────────────────┐
│                    TRON PAYMENT SERVICE                     │
│                     (ISOLATED CONTAINER)                    │
├─────────────────────────────────────────────────────────────┤
│  ✅ ALLOWED:                                                │
│  • USDT-TRC20 transfers                                    │
│  • PayoutRouterV0/PRKYC calls                              │
│  • Energy/bandwidth management                             │
│  • Monthly payout distribution                             │
│  • Wallet integration                                      │
│  • TRX staking for fees                                    │
├─────────────────────────────────────────────────────────────┤
│  ❌ PROHIBITED:                                             │
│  • Session anchoring                                       │
│  • Consensus participation                                 │
│  • Chunk storage operations                                │
│  • Governance operations                                   │
│  • DHT/CRDT participation                                  │
│  • Work credits calculation                                │
│  • Leader selection                                        │
└─────────────────────────────────────────────────────────────┘
```

## Container Configuration

### Docker Compose Configuration
```yaml
services:
  tron-payment-service:
    image: gcr.io/distroless/nodejs20-debian12
    container_name: lucid-tron-payment
    restart: unless-stopped
    
    # Network isolation - wallet plane only
    networks:
      - wallet_plane
    
    # Service labels for Beta sidecar
    labels:
      - com.lucid.plane=wallet
      - com.lucid.service=tron-payment
      - com.lucid.expose=true
      - com.lucid.port=8080
    
    # Environment variables
    environment:
      - NODE_ENV=production
      - TRON_ONLY_PAYMENTS=true
      - TRON_NETWORK=${TRON_NETWORK:-shasta}
      - USDT_CONTRACT_ADDRESS=${USDT_CONTRACT_ADDRESS}
      - PAYOUT_ROUTER_V0_ADDRESS=${PAYOUT_ROUTER_V0_ADDRESS}
      - PAYOUT_ROUTER_KYC_ADDRESS=${PAYOUT_ROUTER_KYC_ADDRESS}
    
    # Volumes - only payment-related data
    volumes:
      - tron_payouts_data:/data/payouts
      - tron_keys:/data/keys:ro
    
    # Security configuration
    security_opt:
      - seccomp:./seccomp-tron.json
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    
    # User and resource limits
    user: "65532:65532"
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    
    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  wallet_plane:
    driver: bridge
    internal: true
    labels:
      - com.lucid.plane=wallet

volumes:
  tron_payouts_data:
    driver: local
    labels:
      - com.lucid.data=payouts
  tron_keys:
    driver: local
    labels:
      - com.lucid.data=keys
```

### Seccomp Profile
```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_X86", "SCMP_ARCH_X32"],
  "syscalls": [
    {
      "names": [
        "accept", "accept4", "access", "bind", "close", "connect",
        "epoll_create1", "epoll_ctl", "epoll_pwait", "fstat", "getpeername",
        "getsockname", "getsockopt", "listen", "lseek", "mmap", "munmap",
        "openat", "poll", "read", "readv", "recvfrom", "recvmmsg", "recvmsg",
        "sendmmsg", "sendmsg", "sendto", "setsockopt", "shutdown", "socket",
        "socketpair", "write", "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

## Data Isolation

### MongoDB Collections
The TRON service may ONLY access the following MongoDB collections:

```javascript
// ✅ ALLOWED: Payment-related collections only
const allowedCollections = {
  payouts: 'payouts',           // Payout transactions
  payout_batches: 'payout_batches', // Batch processing
  tron_receipts: 'tron_receipts',   // TRON transaction receipts
  wallet_keys: 'wallet_keys'        // Wallet key management
};

// ❌ PROHIBITED: Blockchain-related collections
const prohibitedCollections = {
  sessions: 'sessions',         // Session data
  chunks: 'chunks',            // Chunk storage
  task_proofs: 'task_proofs',   // Work credits
  work_tally: 'work_tally',     // Consensus metrics
  leader_schedule: 'leader_schedule' // Consensus scheduling
};
```

### Database Access Pattern
```javascript
// ✅ COMPLIANT: TRON service database access
class TronPaymentService {
  constructor(db) {
    // Only initialize allowed collections
    this.payouts = db.collection('payouts');
    this.payoutBatches = db.collection('payout_batches');
    this.tronReceipts = db.collection('tron_receipts');
    this.walletKeys = db.collection('wallet_keys');
  }

  async processPayout(sessionId, recipient, amount, router) {
    // Validate input
    if (!sessionId || !recipient || !amount) {
      throw new Error('Invalid payout parameters');
    }

    // Create payout record
    const payout = {
      sessionId,
      recipient,
      amount,
      router,
      status: 'pending',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    // Store in allowed collection
    await this.payouts.insertOne(payout);

    // Process TRON transaction
    const result = await this.executeTronPayout(payout);
    
    // Update payout status
    await this.payouts.updateOne(
      { _id: payout._id },
      { $set: { status: 'completed', tronTxId: result.txId, updatedAt: new Date() } }
    );

    return result;
  }

  // ❌ NON-COMPLIANT: Accessing blockchain collections
  async getSessionData(sessionId) {
    // This would violate isolation - sessions are blockchain data
    return await this.db.collection('sessions').findOne({ sessionId });
  }
}
```

## Network Isolation

### Beta Sidecar Configuration
The Beta sidecar enforces network isolation for the TRON service:

```yaml
# Beta sidecar configuration for TRON service
services:
  beta-sidecar:
    image: gcr.io/distroless/nodejs20-debian12
    container_name: lucid-beta-sidecar
    networks:
      - wallet_plane
      - ops_plane
      - chain_plane
    
    labels:
      - com.lucid.service=beta-sidecar
      - com.lucid.plane=ops
    
    environment:
      - BETA_ACL_CONFIG=/etc/beta/acl.yaml
      - BETA_TOR_CONFIG=/etc/beta/torrc
    
    volumes:
      - ./configs/beta/acl.yaml:/etc/beta/acl.yaml:ro
      - ./configs/beta/torrc:/etc/beta/torrc:ro
```

### ACL Configuration
```yaml
# configs/beta/acl.yaml
acls:
  wallet_plane:
    # TRON service can only communicate with:
    allowed_services:
      - admin-ui  # For payout requests
      - walletd   # For key management
    
    # TRON service cannot access:
    denied_services:
      - blockchain-core
      - blockchain-ledger
      - blockchain-virtual-machine
      - sessions-gateway
      - sessions-manifests
      - node-worker
      - node-data-host
    
    # TRON service can only make outbound connections to:
    outbound_allowed:
      - tron-mainnet:443
      - tron-shasta:443
    
    # No inbound connections from other planes
    inbound_denied_from:
      - chain_plane
      - ops_plane
```

## API Design

### TRON Payment Service API
The TRON service exposes a minimal API focused solely on payment operations:

```javascript
// ✅ ALLOWED: Payment-focused API endpoints
const paymentEndpoints = {
  // Payout operations
  'POST /payouts': 'processPayout',
  'GET /payouts/:id': 'getPayoutStatus',
  'GET /payouts': 'listPayouts',
  
  // Batch operations
  'POST /batches': 'createBatch',
  'GET /batches/:id': 'getBatchStatus',
  'POST /batches/:id/process': 'processBatch',
  
  // Wallet operations
  'GET /wallet/balance': 'getWalletBalance',
  'GET /wallet/address': 'getWalletAddress',
  'POST /wallet/stake': 'stakeTrx',
  'GET /wallet/energy': 'getEnergyInfo',
  
  // Health and status
  'GET /health': 'healthCheck',
  'GET /status': 'getServiceStatus'
};

// ❌ PROHIBITED: Blockchain-focused API endpoints
const prohibitedEndpoints = {
  'POST /sessions': 'createSession',        // Session management
  'GET /sessions/:id': 'getSession',        // Session data
  'POST /chunks': 'storeChunk',             // Chunk storage
  'GET /consensus/leader': 'getLeader',     // Consensus operations
  'POST /governance/proposal': 'createProposal' // Governance
};
```

### API Implementation
```javascript
// ✅ COMPLIANT: Payment service API implementation
class TronPaymentAPI {
  constructor(paymentService) {
    this.paymentService = paymentService;
  }

  // Payout processing endpoint
  async processPayout(req, res) {
    try {
      const { sessionId, recipient, amount, router } = req.body;
      
      // Validate payment parameters
      if (!this.isValidPaymentRequest(sessionId, recipient, amount, router)) {
        return res.status(400).json({ error: 'Invalid payment request' });
      }

      // Process payout through TRON
      const result = await this.paymentService.processPayout(
        sessionId, recipient, amount, router
      );

      res.json({
        success: true,
        payoutId: result.payoutId,
        tronTxId: result.tronTxId,
        status: 'pending'
      });
    } catch (error) {
      console.error('Payout processing failed:', error);
      res.status(500).json({ error: 'Payout processing failed' });
    }
  }

  // Health check endpoint
  async healthCheck(req, res) {
    try {
      const health = await this.paymentService.getHealthStatus();
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        tron_network: health.tronNetwork,
        wallet_connected: health.walletConnected,
        energy_available: health.energyAvailable
      });
    } catch (error) {
      res.status(503).json({ status: 'unhealthy', error: error.message });
    }
  }

  // ❌ NON-COMPLIANT: Blockchain API endpoints
  async createSession(req, res) {
    // This violates TRON isolation - sessions are blockchain operations
    throw new Error('TRON service cannot create sessions');
  }
}
```

## Monitoring and Observability

### Metrics Collection
The TRON service should only collect payment-related metrics:

```javascript
// ✅ ALLOWED: Payment-focused metrics
const paymentMetrics = {
  // Payout metrics
  payouts_total: 'counter',
  payouts_amount_total: 'counter',
  payout_duration_seconds: 'histogram',
  payout_failures_total: 'counter',
  
  // TRON network metrics
  tron_transactions_total: 'counter',
  tron_transaction_fees_total: 'counter',
  tron_energy_usage_total: 'counter',
  tron_bandwidth_usage_total: 'counter',
  
  // Wallet metrics
  wallet_balance_usdt: 'gauge',
  wallet_balance_trx: 'gauge',
  wallet_energy_available: 'gauge',
  wallet_bandwidth_available: 'gauge',
  
  // Service metrics
  service_uptime_seconds: 'counter',
  service_health_status: 'gauge'
};

// ❌ PROHIBITED: Blockchain-focused metrics
const prohibitedMetrics = {
  sessions_total: 'counter',           // Session metrics
  chunks_stored_total: 'counter',     // Chunk metrics
  consensus_blocks_total: 'counter',  // Consensus metrics
  work_credits_total: 'counter',      // Work credits
  governance_proposals_total: 'counter' // Governance metrics
};
```

### Logging Configuration
```javascript
// ✅ COMPLIANT: Payment-focused logging
class TronPaymentLogger {
  constructor() {
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
      ),
      defaultMeta: { service: 'tron-payment' },
      transports: [
        new winston.transports.File({ filename: '/var/log/tron-payment.log' })
      ]
    });
  }

  // Log payment operations
  logPayoutRequest(sessionId, recipient, amount, router) {
    this.logger.info('Payout request received', {
      sessionId,
      recipient: this.maskAddress(recipient),
      amount,
      router,
      timestamp: new Date().toISOString()
    });
  }

  logPayoutSuccess(payoutId, tronTxId, amount) {
    this.logger.info('Payout completed successfully', {
      payoutId,
      tronTxId,
      amount,
      timestamp: new Date().toISOString()
    });
  }

  logPayoutFailure(payoutId, error) {
    this.logger.error('Payout failed', {
      payoutId,
      error: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString()
    });
  }

  // ❌ NON-COMPLIANT: Blockchain logging
  logSessionCreation(sessionId) {
    // This violates TRON isolation
    throw new Error('TRON service cannot log session operations');
  }
}
```

## Testing and Validation

### Unit Tests
```javascript
// ✅ COMPLIANT: Payment-focused unit tests
describe('TronPaymentService', () => {
  let paymentService;
  let mockDb;

  beforeEach(() => {
    mockDb = {
      collection: jest.fn().mockReturnValue({
        insertOne: jest.fn(),
        updateOne: jest.fn(),
        findOne: jest.fn()
      })
    };
    paymentService = new TronPaymentService(mockDb);
  });

  describe('processPayout', () => {
    it('should process valid payout request', async () => {
      const payoutData = {
        sessionId: 'test-session-123',
        recipient: 'TTest123456789012345678901234567890',
        amount: 1000000, // 1 USDT
        router: 'PayoutRouterV0'
      };

      const result = await paymentService.processPayout(
        payoutData.sessionId,
        payoutData.recipient,
        payoutData.amount,
        payoutData.router
      );

      expect(result).toHaveProperty('payoutId');
      expect(result).toHaveProperty('tronTxId');
      expect(result.status).toBe('pending');
    });

    it('should reject invalid payout parameters', async () => {
      await expect(
        paymentService.processPayout(null, null, null, null)
      ).rejects.toThrow('Invalid payout parameters');
    });
  });

  // ❌ NON-COMPLIANT: Blockchain operation tests
  describe('session operations', () => {
    it('should not be able to create sessions', () => {
      // This test should not exist in TRON service
      expect(() => {
        paymentService.createSession('test-session');
      }).toThrow('TRON service cannot create sessions');
    });
  });
});
```

### Integration Tests
```javascript
// ✅ COMPLIANT: Payment integration tests
describe('TronPaymentIntegration', () => {
  let testContainer;

  beforeAll(async () => {
    // Start TRON service container
    testContainer = await docker.createContainer({
      Image: 'lucid/tron-payment-service:test',
      Env: ['TRON_NETWORK=shasta'],
      NetworkMode: 'wallet_plane'
    });
    await testContainer.start();
  });

  afterAll(async () => {
    if (testContainer) {
      await testContainer.stop();
      await testContainer.remove();
    }
  });

  it('should process payout end-to-end', async () => {
    const payoutRequest = {
      sessionId: 'integration-test-session',
      recipient: 'TTest123456789012345678901234567890',
      amount: 1000000,
      router: 'PayoutRouterV0'
    };

    const response = await fetch('http://localhost:8080/payouts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payoutRequest)
    });

    expect(response.status).toBe(200);
    const result = await response.json();
    expect(result.success).toBe(true);
    expect(result).toHaveProperty('payoutId');
    expect(result).toHaveProperty('tronTxId');
  });

  it('should reject blockchain operation requests', async () => {
    const sessionRequest = {
      sessionId: 'test-session',
      manifest: 'test-manifest'
    };

    const response = await fetch('http://localhost:8080/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sessionRequest)
    });

    expect(response.status).toBe(404); // Endpoint should not exist
  });
});
```

## Compliance Verification

### Automated Compliance Checks
```bash
#!/bin/bash
# compliance-check.sh

echo "Checking TRON service compliance..."

# Check Dockerfile uses distroless base
if ! grep -q "gcr.io/distroless" Dockerfile.tron-payment; then
  echo "❌ FAIL: Dockerfile does not use distroless base"
  exit 1
fi

# Check service only accesses allowed collections
if grep -q "sessions\|chunks\|task_proofs\|work_tally" src/tron-payment-service.js; then
  echo "❌ FAIL: TRON service accesses prohibited collections"
  exit 1
fi

# Check service only exposes payment endpoints
if grep -q "/sessions\|/chunks\|/consensus\|/governance" src/api.js; then
  echo "❌ FAIL: TRON service exposes prohibited endpoints"
  exit 1
fi

# Check network isolation
if ! grep -q "wallet_plane" docker-compose.yml; then
  echo "❌ FAIL: TRON service not isolated to wallet plane"
  exit 1
fi

echo "✅ PASS: TRON service compliance check"
```

### Manual Compliance Checklist
- [ ] TRON service runs in isolated container
- [ ] Container uses distroless base image
- [ ] Service only accesses payment-related MongoDB collections
- [ ] Service only exposes payment-related API endpoints
- [ ] Network isolation to wallet plane only
- [ ] No direct communication with blockchain services
- [ ] Beta sidecar enforces ACLs
- [ ] Security hardening measures implemented
- [ ] Payment-focused metrics and logging only
- [ ] Tests focus on payment operations only

## Conclusion

This guide ensures that TRON remains strictly a payment system within the Lucid RDP architecture. By following these guidelines, the TRON service maintains complete isolation from blockchain operations while providing secure and reliable payment functionality.
