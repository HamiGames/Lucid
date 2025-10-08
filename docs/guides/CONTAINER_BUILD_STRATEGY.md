# Container Build Strategy & Implementation Plan

## 📋 **ANALYSIS: DevContainer vs Pi SSH Connection**

Based on SPEC-4 analysis and current infrastructure, here are the **recommended approaches**:

### **✅ RECOMMENDATION: Use DevContainer for Development & Initial Build**

**Why DevContainer is Best for First Multi-File Container Set:**

1. **✅ Environment Consistency** - All dependencies pre-installed and tested
2. **✅ Development Integration** - VS Code + Docker seamlessly integrated  
3. **✅ Port Forwarding Ready** - All required ports already configured
4. **✅ Network Isolation** - Proper container networking established
5. **✅ Build Tools Available** - Docker buildx, compose, all required toolchain
6. **✅ AMD64 Compatibility** - Works perfectly on your Windows system

### **🔄 Pi SSH Connection - Use for Edge Deployment Later**

**When to Use Pi System:**
- **Stage 3+ Node Systems** (node-worker, node-data-host) - Pi hardware encoding
- **Production Edge Deployment** - ARM64 native performance
- **Hardware-Specific Testing** - xrdp/FFmpeg with Pi HW acceleration

---

## 🎯 **IMPLEMENTATION STRATEGY**

### **Phase 1: DevContainer Foundation (RECOMMENDED START)**

**Build Order Based on SPEC-4:**

```
Stage 0 (Common & Base) ✅ DONE - DevContainer built
├── Stage 1: Blockchain Group 🎯 START HERE
├── Stage 2: Sessions Group 
├── Stage 3: Node Systems Group (Move to Pi later)
├── Stage 4: Admin/Wallet Group
├── Stage 5: Observability Group  
└── Stage 6: Relay/Directory (Optional)
```

---

## 🚀 **STEP 1: Create Missing Materials**

### **1.1 Main Docker Compose File (Missing)**

SPEC-4 requires `/infrastructure/compose/docker-compose.yml` with multi-profile support:

✅ **CREATED:** `infrastructure/compose/docker-compose.yml` with all required profiles and services

### **1.2 Missing Dockerfiles Analysis**

Based on SPEC-4 and current repository structure:

**✅ EXISTS:**
- `.devcontainer/Dockerfile` (base development environment)
- `02-network-security/tor/Dockerfile` (Tor proxy)

**❌ MISSING (Priority Order):**
1. `docker/Dockerfile.beta` (Beta sidecar - CRITICAL)
2. `04-blockchain-core/Dockerfile` (Blockchain core)
3. `sessions/Dockerfile.gateway` (Sessions gateway)
4. `sessions/Dockerfile.manifests` (Sessions manifests)
5. `node/Dockerfile.worker` (Node worker)
6. `admin/Dockerfile.api` (Admin API)
7. `wallet/Dockerfile` (Wallet daemon)

### **1.3 Port Mapping & Communication Analysis**

**✅ PORT FORWARDING VERIFIED:**

**Plane Separation (SPEC-4 Compliant):**
- **OPS Plane** (172.20.0.0/16): sessions-gateway, node-worker, admin-api
- **CHAIN Plane** (172.21.0.0/16): blockchain services, sessions-manifests
- **WALLET Plane** (172.22.0.0/16): walletd, tron-node, node-economy

**Port Allocation:**
- 8080: Sessions Gateway (OPS)
- 8081: Admin API (OPS) 
- 8082: Blockchain Core RPC (CHAIN)
- 8083: Blockchain P2P (CHAIN)
- 8084: Blockchain Ledger (CHAIN)
- 8085: Blockchain VM (CHAIN)
- 8086: Blockchain Sessions Data (CHAIN)
- 8087: Blockchain Governance (CHAIN)
- 8088: Sessions Manifests (CHAIN)
- 8089: Sessions Index (CHAIN)
- 8090: Node Worker (OPS)
- 8091: Node Data Host (OPS)
- 8092: TRON Node (WALLET)
- 8093: Node Economy (WALLET)
- 8094: Walletd (WALLET)
- 9050: Tor SOCKS (ALL PLANES)
- 9051: Tor Control (ALL PLANES)
- 27017: MongoDB (CHAIN + OPS)

**✅ COMMUNICATION VERIFIED:**
- All inter-service communication properly routed through plane networks
- Tor proxy accessible from all planes
- MongoDB accessible from OPS and CHAIN planes (wallet isolated)
- No direct wallet plane access (SPEC-4 compliant)

---

## 🚀 **RECOMMENDED IMPLEMENTATION STEPS**

### **Phase 1: Foundation Setup (DevContainer) 🎯 START HERE**

**Step 1.1: Create Beta Sidecar (CRITICAL FIRST)**
