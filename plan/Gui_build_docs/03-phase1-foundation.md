# Phase 1: Foundation Setup

## Overview

Phase 1 establishes the core infrastructure for the Electron GUI system, including project structure, Tor integration, Docker management, and shared utilities.

## 1.1 Project Structure Creation

### Directory Structure

Create the following directory structure at the project root:

```
electron-gui/
├── main/                          # Main process code
│   ├── index.ts                   # Electron entry point
│   ├── tor-manager.ts             # Tor daemon management
│   ├── docker-manager.ts          # Docker service management
│   ├── window-manager.ts          # Multi-window coordination
│   ├── ipc-handlers.ts            # IPC event handlers
│   ├── preload-user.js            # User GUI preload script
│   ├── preload-developer.js       # Developer GUI preload script
│   ├── preload-node.js            # Node GUI preload script
│   └── preload-admin.js           # Admin GUI preload script
├── renderer/                      # Renderer processes
│   ├── user/                      # User GUI
│   │   ├── index.html
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   └── styles/
│   ├── developer/                 # Developer GUI
│   │   ├── index.html
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   └── styles/
│   ├── node/                      # Node GUI
│   │   ├── index.html
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   └── styles/
│   └── admin/                     # Admin GUI
│       ├── index.html
│       ├── App.tsx
│       ├── components/
│       ├── hooks/
│       ├── pages/
│       └── styles/
├── shared/                        # Shared utilities
│   ├── api-client.ts              # Tor-proxied API client
│   ├── constants.ts               # API endpoints, ports
│   ├── types.ts                   # TypeScript interfaces
│   └── hooks/
│       └── useAPI.ts              # Standardized API hooks
├── assets/                        # Tor binaries, icons
│   ├── tor/
│   │   ├── tor.exe                # Windows Tor binary
│   │   ├── torrc.template         # Tor configuration
│   │   └── torrc                 # Generated config
│   └── icons/
│       ├── icon.ico               # Windows icon
│       ├── icon.png              # Linux icon
│       └── icon.icns             # macOS icon
├── tests/                         # Test files
│   ├── user-gui.spec.ts
│   ├── developer-gui.spec.ts
│   ├── node-gui.spec.ts
│   └── admin-gui.spec.ts
├── docs/                          # Documentation
│   ├── SYNTAX_GUIDE.md
│   ├── API_ENDPOINTS.md
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_GUIDE.md
│   ├── NODE_OPERATOR_GUIDE.md
│   └── ADMIN_GUIDE.md
├── package.json
├── tsconfig.json
├── tsconfig.main.json
├── webpack.config.js
├── webpack.renderer.config.js
├── electron-builder.json
└── jest.config.js
```

### Core Configuration Files

#### package.json
```json
{
  "name": "lucid-electron-gui",
  "version": "1.0.0",
  "description": "Lucid Desktop GUI - Multi-window Electron application",
  "main": "dist/main/index.js",
  "scripts": {
    "dev": "concurrently \"npm run dev:main\" \"npm run dev:renderer\"",
    "dev:main": "tsc -p tsconfig.main.json && electron .",
    "dev:renderer": "webpack serve --config webpack.renderer.config.js",
    "build": "npm run build:main && npm run build:renderer",
    "build:main": "tsc -p tsconfig.main.json",
    "build:renderer": "webpack --config webpack.renderer.config.js",
    "package": "electron-builder",
    "package:win": "electron-builder --win",
    "package:linux": "electron-builder --linux",
    "package:mac": "electron-builder --mac",
    "test": "jest",
    "test:e2e": "jest --config jest.e2e.config.js"
  },
  "dependencies": {
    "electron": "^28.0.0",
    "tor-control": "^2.0.0",
    "dockerode": "^4.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0",
    "socks-proxy-agent": "^8.0.0",
    "zustand": "^4.4.0",
    "tronweb": "^5.0.0",
    "@ledgerhq/hw-app-tron": "^6.0.0",
    "@trezor/connect": "^9.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@types/node": "^20.0.0",
    "webpack": "^5.88.0",
    "webpack-cli": "^5.1.0",
    "webpack-dev-server": "^4.15.0",
    "ts-loader": "^9.4.0",
    "html-webpack-plugin": "^5.5.0",
    "electron-builder": "^24.6.4",
    "jest": "^29.6.0",
    "spectron": "^19.0.0",
    "concurrently": "^8.2.0"
  }
}
```

#### tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "baseUrl": ".",
    "paths": {
      "@/*": ["shared/*"],
      "@/components/*": ["renderer/*/components/*"],
      "@/hooks/*": ["renderer/*/hooks/*", "shared/hooks/*"],
      "@/types/*": ["shared/types.ts"]
    }
  },
  "include": [
    "shared/**/*",
    "renderer/**/*"
  ],
  "exclude": [
    "node_modules",
    "dist",
    "main"
  ]
}
```

#### tsconfig.main.json
```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "outDir": "dist/main",
    "noEmit": false,
    "jsx": "preserve"
  },
  "include": [
    "main/**/*"
  ],
  "exclude": [
    "node_modules",
    "dist",
    "renderer"
  ]
}
```

## 1.2 Tor Integration Layer

### Tor Manager Implementation

**File**: `main/tor-manager.ts`

```typescript
import { spawn, ChildProcess } from 'child_process';
import { TorControl } from 'tor-control';
import { app } from 'electron';
import path from 'path';
import fs from 'fs';

export interface TorConfig {
  socksPort: number;
  controlPort: number;
  dataDir: string;
  torrcPath: string;
}

export class TorManager {
  private torProcess: ChildProcess | null = null;
  private torControl: TorControl | null = null;
  private readonly torPath: string;
  private readonly dataDir: string;
  private readonly config: TorConfig;
  
  constructor() {
    this.torPath = path.join(__dirname, '..', 'assets', 'tor', 'tor.exe');
    this.dataDir = path.join(app.getPath('userData'), 'tor-data');
    this.config = {
      socksPort: 9050,
      controlPort: 9051,
      dataDir: this.dataDir,
      torrcPath: path.join(this.dataDir, 'torrc')
    };
  }
  
  async start(): Promise<void> {
    try {
      // Ensure data directory exists
      if (!fs.existsSync(this.dataDir)) {
        fs.mkdirSync(this.dataDir, { recursive: true });
      }
      
      // Generate torrc configuration
      await this.generateTorrc();
      
      // Spawn Tor process
      this.torProcess = spawn(this.torPath, [
        '--configfile', this.config.torrcPath,
        '--datadir', this.dataDir
      ]);
      
      // Handle process events
      this.torProcess.on('error', (error) => {
        console.error('Tor process error:', error);
      });
      
      this.torProcess.on('exit', (code) => {
        console.log(`Tor process exited with code ${code}`);
      });
      
      // Wait for Tor to start
      await this.waitForTorStartup();
      
      // Connect to control port
      await this.connectToControl();
      
      console.log('Tor daemon started successfully');
    } catch (error) {
      console.error('Failed to start Tor:', error);
      throw error;
    }
  }
  
  private async generateTorrc(): Promise<void> {
    const torrcContent = `
# Tor configuration for Lucid GUI
SocksPort ${this.config.socksPort}
ControlPort ${this.config.controlPort}
DataDirectory ${this.dataDir}
CookieAuthentication 1
CookieAuthFile ${path.join(this.dataDir, 'control_auth_cookie')}
Log notice file ${path.join(this.dataDir, 'tor.log')}
`.trim();
    
    fs.writeFileSync(this.config.torrcPath, torrcContent);
  }
  
  private async waitForTorStartup(): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Tor startup timeout'));
      }, 30000);
      
      const checkStartup = () => {
        // Check if control port is available
        const net = require('net');
        const socket = net.createConnection(this.config.controlPort, '127.0.0.1');
        
        socket.on('connect', () => {
          clearTimeout(timeout);
          socket.destroy();
          resolve();
        });
        
        socket.on('error', () => {
          setTimeout(checkStartup, 1000);
        });
      };
      
      checkStartup();
    });
  }
  
  private async connectToControl(): Promise<void> {
    this.torControl = new TorControl({
      host: '127.0.0.1',
      port: this.config.controlPort,
      auth: {
        type: 'cookie',
        cookieFile: path.join(this.dataDir, 'control_auth_cookie')
      }
    });
    
    await this.torControl.connect();
  }
  
  async getProxyConfig(): Promise<{ host: string; port: number }> {
    return { 
      host: '127.0.0.1', 
      port: this.config.socksPort 
    };
  }
  
  async maskOnionAddress(url: string): Promise<string> {
    if (url.includes('.onion')) {
      // Replace .onion with localhost for internal routing
      return url.replace(/\.onion/g, '.localhost');
    }
    return url;
  }
  
  async getStatus(): Promise<{ connected: boolean; circuits: number }> {
    if (!this.torControl) {
      return { connected: false, circuits: 0 };
    }
    
    try {
      const circuits = await this.torControl.getCircuits();
      return { connected: true, circuits: circuits.length };
    } catch (error) {
      return { connected: false, circuits: 0 };
    }
  }
  
  async stop(): Promise<void> {
    if (this.torControl) {
      await this.torControl.disconnect();
      this.torControl = null;
    }
    
    if (this.torProcess) {
      this.torProcess.kill('SIGTERM');
      this.torProcess = null;
    }
    
    // Cleanup data directory
    if (fs.existsSync(this.dataDir)) {
      fs.rmSync(this.dataDir, { recursive: true, force: true });
    }
  }
}
```

## 1.3 Docker Service Manager

### Docker Manager Implementation

**File**: `main/docker-manager.ts`

```typescript
import Docker from 'dockerode';
import { EventEmitter } from 'events';
import path from 'path';
import fs from 'fs';
import yaml from 'js-yaml';

export type ServiceLevel = 'admin' | 'developer' | 'user' | 'node';

export interface ServiceStatus {
  name: string;
  status: 'starting' | 'healthy' | 'unhealthy' | 'stopped';
  uptime: number;
  cpu: number;
  memory: number;
  port: number;
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'critical';
  services: ServiceStatus[];
  tor_status: 'connected' | 'disconnected';
  docker_status: 'running' | 'stopped';
}

export class DockerManager extends EventEmitter {
  private docker: Docker;
  private runningServices: Map<string, string> = new Map();
  private readonly projectRoot: string;
  
  constructor() {
    super();
    this.docker = new Docker();
    this.projectRoot = path.join(__dirname, '..', '..', '..');
  }
  
  async checkDockerAvailability(): Promise<boolean> {
    try {
      await this.docker.ping();
      return true;
    } catch (error) {
      console.error('Docker not available:', error);
      return false;
    }
  }
  
  async startLucidStack(level: ServiceLevel): Promise<void> {
    if (level === 'user' || level === 'node') {
      throw new Error('User and Node GUIs cannot start backend services');
    }
    
    const composeFiles = this.getComposeFilesForLevel(level);
    
    for (const composeFile of composeFiles) {
      await this.startComposeFile(composeFile);
    }
    
    this.emit('stack-started', { level, services: Array.from(this.runningServices.keys()) });
  }
  
  private getComposeFilesForLevel(level: ServiceLevel): string[] {
    const basePath = path.join(this.projectRoot, 'configs', 'docker');
    
    if (level === 'admin') {
      return [
        path.join(basePath, 'docker-compose.foundation.yml'),
        path.join(basePath, 'docker-compose.core.yml'),
        path.join(basePath, 'docker-compose.application.yml'),
        path.join(basePath, 'docker-compose.support.yml'),
      ];
    } else if (level === 'developer') {
      return [
        path.join(basePath, 'docker-compose.foundation.yml'),
        path.join(basePath, 'docker-compose.core.yml'),
        path.join(basePath, 'docker-compose.application.yml'),
      ];
    }
    return [];
  }
  
  private async startComposeFile(composePath: string): Promise<void> {
    if (!fs.existsSync(composePath)) {
      throw new Error(`Compose file not found: ${composePath}`);
    }
    
    const composeContent = fs.readFileSync(composePath, 'utf8');
    const compose = yaml.load(composeContent) as any;
    
    for (const [serviceName, serviceConfig] of Object.entries(compose.services)) {
      await this.startService(serviceName, serviceConfig as any);
    }
  }
  
  private async startService(serviceName: string, serviceConfig: any): Promise<void> {
    try {
      const container = await this.docker.createContainer({
        Image: serviceConfig.image,
        name: serviceName,
        Env: serviceConfig.environment || [],
        PortBindings: this.createPortBindings(serviceConfig.ports || []),
        Volumes: this.createVolumeMounts(serviceConfig.volumes || []),
        Cmd: serviceConfig.command || [],
        WorkingDir: serviceConfig.working_dir,
        Healthcheck: serviceConfig.healthcheck
      });
      
      await container.start();
      this.runningServices.set(serviceName, container.id);
      
      this.emit('service-started', { name: serviceName, id: container.id });
    } catch (error) {
      console.error(`Failed to start service ${serviceName}:`, error);
      throw error;
    }
  }
  
  private createPortBindings(ports: string[]): any {
    const bindings: any = {};
    
    for (const port of ports) {
      const [containerPort, hostPort] = port.split(':');
      bindings[`${containerPort}/tcp`] = [{ HostPort: hostPort || containerPort }];
    }
    
    return bindings;
  }
  
  private createVolumeMounts(volumes: string[]): any {
    const mounts: any = {};
    
    for (const volume of volumes) {
      const [hostPath, containerPath] = volume.split(':');
      mounts[containerPath] = {};
    }
    
    return mounts;
  }
  
  async getServiceStatus(serviceName: string): Promise<ServiceStatus> {
    const containerId = this.runningServices.get(serviceName);
    if (!containerId) {
      return {
        name: serviceName,
        status: 'stopped',
        uptime: 0,
        cpu: 0,
        memory: 0,
        port: 0
      };
    }
    
    try {
      const container = this.docker.getContainer(containerId);
      const stats = await container.stats({ stream: false });
      const info = await container.inspect();
      
      return {
        name: serviceName,
        status: info.State.Health?.Status === 'healthy' ? 'healthy' : 'unhealthy',
        uptime: Math.floor((Date.now() - new Date(info.State.StartedAt).getTime()) / 1000),
        cpu: this.calculateCpuUsage(stats),
        memory: this.calculateMemoryUsage(stats),
        port: this.extractPort(info)
      };
    } catch (error) {
      return {
        name: serviceName,
        status: 'stopped',
        uptime: 0,
        cpu: 0,
        memory: 0,
        port: 0
      };
    }
  }
  
  private calculateCpuUsage(stats: any): number {
    const cpuDelta = stats.cpu_stats.cpu_usage.total_usage - stats.precpu_stats.cpu_usage.total_usage;
    const systemDelta = stats.cpu_stats.system_cpu_usage - stats.precpu_stats.system_cpu_usage;
    const cpuPercent = (cpuDelta / systemDelta) * 100;
    return Math.round(cpuPercent * 100) / 100;
  }
  
  private calculateMemoryUsage(stats: any): number {
    const memoryUsage = stats.memory_stats.usage;
    const memoryLimit = stats.memory_stats.limit;
    return Math.round((memoryUsage / memoryLimit) * 100 * 100) / 100;
  }
  
  private extractPort(info: any): number {
    const ports = info.NetworkSettings?.Ports;
    if (ports) {
      for (const [containerPort, hostBindings] of Object.entries(ports)) {
        if (hostBindings && Array.isArray(hostBindings) && hostBindings.length > 0) {
          return parseInt(hostBindings[0].HostPort);
        }
      }
    }
    return 0;
  }
  
  async stopAllServices(): Promise<void> {
    for (const [serviceName, containerId] of this.runningServices) {
      try {
        const container = this.docker.getContainer(containerId);
        await container.stop();
        await container.remove();
        this.emit('service-stopped', { name: serviceName, id: containerId });
      } catch (error) {
        console.error(`Failed to stop service ${serviceName}:`, error);
      }
    }
    
    this.runningServices.clear();
    this.emit('all-services-stopped');
  }
  
  async getSystemHealth(): Promise<SystemHealth> {
    const services: ServiceStatus[] = [];
    
    for (const serviceName of this.runningServices.keys()) {
      const status = await this.getServiceStatus(serviceName);
      services.push(status);
    }
    
    const healthyServices = services.filter(s => s.status === 'healthy').length;
    const totalServices = services.length;
    
    let overall: 'healthy' | 'degraded' | 'critical';
    if (totalServices === 0) {
      overall = 'critical';
    } else if (healthyServices === totalServices) {
      overall = 'healthy';
    } else if (healthyServices > totalServices / 2) {
      overall = 'degraded';
    } else {
      overall = 'critical';
    }
    
    return {
      overall,
      services,
      tor_status: 'connected', // This would be checked separately
      docker_status: await this.checkDockerAvailability() ? 'running' : 'stopped'
    };
  }
}
```

## 1.4 Window Manager

### Window Manager Implementation

**File**: `main/window-manager.ts`

```typescript
import { BrowserWindow, ipcMain } from 'electron';
import path from 'path';

export interface WindowConfig {
  name: string;
  title: string;
  width: number;
  height: number;
  preload: string;
  level: 'admin' | 'developer' | 'user' | 'node';
  resizable: boolean;
  minimizable: boolean;
  maximizable: boolean;
  closable: boolean;
  show: boolean;
}

export class WindowManager {
  private windows: Map<string, BrowserWindow> = new Map();
  private readonly configs: WindowConfig[] = [
    {
      name: 'user',
      title: 'Lucid User Interface',
      width: 1200,
      height: 800,
      preload: path.join(__dirname, 'preload-user.js'),
      level: 'user',
      resizable: true,
      minimizable: true,
      maximizable: true,
      closable: true,
      show: false
    },
    {
      name: 'developer',
      title: 'Lucid Developer Console',
      width: 1400,
      height: 900,
      preload: path.join(__dirname, 'preload-developer.js'),
      level: 'developer',
      resizable: true,
      minimizable: true,
      maximizable: true,
      closable: true,
      show: false
    },
    {
      name: 'node',
      title: 'Lucid Node Operator',
      width: 1200,
      height: 800,
      preload: path.join(__dirname, 'preload-node.js'),
      level: 'node',
      resizable: true,
      minimizable: true,
      maximizable: true,
      closable: true,
      show: false
    },
    {
      name: 'admin',
      title: 'Lucid System Administration',
      width: 1600,
      height: 1000,
      preload: path.join(__dirname, 'preload-admin.js'),
      level: 'admin',
      resizable: true,
      minimizable: true,
      maximizable: true,
      closable: true,
      show: false
    },
  ];
  
  createWindow(name: string): BrowserWindow {
    const config = this.configs.find(c => c.name === name);
    if (!config) {
      throw new Error(`Unknown window: ${name}`);
    }
    
    const win = new BrowserWindow({
      width: config.width,
      height: config.height,
      title: config.title,
      resizable: config.resizable,
      minimizable: config.minimizable,
      maximizable: config.maximizable,
      closable: config.closable,
      show: config.show,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: config.preload,
        webSecurity: true,
        allowRunningInsecureContent: false,
        experimentalFeatures: false
      },
      icon: path.join(__dirname, '..', 'assets', 'icons', 'icon.png')
    });
    
    // Load renderer HTML for this window
    const htmlPath = path.join(__dirname, '..', 'renderer', name, 'index.html');
    win.loadFile(htmlPath);
    
    // Show window when ready
    win.once('ready-to-show', () => {
      win.show();
    });
    
    // Handle window closed
    win.on('closed', () => {
      this.windows.delete(name);
    });
    
    // Handle window close (prevent default if needed)
    win.on('close', (event) => {
      // Add any cleanup logic here
      // event.preventDefault() to prevent closing
    });
    
    this.windows.set(name, win);
    return win;
  }
  
  getWindow(name: string): BrowserWindow | undefined {
    return this.windows.get(name);
  }
  
  getAllWindows(): BrowserWindow[] {
    return Array.from(this.windows.values());
  }
  
  showWindow(name: string): void {
    const win = this.windows.get(name);
    if (win) {
      win.show();
      win.focus();
    }
  }
  
  hideWindow(name: string): void {
    const win = this.windows.get(name);
    if (win) {
      win.hide();
    }
  }
  
  closeWindow(name: string): void {
    const win = this.windows.get(name);
    if (win) {
      win.close();
    }
  }
  
  closeAllWindows(): void {
    for (const win of this.windows.values()) {
      win.close();
    }
  }
  
  getWindowCount(): number {
    return this.windows.size;
  }
  
  isWindowOpen(name: string): boolean {
    return this.windows.has(name) && !this.windows.get(name)?.isDestroyed();
  }
}
```

## 1.5 Shared API Client

### API Client Implementation

**File**: `shared/api-client.ts`

```typescript
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { SocksProxyAgent } from 'socks-proxy-agent';

export interface LucidError {
  code: string;
  message: string;
  details?: any;
}

export class LucidAPIClient {
  private client: AxiosInstance;
  private torProxy: string = 'socks5://127.0.0.1:9050';
  private baseURL: string;
  
  constructor(baseURL: string) {
    this.baseURL = baseURL;
    const agent = new SocksProxyAgent(this.torProxy);
    
    this.client = axios.create({
      baseURL,
      httpAgent: agent,
      httpsAgent: agent,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Lucid-Electron-GUI/1.0.0'
      },
    });
    
    this.setupInterceptors();
  }
  
  private setupInterceptors(): void {
    // Request interceptor for auth tokens
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getAuthToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );
    
    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => this.handleAPIError(error)
    );
  }
  
  private getAuthToken(): string | null {
    // Get token from secure storage or session
    return localStorage.getItem('lucid_auth_token');
  }
  
  private handleAPIError(error: any): Promise<never> {
    if (error.response) {
      const { status, data } = error.response;
      const lucidError: LucidError = {
        code: data.code || `HTTP_${status}`,
        message: data.message || error.message,
        details: data.details
      };
      return Promise.reject(lucidError);
    } else if (error.request) {
      const lucidError: LucidError = {
        code: 'NETWORK_ERROR',
        message: 'Network request failed',
        details: { originalError: error.message }
      };
      return Promise.reject(lucidError);
    } else {
      const lucidError: LucidError = {
        code: 'UNKNOWN_ERROR',
        message: error.message,
        details: { originalError: error }
      };
      return Promise.reject(lucidError);
    }
  }
  
  // Generic HTTP methods
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }
  
  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }
  
  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }
  
  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }
  
  // Session Management API
  async createSession(data: any): Promise<any> {
    return this.post('/api/v1/sessions', data);
  }
  
  async getUserSessions(userId: string): Promise<any[]> {
    return this.get(`/api/v1/sessions?user_id=${userId}`);
  }
  
  async getSession(sessionId: string): Promise<any> {
    return this.get(`/api/v1/sessions/${sessionId}`);
  }
  
  // Chunk Management API
  async uploadChunk(sessionId: string, chunk: any): Promise<any> {
    return this.post(`/api/v1/sessions/${sessionId}/chunks`, chunk);
  }
  
  async downloadChunk(chunkId: string): Promise<any> {
    return this.get(`/api/v1/chunks/${chunkId}`);
  }
  
  // Proof Verification API
  async verifySessionProof(sessionId: string): Promise<any> {
    return this.post(`/api/v1/sessions/${sessionId}/verify`);
  }
  
  async getMerkleProof(chunkId: string): Promise<any> {
    return this.get(`/api/v1/chunks/${chunkId}/proof`);
  }
  
  // User Management API
  async getUserProfile(userId: string): Promise<any> {
    return this.get(`/api/v1/users/${userId}`);
  }
  
  async updateUserProfile(userId: string, data: any): Promise<any> {
    return this.put(`/api/v1/users/${userId}`, data);
  }
  
  // Node Management API
  async registerNode(nodeData: any): Promise<any> {
    return this.post('/api/v1/nodes/register', nodeData);
  }
  
  async getNodeStatus(nodeId: string): Promise<any> {
    return this.get(`/api/v1/nodes/${nodeId}/status`);
  }
  
  async joinPool(nodeId: string, poolId: string): Promise<any> {
    return this.post(`/api/v1/nodes/${nodeId}/pool`, { poolId });
  }
  
  async getPootScore(nodeId: string): Promise<any> {
    return this.get(`/api/v1/nodes/${nodeId}/poot`);
  }
  
  // Admin API
  async getSystemHealth(): Promise<any> {
    return this.get('/api/v1/admin/system/health');
  }
  
  async getServiceStatus(serviceName: string): Promise<any> {
    return this.get(`/api/v1/admin/services/${serviceName}/status`);
  }
  
  // TRON Payment API
  async getPayoutHistory(nodeId: string): Promise<any[]> {
    return this.get(`/api/v1/payouts?node_id=${nodeId}`);
  }
  
  async requestPayout(nodeId: string, amount: number): Promise<any> {
    return this.post('/api/v1/payouts', { nodeId, amount });
  }
}
```

## 1.6 Shared Types

### TypeScript Interfaces

**File**: `shared/types.ts`

```typescript
// User types (from API Gateway - Cluster 01)
export interface User {
  user_id: string;
  email: string;
  tron_address: string;
  hardware_wallet?: HardwareWallet;
  role: 'user' | 'node_operator' | 'admin' | 'super_admin';
  created_at: string;
  updated_at: string;
}

export interface HardwareWallet {
  type: 'ledger' | 'trezor' | 'keepkey';
  address: string;
  public_key: string;
  connected: boolean;
}

// Session types (from Session Management - Cluster 03)
export interface Session {
  session_id: string;
  user_id: string;
  status: 'active' | 'completed' | 'failed' | 'anchored';
  chunks: Chunk[];
  merkle_root?: string;
  blockchain_anchor?: BlockchainAnchor;
  created_at: string;
  updated_at: string;
}

export interface Chunk {
  chunk_id: string;
  session_id: string;
  sequence: number;
  hash: string;
  size: number;
  encrypted: boolean;
  compressed: boolean;
  created_at: string;
}

export interface BlockchainAnchor {
  transaction_hash: string;
  block_height: number;
  block_hash: string;
  timestamp: string;
}

// Node types (from Node Management - Cluster 05)
export interface Node {
  node_id: string;
  operator_id: string;
  status: 'registered' | 'active' | 'inactive' | 'suspended';
  pool_id?: string;
  poot_score: number;
  resources: NodeResources;
  created_at: string;
  updated_at: string;
}

export interface NodeResources {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_bandwidth: number;
}

export interface Pool {
  pool_id: string;
  name: string;
  description: string;
  min_poot_score: number;
  max_nodes: number;
  current_nodes: number;
  status: 'active' | 'inactive' | 'full';
}

// Blockchain types (from Blockchain Core - Cluster 02)
export interface Block {
  block_id: string;
  height: number;
  previous_hash: string;
  merkle_root: string;
  transactions: Transaction[];
  timestamp: string;
  consensus_votes?: ConsensusVote[];
}

export interface Transaction {
  transaction_id: string;
  type: 'session_anchor' | 'payout' | 'governance';
  data: any;
  timestamp: string;
  block_height: number;
}

export interface ConsensusVote {
  node_id: string;
  vote: 'approve' | 'reject';
  timestamp: string;
}

// Admin types
export interface ServiceStatus {
  name: string;
  status: 'starting' | 'healthy' | 'unhealthy' | 'stopped';
  uptime: number;
  cpu: number;
  memory: number;
  port: number;
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'critical';
  services: ServiceStatus[];
  tor_status: 'connected' | 'disconnected';
  docker_status: 'running' | 'stopped';
}

// TRON Payment types (from TRON Payment - Cluster 07)
export interface Payout {
  payout_id: string;
  node_id: string;
  amount_usdt: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  transaction_hash?: string;
  created_at: string;
  completed_at?: string;
}

// API Response types
export interface APIResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  code?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

// Error types
export interface LucidError {
  code: string;
  message: string;
  details?: any;
}

// Configuration types
export interface AppConfig {
  api_endpoints: {
    gateway: string;
    blockchain: string;
    auth: string;
    sessions: string;
    nodes: string;
    admin: string;
    tron_payment: string;
  };
  tor_config: {
    socks_port: number;
    control_port: number;
  };
  gui_config: {
    theme: 'light' | 'dark';
    language: string;
    auto_update: boolean;
  };
}
```

## 1.7 Constants and Configuration

### API Endpoints Configuration

**File**: `shared/constants.ts`

```typescript
export const API_ENDPOINTS = {
  GATEWAY: 'http://localhost:8080',
  BLOCKCHAIN: 'http://localhost:8084',
  AUTH: 'http://localhost:8089',
  SESSIONS: 'http://localhost:8087',
  NODES: 'http://localhost:8095',
  ADMIN: 'http://localhost:8083',
  TRON_PAYMENT: 'http://localhost:8085',
} as const;

export const TOR_CONFIG = {
  SOCKS_PORT: 9050,
  CONTROL_PORT: 9051,
  DATA_DIR: 'tor-data',
} as const;

export const GUI_CONFIG = {
  WINDOW_SIZES: {
    USER: { width: 1200, height: 800 },
    DEVELOPER: { width: 1400, height: 900 },
    NODE: { width: 1200, height: 800 },
    ADMIN: { width: 1600, height: 1000 },
  },
  THEMES: ['light', 'dark'] as const,
  LANGUAGES: ['en', 'es', 'fr', 'de'] as const,
} as const;

export const ERROR_CODES = {
  // Authentication errors
  AUTH_FAILED: 'LUCID_ERR_2001',
  TOKEN_EXPIRED: 'LUCID_ERR_2002',
  INVALID_SIGNATURE: 'LUCID_ERR_2003',
  
  // Rate limiting
  RATE_LIMIT_EXCEEDED: 'LUCID_ERR_3001',
  
  // Session errors
  SESSION_NOT_FOUND: 'LUCID_ERR_4001',
  SESSION_EXPIRED: 'LUCID_ERR_4002',
  CHUNK_UPLOAD_FAILED: 'LUCID_ERR_4003',
  
  // Node errors
  NODE_NOT_REGISTERED: 'LUCID_ERR_5001',
  POOL_FULL: 'LUCID_ERR_5002',
  INSUFFICIENT_POOT: 'LUCID_ERR_5003',
  
  // System errors
  SERVICE_UNAVAILABLE: 'LUCID_ERR_6001',
  TOR_CONNECTION_FAILED: 'LUCID_ERR_6002',
  DOCKER_NOT_AVAILABLE: 'LUCID_ERR_6003',
} as const;

export const SERVICE_LEVELS = {
  ADMIN: ['foundation', 'core', 'application', 'support'],
  DEVELOPER: ['foundation', 'core', 'application'],
  USER: [],
  NODE: [],
} as const;
```

## Implementation Checklist

### Phase 1 Completion Criteria

- [ ] Project structure created with all directories
- [ ] Package.json with all dependencies configured
- [ ] TypeScript configuration files created
- [ ] Tor manager implemented with daemon management
- [ ] Docker manager implemented with service orchestration
- [ ] Window manager implemented with multi-window support
- [ ] Shared API client implemented with Tor proxy
- [ ] TypeScript interfaces defined for all data types
- [ ] Constants and configuration files created
- [ ] Basic error handling implemented
- [ ] Security patterns established (context isolation, IPC)

### Testing Requirements

- [ ] Tor daemon starts and connects successfully
- [ ] Docker services can be started/stopped
- [ ] All four windows can be created
- [ ] API client routes through Tor proxy
- [ ] Error handling works correctly
- [ ] TypeScript compilation succeeds
- [ ] No security vulnerabilities in IPC communication

### Security Verification

- [ ] Context isolation enabled in all renderers
- [ ] No nodeIntegration in any renderer
- [ ] All IPC communication via preload scripts
- [ ] Tor proxy enforced for all external communication
- [ ] No plaintext .onion addresses in logs
- [ ] Secure storage for authentication tokens
