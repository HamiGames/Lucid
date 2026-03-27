# Quick Reference: Electron GUI Build & Deploy

## TL;DR

**All Dockerfiles:** Fixed and production-ready ✅  
**Docker Compose:** Consolidated (admin-interface in GUI only) ✅  
**Config Verification:** Enhanced (all .json and .conf files) ✅

---

## Build Command (One-Liner)

```bash
cd /mnt/myssd/Lucid/Lucid && bash electron-gui/distroless/build-distroless.sh
```

---

## Deploy Command (One-Liner)

```bash
docker-compose -f configs/docker/docker-compose.gui-integration.yml up -d
```

---

## Health Check URLs

```bash
curl http://127.0.0.1:8120/health  # Admin Interface
curl http://127.0.0.1:3001/health  # User Interface
curl http://127.0.0.1:3002/health  # Node Operator Interface
```

---

## Key Changes

| File | Change | Impact |
|------|--------|--------|
| **Dockerfile.admin** | `npm ci` → `npm install` + config checks | Flexible build ✅ |
| **Dockerfile.user** | Same improvements | Flexible build ✅ |
| **Dockerfile.node** | Same improvements | Flexible build ✅ |
| **docker-compose.support.yml** | Removed admin-interface (82 lines) | Single source of truth ✅ |
| **docker-compose.gui-integration.yml** | Admin-interface only here now | Clean separation ✅ |

---

## Logs

```bash
docker logs lucid-admin-interface
docker logs lucid-user-interface
docker logs lucid-node-interface
docker logs lucid-gui-api-bridge
```

---

## Port Mapping

| Service | Port | Type |
|---------|------|------|
| Admin Interface | 8120 | HTTP |
| Admin Interface HTTPS | 8100 | HTTPS |
| User Interface | 3001 | HTTP |
| Node Operator | 3002 | HTTP |
| GUI API Bridge | 8097 | HTTP |
| GUI Docker Manager | 8098 | HTTP |
| Tor SOCKS5 | 9050 | PROXY |
| Tor Control | 9051 | CONTROL |
| Hardware Wallet | 8099 | HTTP |

---

## Troubleshooting

**Build fails with "not found":**
```bash
cd /mnt/myssd/Lucid/Lucid  # Ensure project root
docker build -f electron-gui/distroless/Dockerfile.admin -t pickme/lucid-admin-interface:latest-arm64 .
```

**Container won't start:**
```bash
docker logs lucid-admin-interface  # Check logs
docker inspect lucid-admin-interface  # Check config
```

**Health check fails:**
```bash
docker exec lucid-admin-interface curl http://127.0.0.1:8120/health
```

---

## Files to Know

```
electron-gui/distroless/
├── Dockerfile.admin          ✅ Fixed & verified
├── Dockerfile.user           ✅ Fixed & verified
├── Dockerfile.node           ✅ Fixed & verified
├── build-distroless.sh       → Use this to build all three
└── BUILD_VERIFICATION.md     → Reference guide

configs/docker/
├── docker-compose.gui-integration.yml    ✅ Admin-interface here
├── docker-compose.support.yml            ✅ Admin-interface removed
└── GUI_SERVICES_DEPLOYMENT.md            → Deployment guide

project root/
└── ELECTRON_GUI_COMPLETION_REPORT.md     → Full details
```

---

**Status:** Production Ready ✅
