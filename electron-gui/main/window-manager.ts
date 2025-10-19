// main/window-manager.ts - Manages 4 separate BrowserWindows
// Based on the electron-multi-gui-development.plan.md specifications

import { BrowserWindow, screen, app, Menu, shell } from 'electron';
import { join } from 'path';
import { WINDOW_CONFIGS } from '../shared/constants';
import { isDevelopment } from '../shared/utils';

export interface WindowInfo {
  window: BrowserWindow;
  name: string;
  title: string;
  level: 'user' | 'developer' | 'node' | 'admin';
  isVisible: boolean;
  isFocused: boolean;
}

export class WindowManager {
  private windows: Map<string, WindowInfo> = new Map();
  private mainWindow: BrowserWindow | null = null;

  constructor() {
    this.setupMenu();
  }

  async createWindow(windowName: keyof typeof WINDOW_CONFIGS): Promise<BrowserWindow> {
    const config = WINDOW_CONFIGS[windowName];
    
    if (this.windows.has(windowName)) {
      const existingWindow = this.windows.get(windowName)!;
      if (!existingWindow.window.isDestroyed()) {
        existingWindow.window.focus();
        return existingWindow.window;
      }
    }

    // Calculate window position (cascade windows)
    const { x, y } = this.calculateWindowPosition(windowName);

    // Create the window
    const window = new BrowserWindow({
      width: config.width,
      height: config.height,
      x,
      y,
      title: config.title,
      show: false, // Don't show until ready
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        enableRemoteModule: false,
        preload: join(__dirname, 'preload.js'),
        webSecurity: !isDevelopment(),
        allowRunningInsecureContent: isDevelopment(),
      },
      icon: join(__dirname, '../../assets/icons/icon.png'),
      titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
      frame: true,
      resizable: true,
      minimizable: true,
      maximizable: true,
      closable: true,
      focusable: true,
      alwaysOnTop: false,
      fullscreenable: true,
      skipTaskbar: false,
      autoHideMenuBar: !isDevelopment(),
    });

    // Load the appropriate HTML file
    const htmlPath = join(__dirname, `../../renderer/${windowName}/${windowName}.html`);
    await window.loadFile(htmlPath);

    // Show window when ready
    window.once('ready-to-show', () => {
      window.show();
      if (isDevelopment()) {
        window.webContents.openDevTools();
      }
    });

    // Store window info
    const windowInfo: WindowInfo = {
      window,
      name: windowName,
      title: config.title,
      level: config.level,
      isVisible: true,
      isFocused: false,
    };

    this.windows.set(windowName, windowInfo);

    // Set as main window if it's the first one
    if (!this.mainWindow) {
      this.mainWindow = window;
    }

    // Setup window event handlers
    this.setupWindowEventHandlers(window, windowName);

    console.log(`Created ${windowName} window`);
    return window;
  }

  private calculateWindowPosition(windowName: keyof typeof WINDOW_CONFIGS): { x: number; y: number } {
    const screenSize = screen.getPrimaryDisplay().workAreaSize;
    const windowConfig = WINDOW_CONFIGS[windowName];
    
    // Calculate cascade offset
    const offset = 30;
    const windowIndex = Object.keys(WINDOW_CONFIGS).indexOf(windowName);
    
    return {
      x: Math.min(offset * windowIndex, screenSize.width - windowConfig.width),
      y: Math.min(offset * windowIndex, screenSize.height - windowConfig.height),
    };
  }

  private setupWindowEventHandlers(window: BrowserWindow, windowName: string): void {
    // Handle window closed
    window.on('closed', () => {
      this.windows.delete(windowName);
      if (this.mainWindow === window) {
        this.mainWindow = null;
      }
      console.log(`${windowName} window closed`);
    });

    // Handle window focus
    window.on('focus', () => {
      const windowInfo = this.windows.get(windowName);
      if (windowInfo) {
        windowInfo.isFocused = true;
        // Update other windows' focus state
        this.windows.forEach((info, name) => {
          if (name !== windowName) {
            info.isFocused = false;
          }
        });
      }
    });

    // Handle window blur
    window.on('blur', () => {
      const windowInfo = this.windows.get(windowName);
      if (windowInfo) {
        windowInfo.isFocused = false;
      }
    });

    // Handle window show
    window.on('show', () => {
      const windowInfo = this.windows.get(windowName);
      if (windowInfo) {
        windowInfo.isVisible = true;
      }
    });

    // Handle window hide
    window.on('hide', () => {
      const windowInfo = this.windows.get(windowName);
      if (windowInfo) {
        windowInfo.isVisible = false;
      }
    });

    // Handle window maximize
    window.on('maximize', () => {
      console.log(`${windowName} window maximized`);
    });

    // Handle window unmaximize
    window.on('unmaximize', () => {
      console.log(`${windowName} window unmaximized`);
    });

    // Handle window minimize
    window.on('minimize', () => {
      console.log(`${windowName} window minimized`);
    });

    // Handle window restore
    window.on('restore', () => {
      console.log(`${windowName} window restored`);
    });

    // Handle external links
    window.webContents.setWindowOpenHandler(({ url }) => {
      shell.openExternal(url);
      return { action: 'deny' };
    });

    // Handle navigation
    window.webContents.on('will-navigate', (event, navigationUrl) => {
      const parsedUrl = new URL(navigationUrl);
      
      // Prevent navigation to external URLs
      if (parsedUrl.origin !== 'file://') {
        event.preventDefault();
        shell.openExternal(navigationUrl);
      }
    });

    // Handle new window
    window.webContents.on('new-window', (event, navigationUrl) => {
      event.preventDefault();
      shell.openExternal(navigationUrl);
    });
  }

  private setupMenu(): void {
    if (process.platform === 'darwin') {
      const template: Electron.MenuItemConstructorOptions[] = [
        {
          label: 'Lucid',
          submenu: [
            { role: 'about' },
            { type: 'separator' },
            { role: 'services' },
            { type: 'separator' },
            { role: 'hide' },
            { role: 'hideothers' },
            { role: 'unhide' },
            { type: 'separator' },
            { role: 'quit' },
          ],
        },
        {
          label: 'Edit',
          submenu: [
            { role: 'undo' },
            { role: 'redo' },
            { type: 'separator' },
            { role: 'cut' },
            { role: 'copy' },
            { role: 'paste' },
            { role: 'selectall' },
          ],
        },
        {
          label: 'View',
          submenu: [
            { role: 'reload' },
            { role: 'forceReload' },
            { role: 'toggleDevTools' },
            { type: 'separator' },
            { role: 'resetZoom' },
            { role: 'zoomIn' },
            { role: 'zoomOut' },
            { type: 'separator' },
            { role: 'togglefullscreen' },
          ],
        },
        {
          label: 'Window',
          submenu: [
            { role: 'minimize' },
            { role: 'close' },
            { type: 'separator' },
            { role: 'front' },
          ],
        },
      ];

      const menu = Menu.buildFromTemplate(template);
      Menu.setApplicationMenu(menu);
    }
  }

  // Window control methods
  getWindow(windowName: string): BrowserWindow | null {
    const windowInfo = this.windows.get(windowName);
    return windowInfo && !windowInfo.window.isDestroyed() ? windowInfo.window : null;
  }

  getAllWindows(): BrowserWindow[] {
    return Array.from(this.windows.values())
      .filter(info => !info.window.isDestroyed())
      .map(info => info.window);
  }

  getWindowInfo(windowName: string): WindowInfo | null {
    const windowInfo = this.windows.get(windowName);
    return windowInfo && !windowInfo.window.isDestroyed() ? windowInfo : null;
  }

  getAllWindowInfo(): WindowInfo[] {
    return Array.from(this.windows.values())
      .filter(info => !info.window.isDestroyed());
  }

  // Window operations
  showWindow(windowName: string): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.show();
      window.focus();
      return true;
    }
    return false;
  }

  hideWindow(windowName: string): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.hide();
      return true;
    }
    return false;
  }

  minimizeWindow(windowName: string): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.minimize();
      return true;
    }
    return false;
  }

  maximizeWindow(windowName: string): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.maximize();
      return true;
    }
    return false;
  }

  restoreWindow(windowName: string): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.restore();
      return true;
    }
    return false;
  }

  closeWindow(windowName: string): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.close();
      return true;
    }
    return false;
  }

  closeAllWindows(): void {
    this.windows.forEach((info, windowName) => {
      if (!info.window.isDestroyed()) {
        info.window.close();
      }
    });
    this.windows.clear();
  }

  // Window positioning
  setWindowPosition(windowName: string, x: number, y: number): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.setPosition(x, y);
      return true;
    }
    return false;
  }

  setWindowSize(windowName: string, width: number, height: number): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.setSize(width, height);
      return true;
    }
    return false;
  }

  centerWindow(windowName: string): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.center();
      return true;
    }
    return false;
  }

  // Window state
  isWindowVisible(windowName: string): boolean {
    const windowInfo = this.windows.get(windowName);
    return windowInfo ? windowInfo.isVisible : false;
  }

  isWindowFocused(windowName: string): boolean {
    const windowInfo = this.windows.get(windowName);
    return windowInfo ? windowInfo.isFocused : false;
  }

  getFocusedWindow(): BrowserWindow | null {
    for (const [windowName, windowInfo] of this.windows) {
      if (windowInfo.isFocused && !windowInfo.window.isDestroyed()) {
        return windowInfo.window;
      }
    }
    return null;
  }

  // Window communication
  sendToWindow(windowName: string, channel: string, data: any): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.webContents.send(channel, data);
      return true;
    }
    return false;
  }

  broadcastToAllWindows(channel: string, data: any): void {
    this.windows.forEach((info, windowName) => {
      this.sendToWindow(windowName, channel, data);
    });
  }

  // Window management
  focusWindow(windowName: string): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.focus();
      return true;
    }
    return false;
  }

  bringWindowToFront(windowName: string): boolean {
    const window = this.getWindow(windowName);
    if (window) {
      window.moveTop();
      window.focus();
      return true;
    }
    return false;
  }

  // Cleanup
  destroy(): void {
    this.closeAllWindows();
    this.windows.clear();
    this.mainWindow = null;
  }
}
