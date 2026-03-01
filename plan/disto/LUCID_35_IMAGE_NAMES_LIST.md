# Lucid Project - 35 Docker Image Names List

## Overview
Complete list of all 35 Docker images required for the Lucid project deployment on Raspberry Pi 5.

**Total Images**: 35  
**Target Architecture**: linux/arm64  
**Registry**: Docker Hub (pickme/lucid namespace)

---

## 📋 **PHASE 1: BASE INFRASTRUCTURE (3 images)**
1. pickme/lucid-base:python-distroless-arm64
2. pickme/lucid-base:java-distroless-arm64
3. pickme/lucid-base:latest-arm64

## 📋 **PHASE 2: FOUNDATION SERVICES (4 images)**
4. pickme/lucid-mongodb:latest-arm64
5. pickme/lucid-redis:latest-arm64
6. pickme/lucid-elasticsearch:latest-arm64
7. pickme/lucid-auth-service:latest-arm64

## 📋 **PHASE 3: CORE SERVICES (6 images)**
8. pickme/lucid-api-gateway:latest-arm64
9. pickme/lucid-service-mesh-controller:latest-arm64
10. pickme/lucid-blockchain-engine:latest-arm64
11. pickme/lucid-session-anchoring:latest-arm64
12. pickme/lucid-block-manager:latest-arm64
13. pickme/lucid-data-chain:latest-arm64

## 📋 **PHASE 4: APPLICATION SERVICES (10 images)**
14. pickme/lucid-session-pipeline:latest-arm64
15. pickme/lucid-session-recorder:latest-arm64
16. pickme/lucid-chunk-processor:latest-arm64
17. pickme/lucid-session-storage:latest-arm64
18. pickme/lucid-session-api:latest-arm64
19. pickme/lucid-rdp-server-manager:latest-arm64
20. pickme/lucid-rdp-xrdp:latest-arm64
21. pickme/lucid-rdp-controller:latest-arm64
22. pickme/lucid-rdp-monitor:latest-arm64
23. pickme/lucid-node-management:latest-arm64

## 📋 **PHASE 5: SUPPORT SERVICES (7 images)**
24. pickme/lucid-admin-interface:latest-arm64
25. pickme/lucid-tron-client:latest-arm64
26. pickme/lucid-payout-router:latest-arm64
27. pickme/lucid-wallet-manager:latest-arm64
28. pickme/lucid-usdt-manager:latest-arm64
29. pickme/lucid-trx-staking:latest-arm64
30. pickme/lucid-payment-gateway:latest-arm64

## 📋 **PHASE 6: SPECIALIZED SERVICES (5 images)**
31. pickme/lucid-gui:latest-arm64
32. pickme/lucid-rdp:latest-arm64
33. pickme/lucid-vm:latest-arm64
34. pickme/lucid-database:latest-arm64
35. pickme/lucid-storage:latest-arm64

---

**Total Images**: 35  
**Generated**: 2025-01-24
