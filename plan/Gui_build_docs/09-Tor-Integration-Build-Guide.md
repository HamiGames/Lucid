# Tor Integration Build Guide

## Overview

This document provides comprehensive guidance for integrating Tor connectivity into the Lucid Electron GUI system, ensuring secure, anonymous communication with the Lucid API backend through SOCKS5 proxy connections.

## Tor Integration Architecture

### 1. Tor Connection Flow

```
┌─────────────────┐    Tor SOCKS5     ┌─────────────────┐    .onion API     ┌─────────────────┐
│   Electron GUI  │ ─────────────────► │   Tor Network   │ ─────────────────► │  Lucid Backend  │
│   (Main Process)│                    │   (SOCKS5:9050) │                    │   (API Gateway) │
└─────────────────┘                    └─────────────────┘                    └─────────────────┘
         │                                     │                                     │
         │                                     │                                     │
         ▼                                     ▼                                     ▼
┌─────────────────┐                    ┌─────────────────┐                    ┌─────────────────┐
│  Tor Manager    │                    │  Circuit Info   │                    │  API Responses  │
│  - Start/Stop   │                    │  - Circuit ID   │                    │  - JSON Data    │
│  - Status Check │                    │  - Exit Nodes   │                    │  - Error Codes  │
│  - Health Check │                    │  - Latency      │                    │  - Rate Limits  │
└─────────────────┘                    └─────────────────┘                    └─────────────────┘
```

### 2. Tor Status Indicators

#### Green Light Indicator
- **Connected**: Green circle with "Secure Connection" text
- **Connecting**: Yellow circle with "Connecting..." text  
- **Disconnected**: Red circle with "Disconnected" text
- **Error**: Red circle with "Connection Error" text

## Tor Manager Implementation

### 1. Main Process Tor Manager (`main/tor-manager.ts`)

```typescript
import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as path from 'path';
import * as fs from 'fs';

interface TorConfig {
  socksPort: number;
  controlPort: number;
  dataDirectory: string;
  logLevel: 'notice' | 'info' | 'warn' | 'err';
  exitNodes: string[];
  strictNodes: boolean;
  circuitBuildTimeout: number;
  newCircuitPeriod: number;
}

interface TorStatus {
  connected: boolean;
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  circuitCount: number;
  lastConnected: Date | null;
  bootstrapProgress: number;
  errorMessage?: string;
}

class TorManager extends EventEmitter {
  private torProcess: ChildProcess | null = null;
  private status: TorStatus;
  private config: TorConfig;
  private torrcPath: string;
  private dataDir: string;
  private isStarting: boolean = false;
  private healthCheckInterval: NodeJS.Timeout | null = null;

  constructor() {
    super();
    this.status = {
      connected: false,
      status: 'disconnected',
      circuitCount: 0,
      lastConnected: null,
      bootstrapProgress: 0
    };
    
    this.config = {
      socksPort: 9050,
      controlPort: 9051,
      dataDirectory: path.join(__dirname, '../assets/tor/data'),
      logLevel: 'notice',
      exitNodes: [],
      strictNodes: false,
      circuitBuildTimeout: 60,
      newCircuitPeriod: 30
    };
    
    this.torrcPath = path.join(__dirname, '../configs/torrc');
    this.dataDir = this.config.dataDirectory;
    
    this.setupDataDirectory();
    this.setupTorrc();
  }

  async startTor(): Promise<void> {
    if (this.isStarting || this.status.connected) {
      return;
    }

    this.isStarting = true;
    this.status.status = 'connecting';
    this.emit('statusChange', this.status);

    try {
      await this.startTorProcess();
      await this.waitForConnection();
      this.startHealthCheck();
      
      this.status.connected = true;
      this.status.status = 'connected';
      this.status.lastConnected = new Date();
      this.emit('statusChange', this.status);
      
    } catch (error) {
      this.status.status = 'error';
      this.status.errorMessage = error.message;
      this.emit('statusChange', this.status);
      throw error;
    } finally {
      this.isStarting = false;
    }
  }

  async stopTor(): Promise<void> {
    if (!this.torProcess) {
      return;
    }

    this.status.status = 'disconnected';
    this.status.connected = false;
    this.emit('statusChange', this.status);

    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }

    return new Promise((resolve) => {
      if (this.torProcess) {
        this.torProcess.on('exit', () => {
          this.torProcess = null;
          resolve();
        });
        this.torProcess.kill('SIGTERM');
      } else {
        resolve();
      }
    });
  }

  getStatus(): TorStatus {
    return { ...this.status };
  }

  isConnected(): boolean {
    return this.status.connected;
  }

  private async startTorProcess(): Promise<void> {
    const torExecutable = this.getTorExecutable();
    
    this.torProcess = spawn(torExecutable, [
      '-f', this.torrcPath,
      '--DataDirectory', this.dataDir
    ]);

    this.torProcess.stdout?.on('data', (data) => {
      this.parseTorOutput(data.toString());
    });

    this.torProcess.stderr?.on('data', (data) => {
      this.parseTorError(data.toString());
    });

    this.torProcess.on('exit', (code) => {
      if (code !== 0) {
        this.status.status = 'error';
        this.status.errorMessage = `Tor process exited with code ${code}`;
        this.emit('statusChange', this.status);
      }
    });
  }

  private async waitForConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Tor connection timeout'));
      }, 60000); // 60 second timeout

      const checkConnection = () => {
        if (this.status.connected) {
          clearTimeout(timeout);
          resolve();
        } else if (this.status.status === 'error') {
          clearTimeout(timeout);
          reject(new Error(this.status.errorMessage || 'Tor connection failed'));
        } else {
          setTimeout(checkConnection, 1000);
        }
      };

      checkConnection();
    });
  }

  private startHealthCheck(): void {
    this.healthCheckInterval = setInterval(async () => {
      try {
        await this.checkTorHealth();
      } catch (error) {
        this.status.status = 'error';
        this.status.errorMessage = error.message;
        this.emit('statusChange', this.status);
      }
    }, 30000); // Check every 30 seconds
  }

  private async checkTorHealth(): Promise<void> {
    // Check if SOCKS5 port is responding
    const net = require('net');
    const socket = new net.Socket();
    
    return new Promise((resolve, reject) => {
      socket.setTimeout(5000);
      
      socket.on('connect', () => {
        socket.destroy();
        resolve();
      });
      
      socket.on('timeout', () => {
        socket.destroy();
        reject(new Error('Tor health check timeout'));
      });
      
      socket.on('error', (error) => {
        reject(error);
      });
      
      socket.connect(this.config.socksPort, '127.0.0.1');
    });
  }

  private parseTorOutput(output: string): void {
    const lines = output.split('\n');
    
    for (const line of lines) {
      if (line.includes('Bootstrap')) {
        const match = line.match(/Bootstrap (\d+)%: (.+)/);
        if (match) {
          this.status.bootstrapProgress = parseInt(match[1]);
          this.emit('bootstrapProgress', this.status.bootstrapProgress);
        }
      }
      
      if (line.includes('Bootstrapped 100%')) {
        this.status.connected = true;
        this.status.status = 'connected';
        this.emit('statusChange', this.status);
      }
    }
  }

  private parseTorError(error: string): void {
    console.error('Tor error:', error);
    
    if (error.includes('Permission denied') || error.includes('Address already in use')) {
      this.status.status = 'error';
      this.status.errorMessage = 'Tor port already in use or permission denied';
      this.emit('statusChange', this.status);
    }
  }

  private getTorExecutable(): string {
    const platform = process.platform;
    const arch = process.arch;
    
    if (platform === 'win32') {
      return path.join(__dirname, '../assets/tor/tor.exe');
    } else if (platform === 'darwin') {
      return path.join(__dirname, '../assets/tor/tor-macos');
    } else {
      return path.join(__dirname, '../assets/tor/tor-linux');
    }
  }

  private setupDataDirectory(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  private setupTorrc(): void {
    const torrcContent = `
# Tor configuration for Lucid GUI
SocksPort ${this.config.socksPort}
ControlPort ${this.config.controlPort}
DataDirectory ${this.dataDir}
Log notice file ${path.join(this.dataDir, 'tor.log')}
Log notice stdout

# Security settings
SafeLogging 1
DisableDebuggerAttachment 1

# Performance settings
CircuitBuildTimeout ${this.config.circuitBuildTimeout}
NewCircuitPeriod ${this.config.newCircuitPeriod}
MaxCircuitDirtiness 600

# Connection settings
ConnectionPadding 1
ReducedConnectionPadding 0

# Exit node settings
${this.config.exitNodes.length > 0 ? `ExitNodes ${this.config.exitNodes.join(',')}` : ''}
${this.config.strictNodes ? 'StrictNodes 1' : 'StrictNodes 0'}

# Bridge settings (if needed)
# UseBridges 1
# Bridge obfs4 192.0.2.1:443 FINGERPRINT
`;

    fs.writeFileSync(this.torrcPath, torrcContent);
  }
}

export default TorManager;
```

### 2. Tor Status Hook (`renderer/common/hooks/useTorStatus.ts`)

```typescript
import { useState, useEffect } from 'react';
import { ipcRenderer } from 'electron';

interface TorStatus {
  connected: boolean;
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  circuitCount: number;
  lastConnected: Date | null;
  bootstrapProgress: number;
  errorMessage?: string;
}

export const useTorStatus = () => {
  const [status, setStatus] = useState<TorStatus>({
    connected: false,
    status: 'disconnected',
    circuitCount: 0,
    lastConnected: null,
    bootstrapProgress: 0
  });

  useEffect(() => {
    // Listen for Tor status updates from main process
    const handleTorStatusChange = (event: any, newStatus: TorStatus) => {
      setStatus(newStatus);
    };

    const handleBootstrapProgress = (event: any, progress: number) => {
      setStatus(prev => ({ ...prev, bootstrapProgress: progress }));
    };

    ipcRenderer.on('tor:status', handleTorStatusChange);
    ipcRenderer.on('tor:bootstrap', handleBootstrapProgress);

    // Request current status
    ipcRenderer.send('tor:getStatus');

    return () => {
      ipcRenderer.removeListener('tor:status', handleTorStatusChange);
      ipcRenderer.removeListener('tor:bootstrap', handleBootstrapProgress);
    };
  }, []);

  const connectTor = () => {
    ipcRenderer.send('tor:connect');
  };

  const disconnectTor = () => {
    ipcRenderer.send('tor:disconnect');
  };

  return {
    status,
    connectTor,
    disconnectTor
  };
};
```

### 3. Tor Indicator Component (`renderer/common/components/TorIndicator.tsx`)

```typescript
import React from 'react';
import { useTorStatus } from '../hooks/useTorStatus';

interface TorIndicatorProps {
  showDetails?: boolean;
  className?: string;
}

export const TorIndicator: React.FC<TorIndicatorProps> = ({ 
  showDetails = false, 
  className = '' 
}) => {
  const { status, connectTor, disconnectTor } = useTorStatus();

  const getStatusColor = () => {
    switch (status.status) {
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
        return 'bg-yellow-500';
      case 'disconnected':
        return 'bg-red-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = () => {
    switch (status.status) {
      case 'connected':
        return 'Secure Connection';
      case 'connecting':
        return 'Connecting...';
      case 'disconnected':
        return 'Disconnected';
      case 'error':
        return 'Connection Error';
      default:
        return 'Unknown';
    }
  };

  const getStatusIcon = () => {
    switch (status.status) {
      case 'connected':
        return '✓';
      case 'connecting':
        return '⟳';
      case 'disconnected':
        return '✗';
      case 'error':
        return '⚠';
      default:
        return '?';
    }
  };

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <div className="relative">
        <div className={`w-3 h-3 rounded-full ${getStatusColor()} transition-colors duration-300`} />
        {status.status === 'connecting' && (
          <div className="absolute inset-0 w-3 h-3 rounded-full border-2 border-yellow-300 animate-ping" />
        )}
      </div>
      
      <span className="text-sm font-medium text-gray-700">
        {getStatusIcon()} {getStatusText()}
      </span>
      
      {showDetails && (
        <div className="ml-2 text-xs text-gray-500">
          {status.status === 'connecting' && (
            <span>Bootstrap: {status.bootstrapProgress}%</span>
          )}
          {status.status === 'connected' && (
            <span>Circuits: {status.circuitCount}</span>
          )}
          {status.status === 'error' && status.errorMessage && (
            <span className="text-red-500">{status.errorMessage}</span>
          )}
        </div>
      )}
      
      <div className="flex space-x-1">
        {!status.connected && status.status !== 'connecting' && (
          <button
            onClick={connectTor}
            className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
          >
            Connect
          </button>
        )}
        
        {status.connected && (
          <button
            onClick={disconnectTor}
            className="px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
          >
            Disconnect
          </button>
        )}
      </div>
    </div>
  );
};
```

## Tor Proxy Configuration

### 1. SOCKS5 Proxy Setup

```typescript
// Tor proxy configuration for API requests
import { Agent } from 'https';
import { SocksProxyAgent } from 'socks-proxy-agent';

class TorProxyConfig {
  private torAgent: SocksProxyAgent;
  private isConnected: boolean = false;

  constructor() {
    this.torAgent = new SocksProxyAgent({
      hostname: '127.0.0.1',
      port: 9050,
      protocol: 'socks5'
    });
  }

  getAgent(): SocksProxyAgent {
    return this.torAgent;
  }

  async testConnection(): Promise<boolean> {
    try {
      const response = await fetch('http://httpbin.org/ip', {
        agent: this.torAgent
      });
      
      const data = await response.json();
      this.isConnected = true;
      return true;
    } catch (error) {
      this.isConnected = false;
      return false;
    }
  }

  isProxyConnected(): boolean {
    return this.isConnected;
  }
}

export default TorProxyConfig;
```

### 2. API Client with Tor Integration

```typescript
// Enhanced API client with Tor proxy support
import { TorProxyConfig } from './tor-proxy-config';
import { TorStatus } from './tor-types';

class TorApiClient {
  private torProxy: TorProxyConfig;
  private baseUrl: string;
  private timeout: number;

  constructor(baseUrl: string, timeout: number = 30000) {
    this.baseUrl = baseUrl;
    this.timeout = timeout;
    this.torProxy = new TorProxyConfig();
  }

  async request<T>(
    method: string,
    endpoint: string,
    data?: any,
    headers?: Record<string, string>
  ): Promise<ApiResponse<T>> {
    // Check if Tor is connected
    if (!this.torProxy.isProxyConnected()) {
      throw new Error('Tor proxy not connected');
    }

    const url = `${this.baseUrl}${endpoint}`;
    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers
      },
      agent: this.torProxy.getAgent(),
      timeout: this.timeout
    };

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      options.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url, options);
      const responseData = await response.json();

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return {
        success: true,
        data: responseData,
        status: response.status
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        status: 0
      };
    }
  }

  async get<T>(endpoint: string, headers?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('GET', endpoint, undefined, headers);
  }

  async post<T>(endpoint: string, data: any, headers?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('POST', endpoint, data, headers);
  }

  async put<T>(endpoint: string, data: any, headers?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', endpoint, data, headers);
  }

  async delete<T>(endpoint: string, headers?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', endpoint, undefined, headers);
  }
}
```

## Tor Configuration Files

### 1. Tor Configuration (`configs/torrc`)

```
# Tor configuration for Lucid GUI
# This file is automatically generated by TorManager

# Network settings
SocksPort 9050
ControlPort 9051
DataDirectory ./assets/tor/data

# Logging
Log notice file ./assets/tor/data/tor.log
Log notice stdout

# Security settings
SafeLogging 1
DisableDebuggerAttachment 1
CookieAuthentication 1
CookieAuthFile ./assets/tor/data/control_auth_cookie

# Performance settings
CircuitBuildTimeout 60
NewCircuitPeriod 30
MaxCircuitDirtiness 600
EnforceDistinctSubnets 1

# Connection settings
ConnectionPadding 1
ReducedConnectionPadding 0
PaddingRelay 1

# Exit node settings (optional)
# ExitNodes {us},{ca},{gb}
# StrictNodes 1

# Bridge settings (if needed for censorship circumvention)
# UseBridges 1
# Bridge obfs4 192.0.2.1:443 FINGERPRINT CERT=AUTH

# Hidden service settings (if needed)
# HiddenServiceDir ./assets/tor/data/hidden_service
# HiddenServicePort 80 127.0.0.1:8080
```

### 2. Tor Configuration JSON (`configs/tor.config.json`)

```json
{
  "tor": {
    "socksPort": 9050,
    "controlPort": 9051,
    "dataDirectory": "./assets/tor/data",
    "logLevel": "notice",
    "exitNodes": [],
    "strictNodes": false,
    "circuitBuildTimeout": 60,
    "newCircuitPeriod": 30,
    "maxCircuitDirtiness": 600,
    "enforceDistinctSubnets": true,
    "connectionPadding": true,
    "reducedConnectionPadding": false,
    "paddingRelay": true
  },
  "proxy": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 9050,
    "protocol": "socks5",
    "timeout": 30000,
    "retries": 3
  },
  "security": {
    "safeLogging": true,
    "disableDebuggerAttachment": true,
    "cookieAuthentication": true
  },
  "performance": {
    "circuitBuildTimeout": 60,
    "newCircuitPeriod": 30,
    "maxCircuitDirtiness": 600,
    "enforceDistinctSubnets": true
  }
}
```

## Tor Binary Management

### 1. Tor Binary Detection

```typescript
// Tor binary detection and management
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

class TorBinaryManager {
  private platform: string;
  private arch: string;
  private torPath: string;

  constructor() {
    this.platform = os.platform();
    this.arch = os.arch();
    this.torPath = this.detectTorBinary();
  }

  private detectTorBinary(): string {
    const basePath = path.join(__dirname, '../assets/tor');
    
    if (this.platform === 'win32') {
      return path.join(basePath, 'tor.exe');
    } else if (this.platform === 'darwin') {
      return path.join(basePath, 'tor-macos');
    } else if (this.platform === 'linux') {
      if (this.arch === 'arm64') {
        return path.join(basePath, 'tor-linux-arm64');
      } else {
        return path.join(basePath, 'tor-linux');
      }
    } else {
      throw new Error(`Unsupported platform: ${this.platform}`);
    }
  }

  getTorPath(): string {
    return this.torPath;
  }

  isTorAvailable(): boolean {
    return fs.existsSync(this.torPath);
  }

  async downloadTorBinary(): Promise<void> {
    // Implementation for downloading Tor binaries
    // This would be called during installation or setup
  }

  async verifyTorBinary(): Promise<boolean> {
    try {
      const { spawn } = require('child_process');
      const tor = spawn(this.torPath, ['--version']);
      
      return new Promise((resolve) => {
        tor.on('exit', (code) => {
          resolve(code === 0);
        });
        
        tor.on('error', () => {
          resolve(false);
        });
      });
    } catch (error) {
      return false;
    }
  }
}
```

### 2. Tor Binary Installation Script

```bash
#!/bin/bash
# install-tor-binaries.sh

set -e

TOR_VERSION="0.4.8.10"
ASSETS_DIR="./assets/tor"
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

echo "Installing Tor binaries for $PLATFORM-$ARCH..."

# Create assets directory
mkdir -p $ASSETS_DIR

# Download Tor binaries based on platform
case $PLATFORM in
  "linux")
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
      TOR_URL="https://dist.torproject.org/torbrowser/12.5.6/tor-browser-linux-arm64-12.5.6.tar.xz"
    else
      TOR_URL="https://dist.torproject.org/torbrowser/12.5.6/tor-browser-linux64-12.5.6.tar.xz"
    fi
    ;;
  "darwin")
    TOR_URL="https://dist.torproject.org/torbrowser/12.5.6/TorBrowser-12.5.6-osx64_en-US.dmg"
    ;;
  *)
    echo "Unsupported platform: $PLATFORM"
    exit 1
    ;;
esac

# Download and extract Tor
echo "Downloading Tor from $TOR_URL..."
wget -O tor-archive.tar.xz "$TOR_URL"

echo "Extracting Tor binaries..."
tar -xf tor-archive.tar.xz

# Copy Tor binary to assets directory
if [ "$PLATFORM" = "linux" ]; then
  cp tor-browser_en-US/Browser/TorBrowser/Tor/tor $ASSETS_DIR/tor-linux
  chmod +x $ASSETS_DIR/tor-linux
elif [ "$PLATFORM" = "darwin" ]; then
  # Mount DMG and copy Tor binary
  hdiutil attach TorBrowser-12.5.6-osx64_en-US.dmg
  cp /Volumes/Tor\ Browser/Tor\ Browser.app/Contents/MacOS/Tor $ASSETS_DIR/tor-macos
  chmod +x $ASSETS_DIR/tor-macos
  hdiutil detach /Volumes/Tor\ Browser
fi

# Clean up
rm -rf tor-archive.tar.xz tor-browser_en-US TorBrowser-12.5.6-osx64_en-US.dmg

echo "Tor binaries installed successfully!"
```

## Tor Security Configuration

### 1. Security Settings

```typescript
// Tor security configuration
interface TorSecurityConfig {
  safeLogging: boolean;
  disableDebuggerAttachment: boolean;
  cookieAuthentication: boolean;
  cookieAuthFile: string;
  hashedControlPassword?: string;
  controlPort: number;
  socksPort: number;
  dataDirectory: string;
}

class TorSecurityManager {
  private config: TorSecurityConfig;

  constructor() {
    this.config = {
      safeLogging: true,
      disableDebuggerAttachment: true,
      cookieAuthentication: true,
      cookieAuthFile: './assets/tor/data/control_auth_cookie',
      controlPort: 9051,
      socksPort: 9050,
      dataDirectory: './assets/tor/data'
    };
  }

  generateControlPassword(): string {
    // Generate a secure control password for Tor
    const crypto = require('crypto');
    return crypto.randomBytes(32).toString('hex');
  }

  hashControlPassword(password: string): string {
    // Hash the control password using Tor's method
    const crypto = require('crypto');
    return crypto.createHash('sha256').update(password).digest('hex');
  }

  setupSecurity(): void {
    // Setup security configurations
    this.setupDataDirectory();
    this.setupControlAuth();
    this.setupLogging();
  }

  private setupDataDirectory(): void {
    const fs = require('fs');
    if (!fs.existsSync(this.config.dataDirectory)) {
      fs.mkdirSync(this.config.dataDirectory, { recursive: true });
    }
  }

  private setupControlAuth(): void {
    // Setup control authentication
    const fs = require('fs');
    const authFile = path.join(this.config.dataDirectory, 'control_auth_cookie');
    
    if (!fs.existsSync(authFile)) {
      // Generate control authentication cookie
      this.generateControlCookie();
    }
  }

  private setupLogging(): void {
    // Setup secure logging
    const logDir = path.join(this.config.dataDirectory, 'logs');
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
  }

  private generateControlCookie(): void {
    // Generate Tor control authentication cookie
    // This would be implemented based on Tor's control protocol
  }
}
```

### 2. Circuit Management

```typescript
// Tor circuit management
class TorCircuitManager {
  private controlPort: number;
  private authCookie: string;

  constructor(controlPort: number, authCookie: string) {
    this.controlPort = controlPort;
    this.authCookie = authCookie;
  }

  async getCircuitInfo(): Promise<CircuitInfo[]> {
    // Get information about current Tor circuits
    const circuits = await this.sendControlCommand('GETINFO circuit-status');
    return this.parseCircuitInfo(circuits);
  }

  async newCircuit(): Promise<void> {
    // Create a new Tor circuit
    await this.sendControlCommand('SIGNAL NEWNYM');
  }

  async closeCircuit(circuitId: string): Promise<void> {
    // Close a specific circuit
    await this.sendControlCommand(`CLOSECIRCUIT ${circuitId}`);
  }

  private async sendControlCommand(command: string): Promise<string> {
    // Send command to Tor control port
    const net = require('net');
    const socket = new net.Socket();
    
    return new Promise((resolve, reject) => {
      socket.connect(this.controlPort, '127.0.0.1', () => {
        socket.write(`AUTHENTICATE ${this.authCookie}\r\n`);
        socket.write(`${command}\r\n`);
        socket.write('QUIT\r\n');
      });
      
      let response = '';
      socket.on('data', (data) => {
        response += data.toString();
      });
      
      socket.on('end', () => {
        resolve(response);
      });
      
      socket.on('error', (error) => {
        reject(error);
      });
    });
  }

  private parseCircuitInfo(circuitData: string): CircuitInfo[] {
    // Parse circuit information from Tor control response
    const circuits: CircuitInfo[] = [];
    const lines = circuitData.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('250 CIRCUIT_STATUS=')) {
        const circuitInfo = this.parseCircuitLine(line);
        if (circuitInfo) {
          circuits.push(circuitInfo);
        }
      }
    }
    
    return circuits;
  }

  private parseCircuitLine(line: string): CircuitInfo | null {
    // Parse individual circuit line
    const match = line.match(/250 CIRCUIT_STATUS=(\d+) (\w+)/);
    if (match) {
      return {
        id: match[1],
        status: match[2],
        buildFlags: [],
        purpose: '',
        timeCreated: 0,
        reason: '',
        remoteReason: '',
        hsState: '',
        rendQuery: '',
        rendCircId: '',
        rendCookie: '',
        purposeBuilt: '',
        timeCreated: 0,
        reason: '',
        remoteReason: '',
        hsState: '',
        rendQuery: '',
        rendCircId: '',
        rendCookie: ''
      };
    }
    return null;
  }
}

interface CircuitInfo {
  id: string;
  status: string;
  buildFlags: string[];
  purpose: string;
  timeCreated: number;
  reason: string;
  remoteReason: string;
  hsState: string;
  rendQuery: string;
  rendCircId: string;
  rendCookie: string;
  purposeBuilt: string;
}
```

## Testing Tor Integration

### 1. Tor Connection Tests

```typescript
// Tor integration tests
describe('Tor Integration', () => {
  let torManager: TorManager;
  let apiClient: TorApiClient;

  beforeEach(() => {
    torManager = new TorManager();
    apiClient = new TorApiClient('http://localhost:8080');
  });

  afterEach(async () => {
    await torManager.stopTor();
  });

  test('should start Tor process', async () => {
    await torManager.startTor();
    expect(torManager.isConnected()).toBe(true);
  });

  test('should connect to API through Tor proxy', async () => {
    await torManager.startTor();
    await torManager.waitForConnection();
    
    const response = await apiClient.get('/api/v1/health');
    expect(response.success).toBe(true);
  });

  test('should handle Tor connection errors', async () => {
    // Mock Tor connection failure
    jest.spyOn(torManager, 'startTor').mockRejectedValue(new Error('Tor connection failed'));
    
    await expect(torManager.startTor()).rejects.toThrow('Tor connection failed');
  });

  test('should retry API requests on Tor failure', async () => {
    const retryApiClient = new TorApiClient('http://localhost:8080', 5000);
    retryApiClient.setRetryConfig({ maxRetries: 3, retryDelay: 1000 });
    
    // Mock first two requests to fail, third to succeed
    let requestCount = 0;
    jest.spyOn(global, 'fetch').mockImplementation(() => {
      requestCount++;
      if (requestCount < 3) {
        return Promise.reject(new Error('Network error'));
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true })
      } as Response);
    });
    
    const response = await retryApiClient.get('/api/v1/test');
    expect(response.success).toBe(true);
    expect(requestCount).toBe(3);
  });
});
```

### 2. Tor Status Indicator Tests

```typescript
// Tor status indicator tests
describe('TorStatusIndicator', () => {
  let mockIpcRenderer: jest.Mocked<typeof ipcRenderer>;

  beforeEach(() => {
    mockIpcRenderer = ipcRenderer as jest.Mocked<typeof ipcRenderer>;
  });

  test('should display connected status', () => {
    const status: TorStatus = {
      connected: true,
      status: 'connected',
      circuitCount: 3,
      lastConnected: new Date(),
      bootstrapProgress: 100
    };

    render(<TorIndicator status={status} showDetails={true} />);
    
    expect(screen.getByText('✓ Secure Connection')).toBeInTheDocument();
    expect(screen.getByText('Circuits: 3')).toBeInTheDocument();
  });

  test('should display connecting status', () => {
    const status: TorStatus = {
      connected: false,
      status: 'connecting',
      circuitCount: 0,
      lastConnected: null,
      bootstrapProgress: 45
    };

    render(<TorIndicator status={status} showDetails={true} />);
    
    expect(screen.getByText('⟳ Connecting...')).toBeInTheDocument();
    expect(screen.getByText('Bootstrap: 45%')).toBeInTheDocument();
  });

  test('should display error status', () => {
    const status: TorStatus = {
      connected: false,
      status: 'error',
      circuitCount: 0,
      lastConnected: null,
      bootstrapProgress: 0,
      errorMessage: 'Connection failed'
    };

    render(<TorIndicator status={status} showDetails={true} />);
    
    expect(screen.getByText('⚠ Connection Error')).toBeInTheDocument();
    expect(screen.getByText('Connection failed')).toBeInTheDocument();
  });
});
```

## Performance Optimization

### 1. Tor Performance Tuning

```typescript
// Tor performance optimization
class TorPerformanceOptimizer {
  private config: TorConfig;

  constructor(config: TorConfig) {
    this.config = config;
  }

  optimizeForPerformance(): void {
    // Optimize Tor configuration for performance
    this.setCircuitBuildTimeout(30); // Faster circuit building
    this.setNewCircuitPeriod(10); // More frequent new circuits
    this.setMaxCircuitDirtiness(300); // Shorter circuit lifetime
    this.enableConnectionPadding();
    this.setEnforceDistinctSubnets(true);
  }

  optimizeForSecurity(): void {
    // Optimize Tor configuration for security
    this.setCircuitBuildTimeout(60); // Slower but more secure
    this.setNewCircuitPeriod(30); // Less frequent new circuits
    this.setMaxCircuitDirtiness(600); // Longer circuit lifetime
    this.enableSafeLogging();
    this.disableDebuggerAttachment();
  }

  private setCircuitBuildTimeout(timeout: number): void {
    this.config.circuitBuildTimeout = timeout;
  }

  private setNewCircuitPeriod(period: number): void {
    this.config.newCircuitPeriod = period;
  }

  private setMaxCircuitDirtiness(dirtiness: number): void {
    this.config.maxCircuitDirtiness = dirtiness;
  }

  private enableConnectionPadding(): void {
    this.config.connectionPadding = true;
  }

  private setEnforceDistinctSubnets(enforce: boolean): void {
    this.config.enforceDistinctSubnets = enforce;
  }

  private enableSafeLogging(): void {
    this.config.safeLogging = true;
  }

  private disableDebuggerAttachment(): void {
    this.config.disableDebuggerAttachment = true;
  }
}
```

### 2. Connection Pool Management

```typescript
// Tor connection pool management
class TorConnectionPool {
  private connections: Map<string, TorConnection> = new Map();
  private maxConnections: number = 10;
  private connectionTimeout: number = 30000;

  async getConnection(endpoint: string): Promise<TorConnection> {
    const connectionKey = this.getConnectionKey(endpoint);
    
    if (this.connections.has(connectionKey)) {
      const connection = this.connections.get(connectionKey)!;
      if (connection.isHealthy()) {
        return connection;
      } else {
        this.connections.delete(connectionKey);
      }
    }

    if (this.connections.size >= this.maxConnections) {
      await this.cleanupStaleConnections();
    }

    const connection = await this.createConnection(endpoint);
    this.connections.set(connectionKey, connection);
    
    return connection;
  }

  private async createConnection(endpoint: string): Promise<TorConnection> {
    const connection = new TorConnection(endpoint, this.connectionTimeout);
    await connection.connect();
    return connection;
  }

  private getConnectionKey(endpoint: string): string {
    return endpoint;
  }

  private async cleanupStaleConnections(): Promise<void> {
    const staleConnections: string[] = [];
    
    for (const [key, connection] of this.connections) {
      if (!connection.isHealthy() || connection.isExpired()) {
        staleConnections.push(key);
      }
    }
    
    for (const key of staleConnections) {
      const connection = this.connections.get(key);
      if (connection) {
        await connection.close();
        this.connections.delete(key);
      }
    }
  }
}

class TorConnection {
  private endpoint: string;
  private timeout: number;
  private createdAt: Date;
  private lastUsed: Date;
  private isConnected: boolean = false;

  constructor(endpoint: string, timeout: number) {
    this.endpoint = endpoint;
    this.timeout = timeout;
    this.createdAt = new Date();
    this.lastUsed = new Date();
  }

  async connect(): Promise<void> {
    // Connect to endpoint through Tor
    this.isConnected = true;
  }

  async close(): Promise<void> {
    // Close connection
    this.isConnected = false;
  }

  isHealthy(): boolean {
    return this.isConnected && !this.isExpired();
  }

  isExpired(): boolean {
    const now = new Date();
    const age = now.getTime() - this.createdAt.getTime();
    return age > this.timeout;
  }

  updateLastUsed(): void {
    this.lastUsed = new Date();
  }
}
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
