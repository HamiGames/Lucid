# Lucid RDP GUI System

A comprehensive web-based GUI system for Lucid RDP that provides secure, Tor-only access to all platform functionality through distroless containers.

## 🎯 Overview

The Lucid RDP GUI System implements three distinct web-based interfaces:

- **User GUI**: End-user session management and control
- **Admin GUI**: Pi appliance administration and provisioning  
- **Node GUI**: Node worker monitoring and PoOT management

All GUIs are built as distroless containers, accessed exclusively via .onion URLs through Tor Browser, and integrate seamlessly with the existing Lucid RDP architecture.

## 🏗️ Architecture

### Web-Based Design
- **Technology**: Next.js 14 with TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **HTTP Client**: Axios with Tor SOCKS proxy
- **Authentication**: JWT with magic link + TOTP

### Container Architecture
- **Base Images**: `gcr.io/distroless/nodejs20-debian12`
- **Security**: Non-root user (UID 65532), read-only filesystem, no shells
- **Multi-stage Builds**: Builder + distroless runtime stages
- **Orchestration**: Docker Compose with auto-start

### Tor Integration
- **Access**: .onion URLs only, no clearnet ingress
- **Service Discovery**: Beta sidecar integration
- **Plane Isolation**: Ops/chain/wallet plane separation
- **SOCKS Proxy**: All traffic forced through Tor SOCKS

## 🚀 Quick Start

### Complete Setup (Recommended)
```bash
# Build, deploy, setup Tor, and verify security
./build/scripts/lucid-gui-complete-setup.sh \
  --push \
  --deploy \
  --setup-tor \
  --verify-security
```

### Individual Components

#### 1. Build GUI Containers
```bash
./build/scripts/build-gui-distroless.sh \
  --services user,admin,node \
  --platform linux/amd64,linux/arm64 \
  --push
```

#### 2. Deploy to Raspberry Pi
```bash
./build/scripts/deploy-gui-pi.sh \
  --host raspberrypi.local \
  --services user,admin,node
```

#### 3. Setup Tor .onion Services
```bash
./build/scripts/setup-tor-gui-services.sh \
  --services user,admin,node
```

#### 4. Generate QR Codes
```bash
./build/scripts/generate-qr-bootstrap.sh \
  --format png \
  --save
```

#### 5. Verify Security Compliance
```bash
./build/scripts/verify-gui-security-compliance.sh \
  --services user,admin,node
```

## 📱 Launch Mechanisms

### 1. QR Code Bootstrap (Primary)
- **Purpose**: Zero-configuration access
- **Usage**: Pi displays QR codes on boot
- **Access**: Scan with mobile device → Tor Browser opens

### 2. Cloud-Init Auto-Setup
- **Purpose**: Automated deployment
- **Configuration**: `ops/cloud-init/lucid-gui-setup.yml`
- **Features**: Auto-start services, QR generation, desktop shortcuts

### 3. Desktop Shortcuts (Optional)
- **Purpose**: Local development/testing access
- **Location**: `/home/pi/Desktop/`
- **Format**: `.desktop` files with .onion URLs

## 🔧 Configuration

### Environment Variables
```bash
# Build configuration
REGISTRY="ghcr.io"
IMAGE_NAME="HamiGames/Lucid"
TAG="latest"
PLATFORM="linux/amd64,linux/arm64"

# Pi deployment
PI_HOST="raspberrypi.local"
PI_USER="pi"
PI_SSH_KEY="/path/to/ssh/key"

# GitHub integration
GITHUB_TOKEN="ghp_..."
GITHUB_SHA="abc123..."
```

### Docker Compose Configuration
```yaml
# infrastructure/compose/docker-compose.gui.yml
services:
  lucid-user-gui:
    image: ghcr.io/hamigames/lucid/user-gui:latest
    container_name: lucid-user-gui
    restart: unless-stopped
    ports:
      - "3001:3001"
    environment:
      - NODE_ENV=production
      - TOR_SOCKS=127.0.0.1:9050
    networks:
      - lucid-gui-net
    profiles: ["gui", "user"]
```

### Tor Configuration
```bash
# /etc/tor/torrc.d/lucid-gui.conf
HiddenServiceDir /var/lib/tor/lucid-user-gui
HiddenServicePort 80 127.0.0.1:3001

HiddenServiceDir /var/lib/tor/lucid-admin-gui
HiddenServicePort 80 127.0.0.1:3002

HiddenServiceDir /var/lib/tor/lucid-node-gui
HiddenServicePort 80 127.0.0.1:3003
```

## 🔒 Security Features

### Distroless Compliance
- **Base Images**: `gcr.io/distroless/nodejs20-debian12`
- **User**: Non-root (UID 65532)
- **Filesystem**: Read-only where possible
- **Shells**: None in runtime containers
- **Package Managers**: None in runtime

### Trust-Nothing Policy
- **Client-Side Enforcement**: Policy validation in browser
- **Tor-Only Access**: No clearnet ingress
- **Onion-Only URLs**: All access via .onion services
- **SOCKS Proxy**: All traffic through Tor SOCKS

### Container Security
- **Security Options**: Seccomp profiles, capability dropping
- **Network Isolation**: Separate Docker networks
- **Resource Limits**: CPU and memory constraints
- **Health Checks**: Container health monitoring

## 📊 Monitoring & Verification

### Security Compliance Verification
```bash
# Run comprehensive security checks
./build/scripts/verify-gui-security-compliance.sh \
  --services user,admin,node \
  --verbose
```

### Health Checks
```bash
# Check container status
docker ps --filter "name=lucid-.*-gui"

# Check Tor services
systemctl status tor

# Check .onion services
ls -la /var/lib/tor/lucid-*-gui/hostname
```

### Logs
```bash
# Container logs
docker logs lucid-user-gui
docker logs lucid-admin-gui
docker logs lucid-node-gui

# Tor logs
tail -f /var/log/tor/notice.log
```

## 🛠️ Development

### Project Structure
```
apps/
├── gui-user/           # User GUI application
│   ├── src/
│   ├── Dockerfile.distroless
│   └── package.json
├── gui-admin/          # Admin GUI application
│   ├── src/
│   ├── Dockerfile.distroless
│   └── package.json
└── gui-node/           # Node GUI application
    ├── src/
    ├── Dockerfile.distroless
    └── package.json

build/scripts/
├── build-gui-distroless.sh
├── deploy-gui-pi.sh
├── setup-tor-gui-services.sh
├── generate-qr-bootstrap.sh
├── verify-gui-security-compliance.sh
└── lucid-gui-complete-setup.sh

ops/cloud-init/
└── lucid-gui-setup.yml
```

### Building Locally
```bash
# Build specific GUI service
cd apps/gui-user
docker build -f Dockerfile.distroless -t lucid-user-gui:latest .

# Build all GUI services
./build/scripts/build-gui-distroless.sh --services user,admin,node
```

### Testing
```bash
# Unit tests
cd apps/gui-user
npm test

# Integration tests
./build/scripts/verify-gui-security-compliance.sh --services user

# End-to-end tests
pytest tests/integration/gui-integration/
```

## 🔄 CI/CD Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/gui-build-deploy.yml
name: GUI Build and Deploy

on:
  push:
    branches: [main]
    paths: ['apps/gui-*/**', 'build/scripts/**']

jobs:
  build-gui:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build GUI containers
        run: ./build/scripts/build-gui-distroless.sh --push
      - name: Deploy to Pi
        run: ./build/scripts/deploy-gui-pi.sh --deploy
      - name: Verify security
        run: ./build/scripts/verify-gui-security-compliance.sh
```

### Automated Deployment
- **Triggers**: Push to main branch
- **Build**: Multi-platform distroless containers
- **Deploy**: Automatic deployment to Pi
- **Verify**: Security compliance checks
- **Notify**: Success/failure notifications

## 📚 API Integration

### Backend Services
- **Session Gateway**: User session management
- **Blockchain Core**: Admin operations
- **Tron Payment Service**: Node monitoring

### Service Discovery
```typescript
// Example service discovery in GUI
const serviceUrl = await beta.resolve('sessions-gateway@ops');
const response = await fetch(`${serviceUrl}/api/sessions`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### Tor HTTP Client
```typescript
// Example Tor HTTP client
import { SocksProxyAgent } from 'socks-proxy-agent';

const agent = new SocksProxyAgent('socks5://127.0.0.1:9050');
const response = await fetch('https://example.onion', {
  agent: agent
});
```

## 🐛 Troubleshooting

### Common Issues

#### GUI Not Accessible
```bash
# Check container status
docker ps | grep lucid-.*-gui

# Check Tor service
systemctl status tor

# Check .onion service
cat /var/lib/tor/lucid-user-gui/hostname
```

#### Tor Connection Issues
```bash
# Test Tor SOCKS proxy
curl --socks5 127.0.0.1:9050 http://check.torproject.org/

# Check Tor logs
tail -f /var/log/tor/notice.log

# Restart Tor service
sudo systemctl restart tor
```

#### Container Build Issues
```bash
# Check Docker build logs
docker build --no-cache -f apps/gui-user/Dockerfile.distroless .

# Verify distroless compliance
./build/scripts/verify-gui-security-compliance.sh --services user
```

### Debug Mode
```bash
# Enable verbose logging
./build/scripts/lucid-gui-complete-setup.sh --verbose

# Check container logs
docker logs -f lucid-user-gui

# Monitor Tor connections
sudo netstat -tulpn | grep :9050
```

## 📖 Documentation

### Related Documents
- [SPEC-5 — Web-Based GUI System Architecture](docs/build-docs/Build_guide_docs/Spec-5 — Web-Based GUI System Architecture.md)
- [SPEC-1B-v2-DISTROLESS](docs/build-docs/Build_guide_docs/SPEC-1B-v2-DISTROLESS.md)
- [SPEC-1A — Background & Requirements](docs/build-docs/Build_guide_docs/Spec-1a — Lucid Rdp_ Background & Requirements.txt)

### API Documentation
- **User GUI API**: Session management, policy enforcement
- **Admin GUI API**: System administration, manifest viewing
- **Node GUI API**: PoOT monitoring, payout tracking

## 🤝 Contributing

### Development Setup
1. Clone the repository
2. Install dependencies: `npm install`
3. Start development server: `npm run dev`
4. Run tests: `npm test`

### Code Standards
- **TypeScript**: Strict mode enabled
- **ESLint**: Airbnb configuration
- **Prettier**: Code formatting
- **Testing**: Jest + React Testing Library

### Pull Request Process
1. Create feature branch
2. Make changes with tests
3. Run security compliance checks
4. Submit pull request
5. Wait for CI/CD verification

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Getting Help
- **Documentation**: Check the docs/ directory
- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for questions
- **Security**: Report security issues privately

### Contact
- **GitHub**: [HamiGames/Lucid](https://github.com/HamiGames/Lucid)
- **Email**: security@lucid-rdp.com (for security issues)

---

**Lucid RDP GUI System** - Secure, Tor-only, distroless web interfaces for blockchain-anchored remote desktop platform.
