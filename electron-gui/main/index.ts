// main/index.ts - Main entry point with window initialization
// Based on the electron-multi-gui-development.plan.md specifications

import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron';
import { join } from 'path';
import { WindowManager } from './window-manager';
import { TorManager } from './tor-manager';
import { DockerService } from './docker-service';
import { setupIpcHandlers } from './ipc-handlers';
import { TOR_CONFIG, WINDOW_CONFIGS } from '../shared/constants';
import { isDevelopment } from '../shared/utils';

class LucidElectronApp {
  private windowManager: WindowManager;
  private torManager: TorManager;
  private dockerService: DockerService;
  private isQuitting: boolean = false;

  constructor() {
    this.windowManager = new WindowManager();
    this.torManager = new TorManager();
    this.dockerService = new DockerService();
  }

  async initialize(): Promise<void> {
    try {
      console.log('Initializing Lucid Electron Application...');

      // Setup IPC handlers
      setupIpcHandlers(this.windowManager, this.torManager, this.dockerService);

      // Initialize Tor connection
      await this.initializeTor();

      // Initialize Docker services
      await this.initializeDocker();

      // Create windows
      await this.createWindows();

      // Setup app event handlers
      this.setupAppEventHandlers();

      console.log('Lucid Electron Application initialized successfully');
    } catch (error) {
      console.error('Failed to initialize Lucid Electron Application:', error);
      app.quit();
    }
  }

  private async initializeTor(): Promise<void> {
    try {
      console.log('Initializing Tor connection...');
      await this.torManager.start();
      console.log('Tor connection initialized');
    } catch (error) {
      console.error('Failed to initialize Tor:', error);
      // Continue without Tor for development
      if (isDevelopment()) {
        console.warn('Continuing without Tor in development mode');
      } else {
        throw error;
      }
    }
  }

  private async initializeDocker(): Promise<void> {
    try {
      console.log('Initializing Docker services...');
      await this.dockerService.initialize();
      console.log('Docker services initialized');
    } catch (error) {
      console.error('Failed to initialize Docker services:', error);
      // Continue without Docker for development
      if (isDevelopment()) {
        console.warn('Continuing without Docker in development mode');
      } else {
        throw error;
      }
    }
  }

  private async createWindows(): Promise<void> {
    try {
      console.log('Creating application windows...');

      // Create all windows based on configuration
      for (const [windowName, config] of Object.entries(WINDOW_CONFIGS)) {
        await this.windowManager.createWindow(windowName as keyof typeof WINDOW_CONFIGS);
      }

      console.log('All windows created successfully');
    } catch (error) {
      console.error('Failed to create windows:', error);
      throw error;
    }
  }

  private setupAppEventHandlers(): void {
    // Handle window-all-closed
    app.on('window-all-closed', () => {
      // On macOS, keep app running even when all windows are closed
      if (process.platform !== 'darwin') {
        app.quit();
      }
    });

    // Handle activate (macOS)
    app.on('activate', async () => {
      // Recreate windows if none exist (macOS)
      const windows = BrowserWindow.getAllWindows();
      if (windows.length === 0) {
        await this.createWindows();
      }
    });

    // Handle before-quit
    app.on('before-quit', async (event) => {
      if (!this.isQuitting) {
        event.preventDefault();
        await this.cleanup();
        this.isQuitting = true;
        app.quit();
      }
    });

    // Handle second-instance
    app.on('second-instance', async () => {
      // Focus existing windows when trying to open second instance
      const windows = BrowserWindow.getAllWindows();
      windows.forEach(window => {
        if (window.isMinimized()) window.restore();
        window.focus();
      });
    });

    // Handle certificate errors (for development)
    app.on('certificate-error', (event, webContents, url, error, certificate, callback) => {
      if (isDevelopment()) {
        // Ignore certificate errors in development
        event.preventDefault();
        callback(true);
      } else {
        callback(false);
      }
    });

    // Handle protocol handlers
    app.setAsDefaultProtocolClient('lucid');
    app.on('open-url', (event, url) => {
      event.preventDefault();
      this.handleProtocolUrl(url);
    });

    // Handle file associations
    app.on('open-file', (event, path) => {
      event.preventDefault();
      this.handleFileOpen(path);
    });
  }

  private async cleanup(): Promise<void> {
    try {
      console.log('Cleaning up application resources...');

      // Stop Tor
      await this.torManager.stop();

      // Stop Docker services
      await this.dockerService.stop();

      // Close all windows
      this.windowManager.closeAllWindows();

      console.log('Application cleanup completed');
    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }

  private handleProtocolUrl(url: string): void {
    console.log('Handling protocol URL:', url);
    // Parse URL and route to appropriate window
    // Implementation depends on specific protocol requirements
  }

  private handleFileOpen(path: string): void {
    console.log('Handling file open:', path);
    // Handle file opening logic
    // Implementation depends on file type requirements
  }
}

// Initialize the application
const lucidApp = new LucidElectronApp();

// Handle app ready
app.whenReady().then(async () => {
  try {
    await lucidApp.initialize();
  } catch (error) {
    console.error('Application initialization failed:', error);
    app.quit();
  }
});

// Handle app window-all-closed
app.on('window-all-closed', () => {
  // On macOS, keep app running even when all windows are closed
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Handle app activate (macOS)
app.on('activate', async () => {
  // Recreate windows if none exist (macOS)
  const windows = BrowserWindow.getAllWindows();
  if (windows.length === 0) {
    try {
      await lucidApp.initialize();
    } catch (error) {
      console.error('Failed to recreate windows:', error);
    }
  }
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  app.quit();
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  app.quit();
});

export default lucidApp;
