# 🔧 SPIN-UP REQUIREMENTS GUIDE

## Complete Setup Instructions for Missing Lucid RDP Components

**Version:** 1.0.0  
**Date:** 2025-10-06  
**Status:** IMPLEMENTATION READY  

---

## **📋 OVERVIEW**

This guide provides detailed spin-up requirements for implementing all missing Lucid RDP components. Each component includes prerequisites, dependencies, installation steps, and verification procedures.

---

## **🎯 PHASE 1: CORE INFRASTRUCTURE COMPONENTS**

### **1.1 RDP Hosting System**

#### **Component: `RDP/recorder/rdp_host.py`**

**Purpose:** Main RDP hosting service with xrdp integration

**Spin-Up Requirements:**

```bash
# System Dependencies
sudo apt-get update
sudo apt-get install -y xrdp xrdp-pulseaudio-installer
sudo apt-get install -y xfce4 xfce4-goodies
sudo apt-get install -y python3-pip python3-venv

# Python Dependencies
pip install fastapi uvicorn websockets asyncio
pip install psutil subprocess
pip install cryptography libsodium

# Create Directories
sudo mkdir -p /etc/xrdp
sudo mkdir -p /var/log/xrdp
sudo mkdir -p /opt/lucid/rdp
sudo chown -R $USER:$USER /opt/lucid/rdp
```

**Verification:**

```bash
# Test xrdp installation
sudo systemctl status xrdp
sudo systemctl enable xrdp

# Test Python environment
python3 -c "import fastapi, uvicorn, websockets"
```

#### **Component: `RDP/recorder/wayland_integration.py`**

**Purpose:** Wayland display server integration

**Spin-Up Requirements:**

```bash
# Wayland Dependencies
sudo apt-get install -y wayland-protocols weston
sudo apt-get install -y libwayland-dev wayland-utils
sudo apt-get install -y python3-pywayland

# Python Dependencies
pip install pywayland pycairo
pip install asyncio websockets
pip install cryptography

# Create Wayland Directories
mkdir -p /opt/lucid/wayland
mkdir -p /opt/lucid/display
```

**Verification:**

```bash
# Test Wayland installation
wayland-info
weston --version

# Test Python Wayland bindings
python3 -c "import wayland"
```

#### **Component: `RDP/recorder/clipboard_handler.py`**

**Purpose:** Clipboard transfer toggles

**Spin-Up Requirements:**

```bash
# Clipboard Dependencies
sudo apt-get install -y xclip xsel
sudo apt-get install -y python3-tk

# Python Dependencies
pip install pyperclip
pip install asyncio websockets
pip install cryptography

# Create Clipboard Directories
mkdir -p /opt/lucid/clipboard
mkdir -p /opt/lucid/transfer
```

**Verification:**

```bash
# Test clipboard tools
xclip -version
xsel --version

# Test Python clipboard
python3 -c "import pyperclip"
```

#### **Component: `RDP/recorder/file_transfer_handler.py`**

**Purpose:** File transfer toggles

**Spin-Up Requirements:**

```bash
# File Transfer Dependencies
sudo apt-get install -y rsync
sudo apt-get install -y python3-paramiko

# Python Dependencies
pip install paramiko
pip install asyncio websockets
pip install cryptography hashlib

# Create Transfer Directories
mkdir -p /opt/lucid/transfer
mkdir -p /opt/lucid/uploads
mkdir -p /opt/lucid/downloads
```

**Verification:**

```bash
# Test rsync
rsync --version

# Test Python paramiko
python3 -c "import paramiko"
```

### **1.2 Session Audit Trail System**

#### **Component: `sessions/recorder/audit_trail.py`**

**Purpose:** Session audit logging

**Spin-Up Requirements:**

```bash
# Logging Dependencies
sudo apt-get install -y rsyslog
sudo apt-get install -y python3-logging

# Python Dependencies
pip install structlog
pip install asyncio websockets
pip install cryptography hashlib
pip install fastapi uvicorn

# Create Audit Directories
sudo mkdir -p /var/log/lucid/audit
sudo mkdir -p /var/log/lucid/sessions
sudo chown -R $USER:$USER /var/log/lucid
```

**Verification:**

```bash
# Test logging system
python3 -c "import structlog, logging"
```

#### **Component: `sessions/recorder/keystroke_monitor.py`**

**Purpose:** Keystroke metadata capture

**Spin-Up Requirements:**

```bash
# Input Monitoring Dependencies
sudo apt-get install -y python3-pynput
sudo apt-get install -y python3-keyboard

# Python Dependencies
pip install pynput keyboard
pip install asyncio websockets
pip install cryptography hashlib

# Create Keystroke Directories
mkdir -p /var/log/lucid/keystrokes
mkdir -p /opt/lucid/input
```

**Verification:**

```bash
# Test input monitoring
python3 -c "import pynput, keyboard"
```

#### **Component: `sessions/recorder/window_focus_monitor.py`**

**Purpose:** Window focus tracking

**Spin-Up Requirements:**

```bash
# Window Management Dependencies
sudo apt-get install -y python3-xlib
sudo apt-get install -y python3-ewmh

# Python Dependencies
pip install Xlib
pip install ewmh
pip install asyncio websockets
pip install cryptography

# Create Window Directories
mkdir -p /var/log/lucid/windows
mkdir -p /opt/lucid/focus
```

**Verification:**

```bash
# Test window management
python3 -c "import Xlib, ewmh"
```

#### **Component: `sessions/recorder/resource_monitor.py`**

**Purpose:** Resource access tracking

**Spin-Up Requirements:**

```bash
# System Monitoring Dependencies
sudo apt-get install -y python3-psutil
sudo apt-get install -y python3-netifaces

# Python Dependencies
pip install psutil netifaces
pip install asyncio websockets
pip install cryptography

# Create Resource Directories
mkdir -p /var/log/lucid/resources
mkdir -p /opt/lucid/monitoring
```

**Verification:**

```bash
# Test system monitoring
python3 -c "import psutil, netifaces"
```

### **1.3 Wallet Management System**

#### **Component: `wallet/walletd/software_vault.py`**

**Purpose:** Passphrase-protected vault

**Spin-Up Requirements:**

```bash
# Cryptographic Dependencies
sudo apt-get install -y python3-cryptography
sudo apt-get install -y python3-argon2

# Python Dependencies
pip install cryptography argon2-cffi
pip install fastapi uvicorn
pip install asyncio websockets

# Create Vault Directories
sudo mkdir -p /opt/lucid/wallet
sudo mkdir -p /opt/lucid/vaults
sudo mkdir -p /opt/lucid/keys
sudo chown -R $USER:$USER /opt/lucid/wallet
```

**Verification:**

```bash
# Test cryptography
python3 -c "import cryptography, argon2"
```

#### **Component: `wallet/walletd/role_manager.py`**

**Purpose:** Role-based access control

**Spin-Up Requirements:**

```bash
# Authentication Dependencies
sudo apt-get install -y python3-jwt
sudo apt-get install -y python3-passlib

# Python Dependencies
pip install PyJWT passlib
pip install fastapi uvicorn
pip install asyncio websockets

# Create Role Directories
mkdir -p /opt/lucid/roles
mkdir -p /opt/lucid/permissions
```

**Verification:**

```bash
# Test authentication
python3 -c "import jwt, passlib"
```

#### **Component: `wallet/walletd/key_rotation.py`**

**Purpose:** Key rotation system

**Spin-Up Requirements:**

```bash
# Key Management Dependencies
sudo apt-get install -y python3-cryptography
sudo apt-get install -y python3-paramiko

# Python Dependencies
pip install cryptography paramiko
pip install fastapi uvicorn
pip install asyncio websockets

# Create Key Directories
mkdir -p /opt/lucid/keys/active
mkdir -p /opt/lucid/keys/rotated
mkdir -p /opt/lucid/keys/backup
```

**Verification:**

```bash
# Test key management
python3 -c "import cryptography, paramiko"
```

---

## **🎯 PHASE 2: BLOCKCHAIN INTEGRATION COMPONENTS**

### **2.1 Smart Contract Development**

#### **Component: `contracts/LucidAnchors.sol`**

**Purpose:** Session anchoring contract

**Spin-Up Requirements:**

```bash
# Solidity Development Dependencies
npm install -g truffle
npm install -g @openzeppelin/contracts
npm install -g hardhat

# Install Solidity Compiler
sudo apt-get install -y solc

# Create Contract Directories
mkdir -p contracts
mkdir -p contracts/migrations
mkdir -p contracts/test
mkdir -p contracts/abi
```

**Verification:**

```bash
# Test Solidity tools
truffle version
hardhat --version
solc --version
```

#### **Component: `contracts/PayoutRouterV0.sol`**

**Purpose:** No-KYC payout router

**Spin-Up Requirements:**

```bash
# TRON Development Dependencies
pip install tronpy
npm install -g tronbox

# Create TRON Directories
mkdir -p contracts/tron
mkdir -p contracts/tron/migrations
mkdir -p contracts/tron/test
```

**Verification:**

```bash
# Test TRON tools
python3 -c "import tronpy"
tronbox version
```

### **2.2 On-System Data Chain Client**

#### **Component: `blockchain/chain-client/on_system_chain_client.py`**

**Purpose:** On-System Chain client

**Spin-Up Requirements:**

```bash
# Blockchain Dependencies
pip install web3 eth-account
pip install tronpy base58
pip install cryptography hashlib

# Create Blockchain Directories
mkdir -p blockchain/chain-client
mkdir -p blockchain/contracts
mkdir -p blockchain/abi
mkdir -p blockchain/keys
```

**Verification:**

```bash
# Test blockchain libraries
python3 -c "import web3, tronpy, base58"
```

#### **Component: `blockchain/chain-client/lucid_anchors_client.py`**

**Purpose:** LucidAnchors contract client

**Spin-Up Requirements:**

```bash
# Contract Interaction Dependencies
pip install web3 eth-account
pip install tronpy base58
pip install cryptography hashlib

# Create Contract Client Directories
mkdir -p blockchain/chain-client/contracts
mkdir -p blockchain/chain-client/abi
```

**Verification:**

```bash
# Test contract interaction
python3 -c "import web3, tronpy"
```

### **2.3 TRON Integration System**

#### **Component: `payment-systems/tron-node/payout_router_v0.py`**

**Purpose:** PayoutRouterV0 integration

**Spin-Up Requirements:**

```bash
# TRON Integration Dependencies
pip install tronpy
pip install base58 cryptography
pip install fastapi uvicorn

# Create TRON Directories
mkdir -p payment-systems/tron-node
mkdir -p payment-systems/contracts
mkdir -p payment-systems/abi
```

**Verification:**

```bash
# Test TRON integration
python3 -c "import tronpy, base58"
```

#### **Component: `payment-systems/tron-node/usdt_trc20.py`**

**Purpose:** USDT-TRC20 integration

**Spin-Up Requirements:**

```bash
# USDT Integration Dependencies
pip install tronpy
pip install base58 cryptography
pip install fastapi uvicorn

# Create USDT Directories
mkdir -p payment-systems/usdt
mkdir -p payment-systems/trc20
```

**Verification:**

```bash
# Test USDT integration
python3 -c "import tronpy, base58"
```

---

## **🎯 PHASE 3: ADMIN UI & GOVERNANCE COMPONENTS**

### **3.1 Minimal Web Admin UI**

#### **Component: `admin/admin-ui/`**

**Purpose:** Complete Next.js application

**Spin-Up Requirements:**

```bash
# Node.js Installation
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Create Next.js Application
npx create-next-app@latest admin-ui --typescript --tailwind --eslint
cd admin-ui

# Install Dependencies
npm install @next/font
npm install @headlessui/react
npm install @heroicons/react
npm install axios
npm install react-hook-form
npm install @types/node
```

**Verification:**

```bash
# Test Node.js
node --version
npm --version

# Test Next.js
cd admin-ui
npm run dev
```

#### **Component: `admin/admin-ui/src/pages/provisioning.tsx`**

**Purpose:** Provisioning interface

**Spin-Up Requirements:**

```bash
# React Dependencies
npm install react react-dom
npm install @types/react @types/react-dom
npm install axios
npm install react-hook-form
```

**Verification:**

```bash
# Test React components
npm run build
```

### **3.2 Governance System**

#### **Component: `common/governance/lucid_governor.py`**

**Purpose:** Governor implementation

**Spin-Up Requirements:**

```bash
# Governance Dependencies
pip install fastapi uvicorn
pip install web3 eth-account
pip install cryptography hashlib
pip install asyncio

# Create Governance Directories
mkdir -p common/governance
mkdir -p common/voting
mkdir -p common/parameters
```

**Verification:**

```bash
# Test governance libraries
python3 -c "import fastapi, web3, cryptography"
```

#### **Component: `common/governance/timelock.py`**

**Purpose:** Timelock implementation

**Spin-Up Requirements:**

```bash
# Timelock Dependencies
pip install fastapi uvicorn
pip install web3 eth-account
pip install cryptography hashlib
pip install asyncio

# Create Timelock Directories
mkdir -p common/governance/timelock
mkdir -p common/governance/queues
```

**Verification:**

```bash
# Test timelock libraries
python3 -c "import fastapi, web3, cryptography"
```

---

## **🎯 PHASE 4: CONSENSUS & ADVANCED FEATURES**

### **4.1 PoOT Consensus System**

#### **Component: `node/consensus/leader_selection.py`**

**Purpose:** Leader selection algorithm

**Spin-Up Requirements:**

```bash
# Consensus Dependencies
pip install asyncio websockets
pip install cryptography hashlib
pip install psutil
pip install fastapi uvicorn

# Create Consensus Directories
mkdir -p node/consensus
mkdir -p node/beacons
mkdir -p node/proofs
```

**Verification:**

```bash
# Test consensus libraries
python3 -c "import asyncio, websockets, cryptography, psutil"
```

#### **Component: `node/consensus/task_proofs.py`**

**Purpose:** Task proof collection

**Spin-Up Requirements:**

```bash
# Proof Collection Dependencies
pip install asyncio websockets
pip install cryptography hashlib
pip install psutil
pip install fastapi uvicorn

# Create Proof Directories
mkdir -p node/consensus/proofs
mkdir -p node/consensus/tasks
```

**Verification:**

```bash
# Test proof collection
python3 -c "import asyncio, websockets, cryptography, psutil"
```

### **4.2 OTA Update Mechanism**

#### **Component: `tools/ops/ota/update_manager.py`**

**Purpose:** OTA update system

**Spin-Up Requirements:**

```bash
# OTA Dependencies
pip install cryptography
pip install requests
pip install fastapi uvicorn
pip install asyncio

# Create OTA Directories
mkdir -p tools/ops/ota
mkdir -p tools/ops/signatures
mkdir -p tools/ops/versions
```

**Verification:**

```bash
# Test OTA libraries
python3 -c "import cryptography, requests, fastapi"
```

#### **Component: `tools/ops/ota/signature_verifier.py`**

**Purpose:** Release signature verification

**Spin-Up Requirements:**

```bash
# Signature Verification Dependencies
pip install cryptography
pip install requests
pip install fastapi uvicorn
pip install asyncio

# Create Signature Directories
mkdir -p tools/ops/signatures
mkdir -p tools/ops/keys
```

**Verification:**

```bash
# Test signature verification
python3 -c "import cryptography, requests"
```

---

## **🛠️ BUILD SYSTEM COMPONENTS**

### **Component: `scripts/build_ffmpeg_pi.sh`**

**Purpose:** FFmpeg cross-compilation

**Spin-Up Requirements:**

```bash
# Build Dependencies
sudo apt-get install -y build-essential cmake
sudo apt-get install -y git curl wget
sudo apt-get install -y pkg-config

# FFmpeg Dependencies
sudo apt-get install -y libavcodec-dev libavformat-dev libavutil-dev
sudo apt-get install -y libswscale-dev libswresample-dev
sudo apt-get install -y libx264-dev libx265-dev

# Create Build Directories
mkdir -p scripts/build
mkdir -p scripts/ffmpeg
mkdir -p scripts/cross-compile
```

**Verification:**

```bash
# Test build tools
gcc --version
cmake --version
pkg-config --version
```

### **Component: `scripts/build_contracts.sh`**

**Purpose:** Contract compilation

**Spin-Up Requirements:**

```bash
# Solidity Dependencies
npm install -g truffle
npm install -g @openzeppelin/contracts
npm install -g hardhat

# Create Contract Build Directories
mkdir -p scripts/contracts
mkdir -p scripts/build
mkdir -p scripts/abi
```

**Verification:**

```bash
# Test contract build tools
truffle version
hardhat --version
```

### **Component: `scripts/build_pi_image.sh`**

**Purpose:** Pi flashable image

**Spin-Up Requirements:**

```bash
# Pi Image Dependencies
sudo apt-get install -y docker.io docker-compose
sudo apt-get install -y qemu-user-static
sudo apt-get install -y binfmt-support

# Create Pi Image Directories
mkdir -p scripts/pi-image
mkdir -p scripts/flash
mkdir -p scripts/boot
```

**Verification:**

```bash
# Test Docker
docker --version
docker-compose --version

# Test QEMU
qemu-arm-static --version
```

---

## **🧪 TESTING FRAMEWORK COMPONENTS**

### **Component: `tests/test_tor_connectivity.sh`**

**Purpose:** Tor connectivity tests

**Spin-Up Requirements:**

```bash
# Testing Dependencies
pip install pytest pytest-asyncio
pip install requests websockets
pip install docker

# Create Test Directories
mkdir -p tests
mkdir -p tests/integration
mkdir -p tests/unit
mkdir -p tests/chaos
```

**Verification:**

```bash
# Test testing tools
pytest --version
python3 -c "import requests, websockets, docker"
```

### **Component: `tests/test_hardware_encoding.sh`**

**Purpose:** Hardware encoding tests

**Spin-Up Requirements:**

```bash
# Hardware Testing Dependencies
sudo apt-get install -y ffmpeg
sudo apt-get install -y v4l-utils
sudo apt-get install -y python3-opencv

# Create Hardware Test Directories
mkdir -p tests/hardware
mkdir -p tests/encoding
mkdir -p tests/v4l2
```

**Verification:**

```bash
# Test hardware tools
ffmpeg -version
v4l2-ctl --version
python3 -c "import cv2"
```

### **Component: `tests/test_blockchain_integration.sh`**

**Purpose:** Blockchain integration tests

**Spin-Up Requirements:**

```bash
# Blockchain Testing Dependencies
pip install web3 eth-account
pip install tronpy base58
pip install pytest pytest-asyncio

# Create Blockchain Test Directories
mkdir -p tests/blockchain
mkdir -p tests/contracts
mkdir -p tests/tron
```

**Verification:**

```bash
# Test blockchain testing
python3 -c "import web3, tronpy, pytest"
```

---

## **📊 COMPLETE SPIN-UP CHECKLIST**

### **System Requirements:**

- ✅ Ubuntu 20.04+ or Raspberry Pi OS 64-bit
- ✅ Python 3.8+ with pip
- ✅ Node.js 20+ with npm
- ✅ Docker and Docker Compose
- ✅ Git and build tools

### **Python Dependencies:**

- ✅ fastapi uvicorn websockets asyncio
- ✅ cryptography libsodium argon2-cffi
- ✅ psutil pynput keyboard
- ✅ web3 eth-account tronpy base58
- ✅ pytest pytest-asyncio

### **Node.js Dependencies:**

- ✅ Next.js 14+ with TypeScript
- ✅ React 18+ with hooks
- ✅ Tailwind CSS for styling
- ✅ Axios for API calls

### **System Tools:**

- ✅ xrdp for RDP hosting
- ✅ Wayland for display server
- ✅ FFmpeg for video encoding
- ✅ Tor for network security
- ✅ MongoDB for data storage

### **Build Tools:**

- ✅ Docker Buildx for multi-arch builds
- ✅ Truffle/Hardhat for smart contracts
- ✅ CMake for native compilation
- ✅ Git for version control

---

## **🚀 QUICK START COMMANDS**

### **Complete System Setup:**

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install core dependencies
sudo apt-get install -y python3-pip python3-venv nodejs npm docker.io docker-compose git build-essential cmake

# Install Python packages
pip install fastapi uvicorn websockets asyncio cryptography libsodium argon2-cffi psutil pynput keyboard web3 eth-account tronpy base58 pytest pytest-asyncio

# Install Node.js packages
npm install -g truffle hardhat @openzeppelin/contracts

# Create directory structure
mkdir -p {RDP,admin,blockchain,common,node,payment-systems,tools,contracts,tests}/{recorder,admin-ui,chain-client,governance,consensus,tron-node,ops,ota}

# Set permissions
chmod -R 755 RDP admin blockchain common node payment-systems tools contracts tests
```

### **Verification:**

```bash
# Test Python environment
python3 -c "import fastapi, uvicorn, websockets, asyncio, cryptography, libsodium, argon2, psutil, pynput, keyboard, web3, tronpy, base58, pytest"

# Test Node.js environment
node --version && npm --version

# Test Docker environment
docker --version && docker-compose --version

# Test build tools
truffle version && hardhat --version
```

---

## **📈 SUCCESS METRICS**

### **Phase 1 Complete When:**

- ✅ All Python dependencies installed
- ✅ RDP hosting system functional
- ✅ Session audit trail logging
- ✅ Wallet management working

### **Phase 2 Complete When:**

- ✅ Smart contracts compiled
- ✅ Blockchain clients connected
- ✅ TRON integration working
- ✅ Payout system functional

### **Phase 3 Complete When:**

- ✅ Next.js admin UI running
- ✅ Governance system active
- ✅ Voting system functional
- ✅ Parameter registry working

### **Phase 4 Complete When:**

- ✅ PoOT consensus running
- ✅ OTA updates working
- ✅ Testing framework complete
- ✅ Production deployment ready

---

## **🎯 CONCLUSION**

This spin-up requirements guide provides complete setup instructions for implementing all missing Lucid RDP components. Each component includes detailed prerequisites, dependencies, installation steps, and verification procedures.

**Key Success Factors:**
1. **Follow the phase order** - Each phase builds on the previous
2. **Complete all spin-up requirements** - Ensure all dependencies are installed
3. **Verify each component** - Test functionality before moving to next phase
4. **Document progress** - Track completion of each component

**Total Setup Time: 2-4 hours for complete environment**

With this guide, all missing components can be systematically implemented to achieve full SPEC-1 compliance.

