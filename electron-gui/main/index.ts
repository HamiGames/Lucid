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
    // Tor status handlers
    ipcMain.handle(IPCChannels.TOR_GET_STATUS, () => {
      return this.torManager.getStatus();
    });

    ipcMain.handle(IPCChannels.TOR_START, async () => {
      return await this.torManager.start();
    });

    ipcMain.handle(IPCChannels.TOR_STOP, async () => {
      return await this.torManager.stop();
    });

    // Window management handlers
    ipcMain.handle(IPCChannels.WINDOW_CREATE, async (event, windowType: string, options: any) => {
      return await this.windowManager.createWindow(windowType, options);
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

    // Docker service handlers
    ipcMain.handle(IPCChannels.DOCKER_GET_CONTAINERS, async () => {
      return await this.dockerService.getContainers();
    });

    ipcMain.handle(IPCChannels.DOCKER_START_CONTAINER, async (event, containerId: string) => {
      return await this.dockerService.startContainer(containerId);
    });

    ipcMain.handle(IPCChannels.DOCKER_STOP_CONTAINER, async (event, containerId: string) => {
      return await this.dockerService.stopContainer(containerId);
    });

    ipcMain.handle(IPCChannels.DOCKER_GET_LOGS, async (event, containerId: string, lines: number = 100) => {
      return await this.dockerService.getContainerLogs(containerId, lines);
    });

    // API proxy handlers
    ipcMain.handle(IPCChannels.API_REQUEST, async (event, request: any) => {
      return await this.handleApiRequest(request);
    });

    // Hardware wallet handlers
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
