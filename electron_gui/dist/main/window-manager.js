"use strict";
/**
 * LUCID Window Manager - SPEC-1B Implementation
 * Manages multiple GUI windows (User, Developer, Node, Admin)
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.WindowManager = void 0;
const electron_1 = require("electron");
const path = __importStar(require("path"));
const tor_manager_1 = require("./tor-manager");
class WindowManager {
    constructor() {
        this.windows = new Map();
        this.torManager = new tor_manager_1.TorManager();
    }
    async createWindow(windowType, options = {}) {
        try {
            console.log(`Creating ${windowType} window...`);
            // Generate unique window ID
            const windowId = `${windowType}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            // Get default options for window type
            const defaultOptions = this.getDefaultOptions(windowType);
            const finalOptions = { ...defaultOptions, ...options };
            // Create browser window
            const window = new electron_1.BrowserWindow({
                width: finalOptions.width || 1200,
                height: finalOptions.height || 800,
                x: finalOptions.x,
                y: finalOptions.y,
                webPreferences: {
                    nodeIntegration: false,
                    contextIsolation: true,
                    preload: path.join(__dirname, 'preload.js'),
                    webSecurity: true,
                    allowRunningInsecureContent: false
                },
                icon: finalOptions.icon || path.join(__dirname, `../assets/icons/${windowType}-icon.png`),
                title: finalOptions.title || `Lucid ${this.capitalize(windowType)} GUI`,
                show: finalOptions.show !== false,
                frame: true,
                resizable: finalOptions.resizable !== false,
                minimizable: finalOptions.minimizable !== false,
                maximizable: finalOptions.maximizable !== false,
                closable: true,
                alwaysOnTop: finalOptions.alwaysOnTop || false,
                fullscreen: finalOptions.fullscreen || false,
                backgroundColor: '#1a1a1a', // Dark theme
                titleBarStyle: 'default'
            });
            // Load window content
            await this.loadWindowContent(window, windowType);
            // Setup window event handlers
            this.setupWindowEventHandlers(window, windowId, windowType);
            // Create GUI window object
            const guiWindow = {
                id: windowId,
                type: windowType,
                window,
                options: finalOptions,
                createdAt: new Date(),
                lastActivity: new Date()
            };
            // Store window
            this.windows.set(windowId, guiWindow);
            console.log(`${windowType} window created with ID: ${windowId}`);
            return windowId;
        }
        catch (error) {
            console.error(`Failed to create ${windowType} window:`, error);
            throw error;
        }
    }
    async closeWindow(windowId) {
        try {
            const guiWindow = this.windows.get(windowId);
            if (!guiWindow) {
                console.warn(`Window ${windowId} not found`);
                return false;
            }
            console.log(`Closing window ${windowId}...`);
            // Close the window
            guiWindow.window.close();
            // Remove from tracking
            this.windows.delete(windowId);
            console.log(`Window ${windowId} closed successfully`);
            return true;
        }
        catch (error) {
            console.error(`Failed to close window ${windowId}:`, error);
            return false;
        }
    }
    async minimizeWindow(windowId) {
        try {
            const guiWindow = this.windows.get(windowId);
            if (!guiWindow) {
                console.warn(`Window ${windowId} not found`);
                return false;
            }
            guiWindow.window.minimize();
            guiWindow.lastActivity = new Date();
            return true;
        }
        catch (error) {
            console.error(`Failed to minimize window ${windowId}:`, error);
            return false;
        }
    }
    async maximizeWindow(windowId) {
        try {
            const guiWindow = this.windows.get(windowId);
            if (!guiWindow) {
                console.warn(`Window ${windowId} not found`);
                return false;
            }
            if (guiWindow.window.isMaximized()) {
                guiWindow.window.unmaximize();
            }
            else {
                guiWindow.window.maximize();
            }
            guiWindow.lastActivity = new Date();
            return true;
        }
        catch (error) {
            console.error(`Failed to maximize window ${windowId}:`, error);
            return false;
        }
    }
    async restoreWindow(windowId) {
        try {
            const guiWindow = this.windows.get(windowId);
            if (!guiWindow) {
                console.warn(`Window ${windowId} not found`);
                return false;
            }
            guiWindow.window.restore();
            guiWindow.lastActivity = new Date();
            return true;
        }
        catch (error) {
            console.error(`Failed to restore window ${windowId}:`, error);
            return false;
        }
    }
    async focusWindow(windowId) {
        try {
            const guiWindow = this.windows.get(windowId);
            if (!guiWindow) {
                console.warn(`Window ${windowId} not found`);
                return false;
            }
            guiWindow.window.focus();
            guiWindow.lastActivity = new Date();
            return true;
        }
        catch (error) {
            console.error(`Failed to focus window ${windowId}:`, error);
            return false;
        }
    }
    getWindow(windowId) {
        return this.windows.get(windowId);
    }
    broadcastToAllWindows(channel, data) {
        for (const gui of this.windows.values()) {
            if (!gui.window.isDestroyed()) {
                gui.window.webContents.send(channel, data);
            }
        }
    }
    getAllWindows() {
        return Array.from(this.windows.values());
    }
    getWindowsByType(type) {
        return Array.from(this.windows.values()).filter(window => window.type === type);
    }
    getWindowCount() {
        return this.windows.size;
    }
    getWindowCountByType() {
        const counts = {
            user: 0,
            developer: 0,
            node: 0,
            admin: 0
        };
        this.windows.forEach(window => {
            counts[window.type]++;
        });
        return counts;
    }
    getDefaultOptions(windowType) {
        const { width, height } = electron_1.screen.getPrimaryDisplay().workAreaSize;
        const defaultOptions = {
            user: {
                width: Math.min(1000, width),
                height: Math.min(700, height),
                title: 'Lucid User GUI',
                resizable: true,
                minimizable: true,
                maximizable: true
            },
            developer: {
                width: Math.min(1400, width),
                height: Math.min(900, height),
                title: 'Lucid Developer Console',
                resizable: true,
                minimizable: true,
                maximizable: true
            },
            node: {
                width: Math.min(1200, width),
                height: Math.min(800, height),
                title: 'Lucid Node Operator',
                resizable: true,
                minimizable: true,
                maximizable: true
            },
            admin: {
                width: Math.min(1600, width),
                height: Math.min(1000, height),
                title: 'Lucid System Admin',
                resizable: true,
                minimizable: true,
                maximizable: true,
                alwaysOnTop: false
            }
        };
        return defaultOptions[windowType] || defaultOptions.user;
    }
    async loadWindowContent(window, windowType) {
        const isDev = process.env.NODE_ENV === 'development';
        const htmlFile = `${windowType}.html`;
        if (isDev) {
            // Development mode - load from local server
            await window.loadURL(`http://localhost:3000/${htmlFile}`);
            window.webContents.openDevTools();
        }
        else {
            // Production mode - load from file
            await window.loadFile(path.join(__dirname, `../renderer/${windowType}/${htmlFile}`));
        }
    }
    setupWindowEventHandlers(window, windowId, windowType) {
        // Window ready to show
        window.once('ready-to-show', () => {
            const guiWindow = this.windows.get(windowId);
            if (guiWindow) {
                guiWindow.lastActivity = new Date();
            }
        });
        // Window closed
        window.on('closed', () => {
            console.log(`Window ${windowId} closed`);
            this.windows.delete(windowId);
        });
        // Window focus
        window.on('focus', () => {
            const guiWindow = this.windows.get(windowId);
            if (guiWindow) {
                guiWindow.lastActivity = new Date();
            }
        });
        // Window blur
        window.on('blur', () => {
            // Update last activity
            const guiWindow = this.windows.get(windowId);
            if (guiWindow) {
                guiWindow.lastActivity = new Date();
            }
        });
        // Window resize
        window.on('resize', () => {
            const guiWindow = this.windows.get(windowId);
            if (guiWindow) {
                guiWindow.lastActivity = new Date();
            }
        });
        // Window move
        window.on('move', () => {
            const guiWindow = this.windows.get(windowId);
            if (guiWindow) {
                guiWindow.lastActivity = new Date();
            }
        });
        // Prevent navigation to external URLs
        window.webContents.on('will-navigate', (event, navigationUrl) => {
            const parsedUrl = new URL(navigationUrl);
            if (parsedUrl.origin !== window.webContents.getURL()) {
                event.preventDefault();
                console.warn(`Blocked navigation to external URL: ${navigationUrl}`);
            }
        });
        // Handle new window requests
        window.webContents.setWindowOpenHandler(({ url }) => {
            console.warn(`Blocked new window request to: ${url}`);
            return { action: 'deny' };
        });
        // Handle certificate errors (for .onion addresses)
        window.webContents.on('certificate-error', (event, url, error, certificate, callback) => {
            if (url.includes('.onion')) {
                // Allow .onion addresses (self-signed certificates)
                event.preventDefault();
                callback(true);
            }
            else {
                // Reject other certificate errors
                callback(false);
            }
        });
        // Handle console messages
        window.webContents.on('console-message', (event, level, message, line, sourceId) => {
            console.log(`[${windowType.toUpperCase()}] ${message}`);
        });
        // Handle unresponsive window
        window.on('unresponsive', () => {
            console.warn(`Window ${windowId} became unresponsive`);
        });
        window.on('responsive', () => {
            console.log(`Window ${windowId} became responsive again`);
        });
        // Handle crashed window
        window.webContents.on('crashed', (event, killed) => {
            console.error(`Window ${windowId} crashed (killed: ${killed})`);
            // Show crash dialog
            electron_1.dialog.showErrorBox('Window Crashed', `The ${windowType} window has crashed. The application will attempt to recover.`);
        });
    }
    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    // Utility methods for window management
    async cascadeWindows() {
        const windows = this.getAllWindows();
        if (windows.length <= 1)
            return;
        const { width, height } = electron_1.screen.getPrimaryDisplay().workAreaSize;
        const offset = 30;
        let x = 50;
        let y = 50;
        for (const guiWindow of windows) {
            const windowBounds = guiWindow.window.getBounds();
            guiWindow.window.setBounds({
                x: Math.min(x, width - windowBounds.width),
                y: Math.min(y, height - windowBounds.height),
                width: windowBounds.width,
                height: windowBounds.height
            });
            x += offset;
            y += offset;
        }
    }
    async tileWindows() {
        const windows = this.getAllWindows();
        if (windows.length <= 1)
            return;
        const { width, height } = electron_1.screen.getPrimaryDisplay().workAreaSize;
        const cols = Math.ceil(Math.sqrt(windows.length));
        const rows = Math.ceil(windows.length / cols);
        const windowWidth = Math.floor(width / cols);
        const windowHeight = Math.floor(height / rows);
        windows.forEach((guiWindow, index) => {
            const col = index % cols;
            const row = Math.floor(index / cols);
            guiWindow.window.setBounds({
                x: col * windowWidth,
                y: row * windowHeight,
                width: windowWidth,
                height: windowHeight
            });
        });
    }
    async minimizeAllWindows() {
        const promises = Array.from(this.windows.keys()).map(windowId => this.minimizeWindow(windowId));
        await Promise.all(promises);
    }
    async restoreAllWindows() {
        const promises = Array.from(this.windows.keys()).map(windowId => this.restoreWindow(windowId));
        await Promise.all(promises);
    }
    async closeAllWindows() {
        const promises = Array.from(this.windows.keys()).map(windowId => this.closeWindow(windowId));
        await Promise.all(promises);
    }
    getWindowStatistics() {
        const windows = this.getAllWindows();
        const now = new Date();
        return {
            totalWindows: windows.length,
            windowsByType: this.getWindowCountByType(),
            activeWindows: windows.filter(w => !w.window.isMinimized()).length,
            averageUptime: windows.reduce((sum, w) => sum + (now.getTime() - w.createdAt.getTime()), 0) / windows.length,
            oldestWindow: windows.reduce((oldest, w) => w.createdAt < oldest.createdAt ? w : oldest, windows[0])?.createdAt,
            newestWindow: windows.reduce((newest, w) => w.createdAt > newest.createdAt ? w : newest, windows[0])?.createdAt
        };
    }
}
exports.WindowManager = WindowManager;
