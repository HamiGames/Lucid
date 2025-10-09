# 🏭 LUCID PROJECT BUILD ZONE RULES

## **OFFICIAL BUILD ENVIRONMENT**

### **🎯 PRIMARY BUILD ZONE: `lucid-devcontainer`**

**Container Name**: `lucid-devcontainer`  
**Image**: `pickme/lucid:devcontainer-dind`  
**Status**: **ACTIVE BUILD FACTORY**  

### **📋 BUILD ZONE SPECIFICATIONS**

#### **Container Requirements**
- ✅ **Docker-in-Docker (DinD)** - Full privileged access
- ✅ **Multi-Platform Buildx** - AMD64/ARM64 support via `lucid-pi` builder
- ✅ **Network Isolation** - `lucid-dev_lucid_net` (172.20.0.0/16)
- ✅ **Development Stack** - Java 17, Python 3.10, Node.js 20 LTS
- ✅ **SSH Access** - Port 2222 for remote development
- ✅ **Port Mapping** - All Lucid service ports (8080-8082, 9050-9051, 27017)

#### **Build Tools Available**
- **Docker**: Multi-platform image building
- **Docker Compose**: Service orchestration
- **Maven**: Java project builds
- **Gradle**: Alternative Java builds  
- **Python**: pip, venv, development tools
- **Node.js**: npm, yarn package management
- **Git**: Source control operations
- **SSH**: Remote repository access

#### **Workspace Configuration**
- **Host Mount**: Project root → `/workspaces/Lucid`
- **Working Directory**: `/workspaces/Lucid`
- **User**: `root` (required for Docker operations)

### **🚫 EXCLUSION RULES**

#### **NEVER USE FOR BUILDS**
- ❌ `buildx_buildkit_*` containers (support infrastructure only)
- ❌ Direct host Docker (security isolation required)
- ❌ Other development containers (dedicated build zone policy)

### **🔧 BUILD COMMANDS**

#### **Starting Build Zone**
```bash
# Start the build environment
docker start lucid-devcontainer

# Verify build tools
docker exec lucid-devcontainer docker --version
docker exec lucid-devcontainer docker buildx ls
```

#### **Building Docker Images**
```bash
# Inside devcontainer - Multi-platform builds
docker buildx build --platform linux/amd64,linux/arm64 -t myimage:tag .

# Standard single-platform builds  
docker build -t myimage:tag .
```

#### **VS Code Integration**
```bash
# Launch VS Code with devcontainer
./launch-devcontainer.ps1

# Or manual connection:
# VS Code → Ctrl+Shift+P → "Dev Containers: Reopen in Container"
```

### **🛡️ SECURITY & ISOLATION**

#### **Network Isolation**
- All builds occur within `lucid-dev_lucid_net`
- No direct host network access during builds
- SSH tunnel available for Pi deployment (192.168.0.75:22)

#### **Volume Management**  
- **Source**: Read/write access to project files
- **Docker Data**: Isolated within container volumes
- **SSH Keys**: Read-only mount from host
- **Git Config**: Read-only mount from host

### **📊 MONITORING & HEALTH**

#### **Container Health**
```bash
# Check build zone status
docker ps --filter "name=lucid-devcontainer"

# Health verification
docker exec lucid-devcontainer docker info
docker exec lucid-devcontainer docker buildx ls
```

#### **Resource Allocation**
- **Memory Limit**: 12GB
- **CPU Limit**: 6.0 cores  
- **Memory Reservation**: 4GB
- **CPU Reservation**: 2.0 cores

---

## **⚖️ ENFORCEMENT**

**This document establishes `lucid-devcontainer` as the ONLY authorized build environment for all Lucid project Docker operations.**

All team members and automated systems MUST use this designated build zone to ensure:
- Consistent build environments
- Security isolation
- Multi-platform compatibility  
- Reproducible builds
- Proper resource management

**Last Updated**: October 2, 2025  
**Status**: **ACTIVE** ✅