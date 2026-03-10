#!/usr/bin/env node
/**
 * LUCID Electron GUI Main Process - SPEC-1B Implementation
 * Multi-window Electron application with 4 distinct GUI frames
 */

import { app, BrowserWindow, ipcMain, screen, shell } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { TorManager } from './tor-manager';
import { WindowManager } from './window-manager';
import { DockerService } from './docker-service';
import { IPCChannels } from '../shared/ipc-channels';

// Configure logging
const isDev = process.env.NODE_ENV === 'development';

class LucidElectronApp {
  private mainWindow: BrowserWindow | null = null;
  private windows: Map<string, BrowserWindow> = new Map();
  private torManager: TorManager;
  private windowManager: WindowManager;
  private dockerService: DockerService;
  private isQuitting = false;

  constructor() {
    this.torManager = new TorManager();
    this.windowManager = new WindowManager();
    this.dockerService = new DockerService();
  }

  async initialize(): Promise<void> {
    try {
      console.log('Initializing Lucid Electron App...');

      // Initialize application services
      const { appInitialization } = await import('../shared/app-initialization');
      await appInitialization.initialize();

      // Initialize Tor manager
      await this.torManager.initialize();

      // Initialize Docker service
      await this.dockerService.initialize();

      // Setup IPC handlers
      this.setupIpcHandlers();

      // Setup app event handlers
      this.setupAppEventHandlers();

      console.log('Lucid Electron App initialized successfully');

    } catch (error) {
      console.error('Failed to initialize Lucid Electron App:', error);
      throw error;
    }
  }

  private setupIpcHandlers(): void {
    // =====================================================================
    // TOR Handlers
    // =====================================================================
    ipcMain.handle(IPCChannels.TOR_GET_STATUS, () => {
      return this.torManager.getStatus();
    });

    ipcMain.handle(IPCChannels.TOR_START, async () => {
      return await this.torManager.start();
    });

    ipcMain.handle(IPCChannels.TOR_STOP, async () => {
      return await this.torManager.stop();
    });

    ipcMain.handle(IPCChannels.TOR_RESTART, async () => {
      await this.torManager.stop();
      return await this.torManager.start();
    });

    ipcMain.handle(IPCChannels.TOR_GET_METRICS, () => {
      return this.torManager.getMetrics?.() || { uptimeSeconds: 0, bytesRead: 0, bytesWritten: 0 };
    });

    ipcMain.handle(IPCChannels.TOR_TEST_CONNECTION, async (event, { url }) => {
      return await this.torManager.testConnection?.(url) || { success: false };
    });

    ipcMain.handle(IPCChannels.TOR_HEALTH_CHECK, async () => {
      return await this.torManager.healthCheck?.() || { healthy: false };
    });

    // =====================================================================
    // Window Management Handlers
    // =====================================================================
    ipcMain.handle(IPCChannels.WINDOW_CREATE, async (event, { type, options }) => {
      return await this.windowManager.createWindow(type, options);
    });

    ipcMain.handle(IPCChannels.WINDOW_CLOSE, async (event, windowId: string) => {
      return await this.windowManager.closeWindow(windowId);
    });

    ipcMain.handle(IPCChannels.WINDOW_MINIMIZE, async (event, windowId: string) => {
      return await this.windowManager.minimizeWindow(windowId);
    });

    ipcMain.handle(IPCChannels.WINDOW_MAXIMIZE, async (event, windowId: string) => {
      return await this.windowManager.maximizeWindow(windowId);
    });

    ipcMain.handle(IPCChannels.WINDOW_RESTORE, async (event, windowId: string) => {
      return await this.windowManager.restoreWindow?.(windowId) || { success: false };
    });

    ipcMain.handle(IPCChannels.WINDOW_GET_LIST, async () => {
      return Array.from(this.windows.values()).map((w, idx) => ({
        id: idx.toString(),
        title: w.webContents.getTitle(),
        focused: w.isFocused(),
      }));
    });

    ipcMain.handle(IPCChannels.WINDOW_GET_STATISTICS, async () => {
      return {
        total_windows: this.windows.size,
        focused_window: this.mainWindow?.isFocused() ? 'main' : null,
        timestamp: new Date().toISOString(),
      };
    });

    // =====================================================================
    // Docker Service Handlers
    // =====================================================================
    ipcMain.handle(IPCChannels.DOCKER_GET_STATUS, async () => {
      return this.dockerService.getStatus();
    });

    ipcMain.handle(IPCChannels.DOCKER_CONNECT_SSH, async (event, config: any) => {
      return await this.dockerService.connectSSH(config);
    });

    ipcMain.handle(IPCChannels.DOCKER_DISCONNECT, async () => {
      await this.dockerService.cleanup();
      return { success: true };
    });

    ipcMain.handle(IPCChannels.DOCKER_GET_CONTAINERS, async () => {
      return await this.dockerService.getContainers();
    });

    ipcMain.handle(IPCChannels.DOCKER_GET_CONTAINER, async (event, containerId: string) => {
      return await this.dockerService.getContainer(containerId);
    });

    ipcMain.handle(IPCChannels.DOCKER_START_CONTAINER, async (event, containerId: string) => {
      return await this.dockerService.startContainer(containerId);
    });

    ipcMain.handle(IPCChannels.DOCKER_STOP_CONTAINER, async (event, containerId: string) => {
      return await this.dockerService.stopContainer(containerId);
    });

    ipcMain.handle(IPCChannels.DOCKER_RESTART_CONTAINER, async (event, containerId: string) => {
      return await this.dockerService.restartContainer(containerId);
    });

    ipcMain.handle(IPCChannels.DOCKER_REMOVE_CONTAINER, async (event, { id, force }) => {
      return await this.dockerService.removeContainer(id, force);
    });

    ipcMain.handle(IPCChannels.DOCKER_GET_LOGS, async (event, { id, lines }) => {
      return await this.dockerService.getContainerLogs(id, lines || 100);
    });

    ipcMain.handle(IPCChannels.DOCKER_GET_STATS, async (event, containerId: string) => {
      return await this.dockerService.getContainerStats(containerId);
    });

    ipcMain.handle(IPCChannels.DOCKER_GET_ALL_STATS, async () => {
      return await this.dockerService.getAllContainerStats();
    });

    ipcMain.handle(IPCChannels.DOCKER_PULL_IMAGE, async (event, imageName: string) => {
      return await this.dockerService.pullImage(imageName);
    });

    ipcMain.handle(IPCChannels.DOCKER_GET_IMAGES, async () => {
      return await this.dockerService.getImages();
    });

    // =====================================================================
    // API Proxy Handlers
    // =====================================================================
    ipcMain.handle(IPCChannels.API_REQUEST, async (event, request: any) => {
      return await this.handleApiRequest(request);
    });

    ipcMain.handle(IPCChannels.API_GET, async (event, { url, config }) => {
      return await this.handleApiRequest({ method: 'GET', url, ...config });
    });

    ipcMain.handle(IPCChannels.API_POST, async (event, { url, data, config }) => {
      return await this.handleApiRequest({ method: 'POST', url, data, ...config });
    });

    ipcMain.handle(IPCChannels.API_PUT, async (event, { url, data, config }) => {
      return await this.handleApiRequest({ method: 'PUT', url, data, ...config });
    });

    ipcMain.handle(IPCChannels.API_DELETE, async (event, { url, config }) => {
      return await this.handleApiRequest({ method: 'DELETE', url, ...config });
    });

    // =====================================================================
    // Configuration Handlers
    // =====================================================================
    ipcMain.handle(IPCChannels.CONFIG_GET, async (event, key?: string) => {
      return this.getConfig(key);
    });

    ipcMain.handle(IPCChannels.CONFIG_SET, async (event, { key, value }) => {
      return this.setConfig(key, value);
    });

    ipcMain.handle(IPCChannels.CONFIG_RESET, async (event, key?: string) => {
      return this.resetConfig(key);
    });

    ipcMain.handle(IPCChannels.CONFIG_EXPORT, async () => {
      return this.exportConfig();
    });

    ipcMain.handle(IPCChannels.CONFIG_IMPORT, async (event, data: any) => {
      return this.importConfig(data);
    });

    // =====================================================================
    // File Handlers
    // =====================================================================
    ipcMain.handle(IPCChannels.FILE_OPEN, async (event, options: any) => {
      const { dialog } = require('electron');
      return await dialog.showOpenDialog(this.mainWindow || {}, options);
    });

    ipcMain.handle(IPCChannels.FILE_SAVE, async (event, options: any) => {
      const { dialog } = require('electron');
      return await dialog.showSaveDialog(this.mainWindow || {}, options);
    });

    // =====================================================================
    // System Info Handlers
    // =====================================================================
    ipcMain.handle(IPCChannels.SYSTEM_GET_INFO, () => {
      return {
        platform: process.platform,
        arch: process.arch,
        nodeVersion: process.version,
        electronVersion: process.versions.electron,
      };
    });

    ipcMain.handle(IPCChannels.SYSTEM_GET_RESOURCES, () => {
      const { cpuUsage } = process;
      return {
        cpu: cpuUsage(),
        memory: process.memoryUsage(),
      };
    });

    ipcMain.handle(IPCChannels.SYSTEM_GET_NETWORK_INFO, async () => {
      const os = require('os');
      return {
        interfaces: os.networkInterfaces(),
        hostname: os.hostname(),
      };
    });

    ipcMain.handle(IPCChannels.SYSTEM_SHOW_NOTIFICATION, (event, { title, body }) => {
      const { Notification } = require('electron');
      new Notification({ title, body }).show();
      return { success: true };
    });

    ipcMain.handle(IPCChannels.SYSTEM_OPEN_EXTERNAL, (event, url: string) => {
      shell.openExternal(url);
      return { success: true };
    });

    // =====================================================================
    // Logging Handlers
    // =====================================================================
    ipcMain.on(IPCChannels.LOG_INFO, (event, { message, context }) => {
      console.log(`[INFO] ${message}`, context);
    });

    ipcMain.on(IPCChannels.LOG_WARN, (event, { message, context }) => {
      console.warn(`[WARN] ${message}`, context);
    });

    ipcMain.on(IPCChannels.LOG_ERROR, (event, { message, context }) => {
      console.error(`[ERROR] ${message}`, context);
    });

    ipcMain.on(IPCChannels.LOG_DEBUG, (event, { message, context }) => {
      if (process.env.DEBUG) {
        console.debug(`[DEBUG] ${message}`, context);
      }
    });

    // =====================================================================
    // Authentication Handlers
    // =====================================================================
    ipcMain.handle(IPCChannels.AUTH_LOGIN, async (event, { email, signature }) => {
      return await this.handleAuthLogin(email, signature);
    });

    ipcMain.handle(IPCChannels.AUTH_LOGOUT, async () => {
      return await this.handleAuthLogout();
    });

    ipcMain.handle(IPCChannels.AUTH_VERIFY_TOKEN, async (event, { token }) => {
      return await this.verifyAuthToken(token);
    });

    ipcMain.handle(IPCChannels.AUTH_REFRESH_TOKEN, async () => {
      return await this.refreshAuthToken();
    });

    // =====================================================================
    // Update Handlers
    // =====================================================================
    ipcMain.handle(IPCChannels.UPDATE_CHECK, async () => {
      return { available: false };
    });

    ipcMain.handle(IPCChannels.UPDATE_DOWNLOAD, async () => {
      return { success: false };
    });

    ipcMain.handle(IPCChannels.UPDATE_INSTALL, async () => {
      return { success: false };
    });

    ipcMain.handle(IPCChannels.UPDATE_RESTART, async () => {
      app.quit();
      return { success: true };
    });

    // =====================================================================
    // Hardware Wallet Handlers (Legacy)
    // =====================================================================
    ipcMain.handle(IPCChannels.HARDWARE_WALLET_CONNECT, async (event, walletType: string) => {
      return await this.connectHardwareWallet(walletType);
    });

    ipcMain.handle(IPCChannels.HARDWARE_WALLET_SIGN, async (event, data: any) => {
      return await this.signWithHardwareWallet(data);
    });
  }

  private setupAppEventHandlers(): void {
    // App ready event
    app.whenReady().then(async () => {
      try {
        await this.initialize();
        await this.createMainWindow();
        await this.torManager.start();
      } catch (error) {
        console.error('Failed to start application:', error);
        app.quit();
      }
    });

    // App window-all-closed event
    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        this.isQuitting = true;
        app.quit();
      }
    });

    // App activate event (macOS)
    app.on('activate', async () => {
      if (this.windows.size === 0) {
        await this.createMainWindow();
      }
    });

    // App before-quit event
    app.on('before-quit', async (event) => {
      if (!this.isQuitting) {
        event.preventDefault();
        await this.cleanup();
        this.isQuitting = true;
        app.quit();
      }
    });
  }

  private async createMainWindow(): Promise<void> {
    try {
      const { width, height } = screen.getPrimaryDisplay().workAreaSize;

      this.mainWindow = new BrowserWindow({
        width: Math.min(1200, width),
        height: Math.min(800, height),
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true,
          enableRemoteModule: false,
          preload: path.join(__dirname, 'preload.js'),
          webSecurity: true,
          allowRunningInsecureContent: false
        },
        icon: path.join(__dirname, '../assets/icons/lucid-icon.png'),
        title: 'Lucid - Multi-GUI Launcher',
        show: false,
        frame: true,
        resizable: true,
        minimizable: true,
        maximizable: true,
        closable: true
      });

      // Load main window content
      if (isDev) {
        await this.mainWindow.loadURL('http://localhost:3000/main.html');
        this.mainWindow.webContents.openDevTools();
      } else {
        await this.mainWindow.loadFile(path.join(__dirname, '../renderer/main/main.html'));
      }

      // Show window when ready
      this.mainWindow.once('ready-to-show', () => {
        if (this.mainWindow) {
          this.mainWindow.show();
        }
      });

      // Handle window closed
      this.mainWindow.on('closed', () => {
        this.mainWindow = null;
      });

      // Handle external links
      this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
      });

      console.log('Main window created successfully');

    } catch (error) {
      console.error('Failed to create main window:', error);
      throw error;
    }
  }

  private async handleApiRequest(request: any): Promise<any> {
    try {
      // Proxy API requests through Tor if available
      const torStatus = this.torManager.getStatus();
      
      if (torStatus.connected) {
        // Route through Tor SOCKS proxy
        return await this.makeTorRequest(request);
      } else {
        // Direct request (development only)
        if (isDev) {
          return await this.makeDirectRequest(request);
        } else {
          throw new Error('Tor connection required for API requests');
        }
      }

    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  private async makeTorRequest(request: any): Promise<any> {
    // Implement Tor SOCKS proxy request
    // This would use a SOCKS proxy library to route requests through Tor
    console.log('Making Tor request:', request.url);
    
    // Placeholder implementation
    return {
      success: true,
      data: { message: 'Tor request placeholder' },
      timestamp: new Date().toISOString()
    };
  }

  private async makeDirectRequest(request: any): Promise<any> {
    // Implement direct HTTP request for development
    console.log('Making direct request:', request.url);
    
    // Placeholder implementation
    return {
      success: true,
      data: { message: 'Direct request placeholder' },
      timestamp: new Date().toISOString()
    };
  }

  private async connectHardwareWallet(walletType: string): Promise<any> {
    try {
      console.log(`Connecting to ${walletType} hardware wallet...`);
      
      // Implement hardware wallet connection based on type
      switch (walletType.toLowerCase()) {
        case 'ledger':
          return await this.connectLedgerWallet();
        case 'trezor':
          return await this.connectTrezorWallet();
        case 'keepkey':
          return await this.connectKeepKeyWallet();
        default:
          throw new Error(`Unsupported wallet type: ${walletType}`);
      }

    } catch (error) {
      console.error('Hardware wallet connection failed:', error);
      throw error;
    }
  }

  private async connectLedgerWallet(): Promise<any> {
    // Implement Ledger wallet connection
    return {
      success: true,
      walletType: 'ledger',
      address: 'ledger_address_placeholder',
      connected: true
    };
  }

  private async connectTrezorWallet(): Promise<any> {
    // Implement Trezor wallet connection
    return {
      success: true,
      walletType: 'trezor',
      address: 'trezor_address_placeholder',
      connected: true
    };
  }

  private async connectKeepKeyWallet(): Promise<any> {
    // Implement KeepKey wallet connection
    return {
      success: true,
      walletType: 'keepkey',
      address: 'keepkey_address_placeholder',
      connected: true
    };
  }

  private async signWithHardwareWallet(data: any): Promise<any> {
    try {
      console.log('Signing data with hardware wallet...');
      
      // Implement hardware wallet signing
      return {
        success: true,
        signature: 'hardware_wallet_signature_placeholder',
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      console.error('Hardware wallet signing failed:', error);
      throw error;
    }
  }

  private async cleanup(): Promise<void> {
    try {
      console.log('Cleaning up Lucid Electron App...');

      // Stop Tor manager
      await this.torManager.stop();

      // Close all windows
      this.windows.forEach((window, windowId) => {
        if (!window.isDestroyed()) {
          window.close();
        }
      });
      this.windows.clear();

      // Close main window
      if (this.mainWindow && !this.mainWindow.isDestroyed()) {
        this.mainWindow.close();
        this.mainWindow = null;
      }

      // Cleanup Docker service
      await this.dockerService.cleanup();

      console.log('Lucid Electron App cleanup completed');

    } catch (error) {
      console.error('Failed to cleanup Lucid Electron App:', error);
    }
  }

  // =====================================================================
  // Configuration Management
  // =====================================================================

  private config: Map<string, any> = new Map();

  private getConfig(key?: string): any {
    if (key) {
      return this.config.get(key);
    }
    return Object.fromEntries(this.config);
  }

  private setConfig(key: string, value: any): { success: boolean } {
    this.config.set(key, value);
    
    // Broadcast config update to all windows
    this.windows.forEach((window) => {
      window.webContents.send(IPCChannels.CONFIG_UPDATED, {
        key,
        value,
        scope: 'system',
        updatedAt: new Date().toISOString(),
      });
    });

    return { success: true };
  }

  private resetConfig(key?: string): { success: boolean } {
    if (key) {
      this.config.delete(key);
    } else {
      this.config.clear();
    }
    return { success: true };
  }

  private exportConfig(): any {
    return {
      config: Object.fromEntries(this.config),
      exportedAt: new Date().toISOString(),
    };
  }

  private importConfig(data: any): { success: boolean } {
    try {
      if (data.config && typeof data.config === 'object') {
        Object.entries(data.config).forEach(([key, value]) => {
          this.config.set(key, value);
        });
      }
      return { success: true };
    } catch (error) {
      console.error('Failed to import config:', error);
      return { success: false };
    }
  }

  // =====================================================================
  // Authentication Management
  // =====================================================================

  private authToken: string | null = null;
  private authTokenExpiry: Date | null = null;
  private tokenRefreshTimer: NodeJS.Timeout | null = null;

  private async handleAuthLogin(email: string, signature: string): Promise<any> {
    try {
      // TODO: Implement actual authentication with backend
      console.log(`Auth login attempt for: ${email}`);
      
      this.authToken = `token_${Date.now()}`;
      this.authTokenExpiry = new Date(Date.now() + 3600000); // 1 hour

      this.scheduleTokenRefresh();

      // Broadcast auth status change
      this.broadcastAuthStatusChange(true, { email, role: 'admin' });

      return {
        success: true,
        token: this.authToken,
        expiresAt: this.authTokenExpiry.toISOString(),
      };
    } catch (error) {
      console.error('Authentication failed:', error);
      return { success: false, error: 'Authentication failed' };
    }
  }

  private async handleAuthLogout(): Promise<{ success: boolean }> {
    this.authToken = null;
    this.authTokenExpiry = null;

    if (this.tokenRefreshTimer) {
      clearTimeout(this.tokenRefreshTimer);
      this.tokenRefreshTimer = null;
    }

    this.broadcastAuthStatusChange(false);
    return { success: true };
  }

  private async verifyAuthToken(token: string): Promise<any> {
    if (this.authToken === token && this.authTokenExpiry && new Date() < this.authTokenExpiry) {
      return {
        valid: true,
        user: { id: 'admin-1', email: 'admin@lucid.io', role: 'admin' },
        expiresAt: this.authTokenExpiry.toISOString(),
      };
    }
    return { valid: false };
  }

  private async refreshAuthToken(): Promise<any> {
    try {
      // TODO: Implement actual token refresh
      this.authTokenExpiry = new Date(Date.now() + 3600000); // Extend by 1 hour
      this.scheduleTokenRefresh();
      return { success: true, expiresAt: this.authTokenExpiry.toISOString() };
    } catch (error) {
      console.error('Token refresh failed:', error);
      return { success: false };
    }
  }

  private scheduleTokenRefresh(): void {
    if (this.tokenRefreshTimer) {
      clearTimeout(this.tokenRefreshTimer);
    }

    // Refresh token 5 minutes before expiry
    const refreshTime = this.authTokenExpiry ? this.authTokenExpiry.getTime() - Date.now() - 300000 : 0;
    
    if (refreshTime > 0) {
      this.tokenRefreshTimer = setTimeout(() => {
        this.refreshAuthToken();
      }, refreshTime);
    }
  }

  private broadcastAuthStatusChange(authenticated: boolean, user?: any): void {
    this.windows.forEach((window) => {
      window.webContents.send(IPCChannels.AUTH_STATUS_CHANGED, {
        authenticated,
        user,
        timestamp: new Date().toISOString(),
      });
    });
  }

  // =====================================================================
  // API Request Handling
  // =====================================================================

  private async makeDirectRequest(request: any): Promise<any> {
    // Implement direct HTTP request for development
    console.log('Making direct request:', request.url);
    
    // Placeholder implementation
    return {
      success: true,
      data: { message: 'Direct request placeholder' },
      timestamp: new Date().toISOString()
    };
  }

  // =====================================================================
  // Hardware Wallet Management (Legacy)
  // =====================================================================

  private async connectLedgerWallet(): Promise<any> {
    // Implement Ledger wallet connection
    return {
      success: true,
      walletType: 'ledger',
      address: 'ledger_address_placeholder',
      connected: true
    };
  }

  private async connectTrezorWallet(): Promise<any> {
    // Implement Trezor wallet connection
    return {
      success: true,
      walletType: 'trezor',
      address: 'trezor_address_placeholder',
      connected: true
    };
  }

  private async connectKeepKeyWallet(): Promise<any> {
    // Implement KeepKey wallet connection
    return {
      success: true,
      walletType: 'keepkey',
      address: 'keepkey_address_placeholder',
      connected: true
    };
  }

  // Public methods for window management
  async createGUIWindow(guiType: 'user' | 'developer' | 'node' | 'admin', options: any = {}): Promise<string> {
    return await this.windowManager.createWindow(guiType, options);
  }

  async closeGUIWindow(windowId: string): Promise<void> {
    await this.windowManager.closeWindow(windowId);
  }

  getTorStatus(): any {
    return this.torManager.getStatus();
  }

  getDockerStatus(): any {
    return this.dockerService.getStatus();
  }
}

// Create and export app instance
const lucidApp = new LucidElectronApp();

// Export for testing
export { LucidElectronApp };

// Start the application
if (require.main === module) {
  lucidApp.initialize().catch((error) => {
    console.error('Failed to start Lucid Electron App:', error);
    process.exit(1);
  });
}
