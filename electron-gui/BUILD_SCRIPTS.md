# Electron GUI Build Scripts

## Overview

This document provides comprehensive build scripts for the Electron GUI application, ensuring compatibility with the Docker build process and API build progression.

## Build Scripts

### Main Build Script

**File**: `scripts/build.js`

```javascript
#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class ElectronGUIBuilder {
  constructor() {
    this.projectRoot = path.join(__dirname, '..');
    this.distDir = path.join(this.projectRoot, 'dist');
    this.assetsDir = path.join(this.projectRoot, 'assets');
  }

  async build() {
    console.log('🚀 Starting Electron GUI Build Process...');
    
    try {
      // Step 1: Clean previous builds
      await this.clean();
      
      // Step 2: Install dependencies
      await this.installDependencies();
      
      // Step 3: Build main process
      await this.buildMainProcess();
      
      // Step 4: Build renderer processes
      await this.buildRendererProcesses();
      
      // Step 5: Copy assets
      await this.copyAssets();
      
      // Step 6: Validate build
      await this.validateBuild();
      
      console.log('✅ Electron GUI Build Complete!');
      
    } catch (error) {
      console.error('❌ Build failed:', error.message);
      process.exit(1);
    }
  }

  async clean() {
    console.log('🧹 Cleaning previous builds...');
    
    if (fs.existsSync(this.distDir)) {
      fs.rmSync(this.distDir, { recursive: true, force: true });
    }
    
    fs.mkdirSync(this.distDir, { recursive: true });
  }

  async installDependencies() {
    console.log('📦 Installing dependencies...');
    
    execSync('npm install', { 
      cwd: this.projectRoot, 
      stdio: 'inherit' 
    });
  }

  async buildMainProcess() {
    console.log('🔧 Building main process...');
    
    execSync('npm run build:main', { 
      cwd: this.projectRoot, 
      stdio: 'inherit' 
    });
  }

  async buildRendererProcesses() {
    console.log('🎨 Building renderer processes...');
    
    execSync('npm run build:renderer', { 
      cwd: this.projectRoot, 
      stdio: 'inherit' 
    });
  }

  async copyAssets() {
    console.log('📁 Copying assets...');
    
    const assetsToCopy = [
      'assets/icons',
      'assets/images',
      'assets/tor',
      'configs',
      'package.json'
    ];
    
    for (const asset of assetsToCopy) {
      const src = path.join(this.projectRoot, asset);
      const dest = path.join(this.distDir, asset);
      
      if (fs.existsSync(src)) {
        fs.cpSync(src, dest, { recursive: true });
      }
    }
  }

  async validateBuild() {
    console.log('✅ Validating build...');
    
    const requiredFiles = [
      'main/index.js',
      'renderer/user/index.js',
      'renderer/developer/index.js',
      'renderer/node/index.js',
      'renderer/admin/index.js',
      'package.json'
    ];
    
    for (const file of requiredFiles) {
      const filePath = path.join(this.distDir, file);
      if (!fs.existsSync(filePath)) {
        throw new Error(`Required file missing: ${file}`);
      }
    }
    
    console.log('✅ Build validation successful!');
  }
}

// Run build if called directly
if (require.main === module) {
  const builder = new ElectronGUIBuilder();
  builder.build();
}

module.exports = ElectronGUIBuilder;
```

### Development Script

**File**: `scripts/dev.js`

```javascript
#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

class ElectronGUIDeveloper {
  constructor() {
    this.projectRoot = path.join(__dirname, '..');
    this.processes = [];
  }

  async start() {
    console.log('🚀 Starting Electron GUI Development...');
    
    try {
      // Start main process
      await this.startMainProcess();
      
      // Start renderer processes
      await this.startRendererProcesses();
      
      // Start Electron
      await this.startElectron();
      
      console.log('✅ Development environment ready!');
      
    } catch (error) {
      console.error('❌ Development startup failed:', error.message);
      this.cleanup();
      process.exit(1);
    }
  }

  async startMainProcess() {
    console.log('🔧 Starting main process...');
    
    const mainProcess = spawn('npm', ['run', 'dev:main'], {
      cwd: this.projectRoot,
      stdio: 'inherit',
      shell: true
    });
    
    this.processes.push(mainProcess);
  }

  async startRendererProcesses() {
    console.log('🎨 Starting renderer processes...');
    
    const rendererProcess = spawn('npm', ['run', 'dev:renderer'], {
      cwd: this.projectRoot,
      stdio: 'inherit',
      shell: true
    });
    
    this.processes.push(rendererProcess);
  }

  async startElectron() {
    console.log('⚡ Starting Electron...');
    
    const electronProcess = spawn('electron', ['.'], {
      cwd: this.projectRoot,
      stdio: 'inherit',
      shell: true
    });
    
    this.processes.push(electronProcess);
  }

  cleanup() {
    console.log('🧹 Cleaning up processes...');
    
    this.processes.forEach(process => {
      if (process && !process.killed) {
        process.kill();
      }
    });
  }
}

// Handle process termination
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down development environment...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n🛑 Shutting down development environment...');
  process.exit(0);
});

// Run development if called directly
if (require.main === module) {
  const developer = new ElectronGUIDeveloper();
  developer.start();
}

module.exports = ElectronGUIDeveloper;
```

### Pi Deployment Script

**File**: `scripts/deploy-pi.js`

```javascript
#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class PiDeployer {
  constructor() {
    this.projectRoot = path.join(__dirname, '..');
    this.distDir = path.join(this.projectRoot, 'dist');
    this.piConfig = {
      host: '192.168.0.75',
      user: 'pickme',
      port: 22,
      deployDir: '/opt/lucid/electron-gui'
    };
  }

  async deploy() {
    console.log('🚀 Starting Pi Deployment...');
    
    try {
      // Step 1: Build application
      await this.build();
      
      // Step 2: Create deployment package
      await this.createDeploymentPackage();
      
      // Step 3: Deploy to Pi
      await this.deployToPi();
      
      // Step 4: Setup services on Pi
      await this.setupServices();
      
      console.log('✅ Pi Deployment Complete!');
      
    } catch (error) {
      console.error('❌ Deployment failed:', error.message);
      process.exit(1);
    }
  }

  async build() {
    console.log('🔧 Building application...');
    
    execSync('npm run build', { 
      cwd: this.projectRoot, 
      stdio: 'inherit' 
    });
  }

  async createDeploymentPackage() {
    console.log('📦 Creating deployment package...');
    
    const packageDir = path.join(this.distDir, 'package');
    fs.mkdirSync(packageDir, { recursive: true });
    
    // Copy application files
    fs.cpSync(this.distDir, packageDir, { recursive: true });
    
    // Create startup script
    const startupScript = `#!/bin/bash
cd /opt/lucid/electron-gui
export NODE_ENV=production
export ELECTRON_ENV=production
export TOR_ENABLED=true
export DOCKER_HOST=tcp://localhost:2375
./lucid-desktop
`;
    
    fs.writeFileSync(
      path.join(packageDir, 'start.sh'), 
      startupScript
    );
    
    // Make startup script executable
    fs.chmodSync(path.join(packageDir, 'start.sh'), '755');
  }

  async deployToPi() {
    console.log('📡 Deploying to Pi...');
    
    const { host, user, port, deployDir } = this.piConfig;
    
    // Create deployment directory on Pi
    execSync(`ssh -p ${port} ${user}@${host} "mkdir -p ${deployDir}"`);
    
    // Copy files to Pi
    execSync(`scp -r -P ${port} ${this.distDir}/* ${user}@${host}:${deployDir}/`);
    
    // Set permissions
    execSync(`ssh -p ${port} ${user}@${host} "chmod +x ${deployDir}/start.sh"`);
  }

  async setupServices() {
    console.log('⚙️ Setting up services on Pi...');
    
    const { host, user, port, deployDir } = this.piConfig;
    
    // Create systemd service file
    const serviceFile = `[Unit]
Description=Lucid Desktop Application
After=network.target docker.service

[Service]
Type=simple
User=${user}
WorkingDirectory=${deployDir}
ExecStart=${deployDir}/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
`;
    
    // Write service file to Pi
    execSync(`ssh -p ${port} ${user}@${host} "sudo tee /etc/systemd/system/lucid-desktop.service > /dev/null"`, {
      input: serviceFile
    });
    
    // Enable and start service
    execSync(`ssh -p ${port} ${user}@${host} "sudo systemctl daemon-reload"`);
    execSync(`ssh -p ${port} ${user}@${host} "sudo systemctl enable lucid-desktop"`);
    execSync(`ssh -p ${port} ${user}@${host} "sudo systemctl start lucid-desktop"`);
  }
}

// Run deployment if called directly
if (require.main === module) {
  const deployer = new PiDeployer();
  deployer.deploy();
}

module.exports = PiDeployer;
```

### Tor Status Script

**File**: `scripts/tor-status.js`

```javascript
#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class TorStatusChecker {
  constructor() {
    this.projectRoot = path.join(__dirname, '..');
    this.torConfig = {
      socksPort: 9050,
      controlPort: 9051,
      dataDirectory: path.join(this.projectRoot, 'assets', 'tor')
    };
  }

  async checkStatus() {
    console.log('🔍 Checking Tor Status...');
    
    try {
      // Check if Tor process is running
      const isRunning = await this.checkTorProcess();
      
      if (!isRunning) {
        console.log('❌ Tor is not running');
        return false;
      }
      
      // Check SOCKS5 proxy
      const socksStatus = await this.checkSocksProxy();
      
      // Check control port
      const controlStatus = await this.checkControlPort();
      
      // Check circuit status
      const circuitStatus = await this.checkCircuitStatus();
      
      console.log('✅ Tor Status:');
      console.log(`   SOCKS5 Proxy: ${socksStatus ? '✅ Connected' : '❌ Failed'}`);
      console.log(`   Control Port: ${controlStatus ? '✅ Connected' : '❌ Failed'}`);
      console.log(`   Circuits: ${circuitStatus ? '✅ Active' : '❌ None'}`);
      
      return socksStatus && controlStatus && circuitStatus;
      
    } catch (error) {
      console.error('❌ Tor status check failed:', error.message);
      return false;
    }
  }

  async checkTorProcess() {
    try {
      const result = execSync('ps aux | grep tor | grep -v grep', { 
        encoding: 'utf8' 
      });
      return result.trim().length > 0;
    } catch (error) {
      return false;
    }
  }

  async checkSocksProxy() {
    try {
      const result = execSync(`curl -s --socks5 127.0.0.1:${this.torConfig.socksPort} http://httpbin.org/ip`, {
        encoding: 'utf8',
        timeout: 5000
      });
      return result.includes('origin');
    } catch (error) {
      return false;
    }
  }

  async checkControlPort() {
    try {
      const result = execSync(`echo "GETINFO version" | nc 127.0.0.1 ${this.torConfig.controlPort}`, {
        encoding: 'utf8',
        timeout: 5000
      });
      return result.includes('version');
    } catch (error) {
      return false;
    }
  }

  async checkCircuitStatus() {
    try {
      const result = execSync(`echo "GETINFO circuit-status" | nc 127.0.0.1 ${this.torConfig.controlPort}`, {
        encoding: 'utf8',
        timeout: 5000
      });
      return result.includes('BUILT');
    } catch (error) {
      return false;
    }
  }
}

// Run status check if called directly
if (require.main === module) {
  const checker = new TorStatusChecker();
  checker.checkStatus();
}

module.exports = TorStatusChecker;
```

### Docker Status Script

**File**: `scripts/docker-status.js`

```javascript
#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class DockerStatusChecker {
  constructor() {
    this.projectRoot = path.join(__dirname, '..');
    this.dockerConfig = {
      host: '192.168.0.75',
      port: 2375,
      ssh: {
        host: '192.168.0.75',
        user: 'pickme',
        port: 22
      }
    };
  }

  async checkStatus() {
    console.log('🔍 Checking Docker Status...');
    
    try {
      // Check local Docker
      const localDocker = await this.checkLocalDocker();
      
      // Check remote Docker
      const remoteDocker = await this.checkRemoteDocker();
      
      // Check services
      const services = await this.checkServices();
      
      console.log('✅ Docker Status:');
      console.log(`   Local Docker: ${localDocker ? '✅ Running' : '❌ Not Running'}`);
      console.log(`   Remote Docker: ${remoteDocker ? '✅ Connected' : '❌ Failed'}`);
      console.log(`   Services: ${services.length} running`);
      
      return localDocker && remoteDocker;
      
    } catch (error) {
      console.error('❌ Docker status check failed:', error.message);
      return false;
    }
  }

  async checkLocalDocker() {
    try {
      execSync('docker version', { stdio: 'pipe' });
      return true;
    } catch (error) {
      return false;
    }
  }

  async checkRemoteDocker() {
    try {
      const { host, port, ssh } = this.dockerConfig;
      execSync(`ssh -p ${ssh.port} ${ssh.user}@${ssh.host} "docker version"`, { 
        stdio: 'pipe' 
      });
      return true;
    } catch (error) {
      return false;
    }
  }

  async checkServices() {
    try {
      const { host, port, ssh } = this.dockerConfig;
      const result = execSync(`ssh -p ${ssh.port} ${ssh.user}@${ssh.host} "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"`, {
        encoding: 'utf8'
      });
      
      const services = result.split('\n').filter(line => 
        line.includes('lucid-') && line.includes('Up')
      );
      
      return services;
    } catch (error) {
      return [];
    }
  }
}

// Run status check if called directly
if (require.main === module) {
  const checker = new DockerStatusChecker();
  checker.checkStatus();
}

module.exports = DockerStatusChecker;
```

### API Test Script

**File**: `scripts/api-test.js`

```javascript
#!/usr/bin/env node

const axios = require('axios');
const { SocksProxyAgent } = require('socks-proxy-agent');

class APITester {
  constructor() {
    this.torConfig = {
      socksPort: 9050,
      proxy: {
        host: '127.0.0.1',
        port: 9050,
        protocol: 'socks5'
      }
    };
    
    this.apiEndpoints = {
      gateway: 'http://192.168.0.75:8080',
      auth: 'http://192.168.0.75:8089',
      admin: 'http://192.168.0.75:8083',
      blockchain: 'http://192.168.0.75:8084',
      session: 'http://192.168.0.75:8087',
      node: 'http://192.168.0.75:8095'
    };
  }

  async testAPIs() {
    console.log('🔍 Testing API Connectivity...');
    
    try {
      // Test Tor proxy
      const torStatus = await this.testTorProxy();
      
      if (!torStatus) {
        console.log('❌ Tor proxy not available');
        return false;
      }
      
      // Test each API endpoint
      const results = await Promise.allSettled([
        this.testEndpoint('Gateway', this.apiEndpoints.gateway),
        this.testEndpoint('Auth', this.apiEndpoints.auth),
        this.testEndpoint('Admin', this.apiEndpoints.admin),
        this.testEndpoint('Blockchain', this.apiEndpoints.blockchain),
        this.testEndpoint('Session', this.apiEndpoints.session),
        this.testEndpoint('Node', this.apiEndpoints.node)
      ]);
      
      console.log('✅ API Test Results:');
      
      results.forEach((result, index) => {
        const endpoint = Object.keys(this.apiEndpoints)[index];
        if (result.status === 'fulfilled') {
          console.log(`   ${endpoint}: ✅ ${result.value.status}`);
        } else {
          console.log(`   ${endpoint}: ❌ ${result.reason.message}`);
        }
      });
      
      return results.every(result => result.status === 'fulfilled');
      
    } catch (error) {
      console.error('❌ API test failed:', error.message);
      return false;
    }
  }

  async testTorProxy() {
    try {
      const agent = new SocksProxyAgent(`socks5://${this.torConfig.proxy.host}:${this.torConfig.proxy.port}`);
      const response = await axios.get('http://httpbin.org/ip', {
        httpsAgent: agent,
        timeout: 10000
      });
      
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }

  async testEndpoint(name, url) {
    try {
      const agent = new SocksProxyAgent(`socks5://${this.torConfig.proxy.host}:${this.torConfig.proxy.port}`);
      const response = await axios.get(`${url}/health`, {
        httpsAgent: agent,
        timeout: 5000
      });
      
      return {
        name,
        status: response.status,
        responseTime: response.headers['x-response-time'] || 'N/A'
      };
    } catch (error) {
      throw new Error(`${name}: ${error.message}`);
    }
  }
}

// Run API test if called directly
if (require.main === module) {
  const tester = new APITester();
  tester.testAPIs();
}

module.exports = APITester;
```

## Package.json Scripts

### Development Scripts

```json
{
  "scripts": {
    "dev": "concurrently \"npm run dev:main\" \"npm run dev:renderer\"",
    "dev:main": "tsc -p tsconfig.main.json && electron .",
    "dev:renderer": "webpack serve --config webpack.renderer.config.js",
    "dev:full": "node scripts/dev.js"
  }
}
```

### Build Scripts

```json
{
  "scripts": {
    "build": "npm run build:main && npm run build:renderer",
    "build:main": "tsc -p tsconfig.main.json",
    "build:renderer": "webpack --config webpack.renderer.config.js",
    "build:full": "node scripts/build.js"
  }
}
```

### Package Scripts

```json
{
  "scripts": {
    "package": "electron-builder",
    "package:win": "electron-builder --win",
    "package:linux": "electron-builder --linux",
    "package:mac": "electron-builder --mac",
    "package:all": "electron-builder --win --linux --mac"
  }
}
```

### Test Scripts

```json
{
  "scripts": {
    "test": "jest",
    "test:e2e": "jest --config jest.e2e.config.js",
    "test:coverage": "jest --coverage",
    "test:watch": "jest --watch"
  }
}
```

### Deployment Scripts

```json
{
  "scripts": {
    "deploy:pi": "node scripts/deploy-pi.js",
    "deploy:docker": "docker build -t lucid-electron-gui .",
    "deploy:all": "npm run build && npm run package && npm run deploy:pi"
  }
}
```

### Status Scripts

```json
{
  "scripts": {
    "status:tor": "node scripts/tor-status.js",
    "status:docker": "node scripts/docker-status.js",
    "status:api": "node scripts/api-test.js",
    "status:all": "npm run status:tor && npm run status:docker && npm run status:api"
  }
}
```

## Usage Examples

### Development

```bash
# Start development environment
npm run dev

# Start with full logging
DEBUG=electron-gui:* npm run dev

# Start specific GUI
npm run dev:main
npm run dev:renderer
```

### Building

```bash
# Build application
npm run build

# Build with full process
npm run build:full

# Build specific components
npm run build:main
npm run build:renderer
```

### Testing

```bash
# Run all tests
npm test

# Run E2E tests
npm run test:e2e

# Run with coverage
npm run test:coverage

# Run specific test
npm test -- --testNamePattern="admin-gui"
```

### Deployment

```bash
# Deploy to Pi
npm run deploy:pi

# Package for distribution
npm run package

# Package for specific platform
npm run package:linux
npm run package:win
npm run package:mac
```

### Status Checking

```bash
# Check Tor status
npm run status:tor

# Check Docker status
npm run status:docker

# Check API connectivity
npm run status:api

# Check all statuses
npm run status:all
```

---

**Created**: 2025-01-27  
**Project**: Lucid Electron GUI Build Scripts  
**Status**: Complete Build Scripts ✅
