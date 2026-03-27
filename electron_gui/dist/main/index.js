#!/usr/bin/env node
"use strict";
/**
 * LUCID Electron GUI Main Process - SPEC-1B Implementation
 * Multi-window Electron application with 4 distinct GUI frames
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
exports.LucidElectronApp = void 0;
const electron_1 = require("electron");
const path = __importStar(require("path"));
const tor_manager_1 = require("./tor-manager");
const window_manager_1 = require("./window-manager");
const docker_service_1 = require("./docker-service");
const ipc_channels_1 = require("../shared/ipc-channels");
// Configure logging
const isDev = process.env.NODE_ENV === 'development';
class LucidElectronApp {
    constructor() {
        this.mainWindow = null;
        this.windows = new Map();
        this.isQuitting = false;
        // =====================================================================
        // Configuration Management
        // =====================================================================
        this.config = new Map();
        // =====================================================================
        // Authentication Management
        // =====================================================================
        this.authToken = null;
        this.authTokenExpiry = null;
        this.tokenRefreshTimer = null;
        this.torManager = new tor_manager_1.TorManager();
        this.windowManager = new window_manager_1.WindowManager();
        this.dockerService = new docker_service_1.DockerService();
    }
    async initialize() {
        try {
            console.log('Initializing Lucid Electron App...');
            // Initialize application services
            const { appInitialization } = await Promise.resolve().then(() => __importStar(require('../shared/app-initialization')));
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
        }
        catch (error) {
            console.error('Failed to initialize Lucid Electron App:', error);
            throw error;
        }
    }
    setupIpcHandlers() {
        // =====================================================================
        // TOR Handlers
        // =====================================================================
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.TOR_GET_STATUS, () => {
            return this.torManager.getStatus();
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.TOR_START, async () => {
            return await this.torManager.start();
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.TOR_STOP, async () => {
            return await this.torManager.stop();
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.TOR_RESTART, async () => {
            await this.torManager.stop();
            return await this.torManager.start();
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.TOR_GET_METRICS, () => {
            return this.torManager.getMetrics?.() || { uptimeSeconds: 0, bytesRead: 0, bytesWritten: 0 };
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.TOR_TEST_CONNECTION, async (event, { url }) => {
            return await this.torManager.testConnection?.(url) || { success: false };
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.TOR_HEALTH_CHECK, async () => {
            return await this.torManager.healthCheck?.() || { healthy: false };
        });
        // =====================================================================
        // Window Management Handlers
        // =====================================================================
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.WINDOW_CREATE, async (event, { type, options }) => {
            return await this.windowManager.createWindow(type, options);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.WINDOW_CLOSE, async (event, windowId) => {
            return await this.windowManager.closeWindow(windowId);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.WINDOW_MINIMIZE, async (event, windowId) => {
            return await this.windowManager.minimizeWindow(windowId);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.WINDOW_MAXIMIZE, async (event, windowId) => {
            return await this.windowManager.maximizeWindow(windowId);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.WINDOW_RESTORE, async (event, windowId) => {
            return await this.windowManager.restoreWindow?.(windowId) || { success: false };
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.WINDOW_GET_LIST, async () => {
            return Array.from(this.windows.values()).map((w, idx) => ({
                id: idx.toString(),
                title: w.webContents.getTitle(),
                focused: w.isFocused(),
            }));
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.WINDOW_GET_STATISTICS, async () => {
            return {
                total_windows: this.windows.size,
                focused_window: this.mainWindow?.isFocused() ? 'main' : null,
                timestamp: new Date().toISOString(),
            };
        });
        // =====================================================================
        // Docker Service Handlers
        // =====================================================================
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_GET_STATUS, async () => {
            return this.dockerService.getStatus();
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_CONNECT_SSH, async (event, config) => {
            return await this.dockerService.connectSSH(config);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_DISCONNECT, async () => {
            await this.dockerService.cleanup();
            return { success: true };
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_GET_CONTAINERS, async () => {
            return await this.dockerService.getContainers();
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_GET_CONTAINER, async (event, containerId) => {
            return await this.dockerService.getContainer(containerId);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_START_CONTAINER, async (event, containerId) => {
            return await this.dockerService.startContainer(containerId);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_STOP_CONTAINER, async (event, containerId) => {
            return await this.dockerService.stopContainer(containerId);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_RESTART_CONTAINER, async (event, containerId) => {
            return await this.dockerService.restartContainer(containerId);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_REMOVE_CONTAINER, async (event, { id, force }) => {
            return await this.dockerService.removeContainer(id, force);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_GET_LOGS, async (event, { id, lines }) => {
            const result = await this.dockerService.getContainerLogs(id, lines || 100);
            return result.logs;
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_GET_STATS, async (event, containerId) => {
            return await this.dockerService.getContainerStats(containerId);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_GET_ALL_STATS, async () => {
            return await this.dockerService.getAllContainerStats();
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_PULL_IMAGE, async (event, imageName) => {
            return await this.dockerService.pullImage(imageName);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.DOCKER_GET_IMAGES, async () => {
            return await this.dockerService.getImages();
        });
        // =====================================================================
        // API Proxy Handlers
        // =====================================================================
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.API_REQUEST, async (event, request) => {
            return await this.handleApiRequest(request);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.API_GET, async (event, { url, config }) => {
            return await this.handleApiRequest({ method: 'GET', url, ...config });
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.API_POST, async (event, { url, data, config }) => {
            return await this.handleApiRequest({ method: 'POST', url, data, ...config });
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.API_PUT, async (event, { url, data, config }) => {
            return await this.handleApiRequest({ method: 'PUT', url, data, ...config });
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.API_DELETE, async (event, { url, config }) => {
            return await this.handleApiRequest({ method: 'DELETE', url, ...config });
        });
        // =====================================================================
        // Configuration Handlers
        // =====================================================================
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.CONFIG_GET, async (event, key) => {
            return this.getConfig(key);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.CONFIG_SET, async (event, { key, value }) => {
            return this.setConfig(key, value);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.CONFIG_RESET, async (event, key) => {
            return this.resetConfig(key);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.CONFIG_EXPORT, async () => {
            return this.exportConfig();
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.CONFIG_IMPORT, async (event, data) => {
            return this.importConfig(data);
        });
        // =====================================================================
        // File Handlers
        // =====================================================================
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.FILE_OPEN, async (event, options) => {
            const { dialog } = require('electron');
            return await dialog.showOpenDialog(this.mainWindow || {}, options);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.FILE_SAVE, async (event, options) => {
            const { dialog } = require('electron');
            return await dialog.showSaveDialog(this.mainWindow || {}, options);
        });
        // =====================================================================
        // System Info Handlers
        // =====================================================================
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.SYSTEM_GET_INFO, () => {
            return {
                platform: process.platform,
                arch: process.arch,
                nodeVersion: process.version,
                electronVersion: process.versions.electron,
            };
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.SYSTEM_GET_RESOURCES, () => {
            const { cpuUsage } = process;
            return {
                cpu: cpuUsage(),
                memory: process.memoryUsage(),
            };
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.SYSTEM_GET_NETWORK_INFO, async () => {
            const os = require('os');
            return {
                interfaces: os.networkInterfaces(),
                hostname: os.hostname(),
            };
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.SYSTEM_SHOW_NOTIFICATION, (event, { title, body }) => {
            const { Notification } = require('electron');
            new Notification({ title, body }).show();
            return { success: true };
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.SYSTEM_OPEN_EXTERNAL, (event, url) => {
            electron_1.shell.openExternal(url);
            return { success: true };
        });
        // =====================================================================
        // Logging Handlers
        // =====================================================================
        electron_1.ipcMain.on(ipc_channels_1.IPCChannels.LOG_INFO, (event, { message, context }) => {
            console.log(`[INFO] ${message}`, context);
        });
        electron_1.ipcMain.on(ipc_channels_1.IPCChannels.LOG_WARN, (event, { message, context }) => {
            console.warn(`[WARN] ${message}`, context);
        });
        electron_1.ipcMain.on(ipc_channels_1.IPCChannels.LOG_ERROR, (event, { message, context }) => {
            console.error(`[ERROR] ${message}`, context);
        });
        electron_1.ipcMain.on(ipc_channels_1.IPCChannels.LOG_DEBUG, (event, { message, context }) => {
            if (process.env.DEBUG) {
                console.debug(`[DEBUG] ${message}`, context);
            }
        });
        // =====================================================================
        // Authentication Handlers
        // =====================================================================
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.AUTH_LOGIN, async (event, { email, signature }) => {
            return await this.handleAuthLogin(email, signature);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.AUTH_LOGOUT, async () => {
            return await this.handleAuthLogout();
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.AUTH_VERIFY_TOKEN, async (event, { token }) => {
            return await this.verifyAuthToken(token);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.AUTH_REFRESH_TOKEN, async () => {
            return await this.refreshAuthToken();
        });
        // =====================================================================
        // Update Handlers
        // =====================================================================
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.UPDATE_CHECK, async () => {
            return { available: false };
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.UPDATE_DOWNLOAD, async () => {
            return { success: false };
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.UPDATE_INSTALL, async () => {
            return { success: false };
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.UPDATE_RESTART, async () => {
            electron_1.app.quit();
            return { success: true };
        });
        // =====================================================================
        // Hardware Wallet Handlers (Legacy)
        // =====================================================================
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.HARDWARE_WALLET_CONNECT, async (event, walletType) => {
            return await this.connectHardwareWallet(walletType);
        });
        electron_1.ipcMain.handle(ipc_channels_1.IPCChannels.HARDWARE_WALLET_SIGN, async (event, data) => {
            return await this.signWithHardwareWallet(data);
        });
    }
    setupAppEventHandlers() {
        // App ready event
        electron_1.app.whenReady().then(async () => {
            try {
                await this.initialize();
                await this.createMainWindow();
                await this.torManager.start();
            }
            catch (error) {
                console.error('Failed to start application:', error);
                electron_1.app.quit();
            }
        });
        // App window-all-closed event
        electron_1.app.on('window-all-closed', () => {
            if (process.platform !== 'darwin') {
                this.isQuitting = true;
                electron_1.app.quit();
            }
        });
        // App activate event (macOS)
        electron_1.app.on('activate', async () => {
            if (this.windows.size === 0) {
                await this.createMainWindow();
            }
        });
        // App before-quit event
        electron_1.app.on('before-quit', async (event) => {
            if (!this.isQuitting) {
                event.preventDefault();
                await this.cleanup();
                this.isQuitting = true;
                electron_1.app.quit();
            }
        });
    }
    async createMainWindow() {
        try {
            const { width, height } = electron_1.screen.getPrimaryDisplay().workAreaSize;
            this.mainWindow = new electron_1.BrowserWindow({
                width: Math.min(1200, width),
                height: Math.min(800, height),
                webPreferences: {
                    nodeIntegration: false,
                    contextIsolation: true,
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
            }
            else {
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
                electron_1.shell.openExternal(url);
                return { action: 'deny' };
            });
            console.log('Main window created successfully');
        }
        catch (error) {
            console.error('Failed to create main window:', error);
            throw error;
        }
    }
    async handleApiRequest(request) {
        try {
            // Proxy API requests through Tor if available
            const torStatus = this.torManager.getStatus();
            if (torStatus.connected) {
                // Route through Tor SOCKS proxy
                return await this.makeTorRequest(request);
            }
            else {
                // Direct request (development only)
                if (isDev) {
                    return await this.makeDirectRequest(request);
                }
                else {
                    throw new Error('Tor connection required for API requests');
                }
            }
        }
        catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
    async makeTorRequest(request) {
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
    async makeDirectRequest(request) {
        // Implement direct HTTP request for development
        console.log('Making direct request:', request.url);
        // Placeholder implementation
        return {
            success: true,
            data: { message: 'Direct request placeholder' },
            timestamp: new Date().toISOString()
        };
    }
    async connectHardwareWallet(walletType) {
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
        }
        catch (error) {
            console.error('Hardware wallet connection failed:', error);
            throw error;
        }
    }
    async connectLedgerWallet() {
        // Implement Ledger wallet connection
        return {
            success: true,
            walletType: 'ledger',
            address: 'ledger_address_placeholder',
            connected: true
        };
    }
    async connectTrezorWallet() {
        // Implement Trezor wallet connection
        return {
            success: true,
            walletType: 'trezor',
            address: 'trezor_address_placeholder',
            connected: true
        };
    }
    async connectKeepKeyWallet() {
        // Implement KeepKey wallet connection
        return {
            success: true,
            walletType: 'keepkey',
            address: 'keepkey_address_placeholder',
            connected: true
        };
    }
    async signWithHardwareWallet(data) {
        try {
            console.log('Signing data with hardware wallet...');
            // Implement hardware wallet signing
            return {
                success: true,
                signature: 'hardware_wallet_signature_placeholder',
                timestamp: new Date().toISOString()
            };
        }
        catch (error) {
            console.error('Hardware wallet signing failed:', error);
            throw error;
        }
    }
    async cleanup() {
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
        }
        catch (error) {
            console.error('Failed to cleanup Lucid Electron App:', error);
        }
    }
    getConfig(key) {
        if (key) {
            return this.config.get(key);
        }
        return Object.fromEntries(this.config);
    }
    setConfig(key, value) {
        this.config.set(key, value);
        // Broadcast config update to all windows
        this.windows.forEach((window) => {
            window.webContents.send(ipc_channels_1.IPCChannels.CONFIG_UPDATED, {
                key,
                value,
                scope: 'system',
                updatedAt: new Date().toISOString(),
            });
        });
        return { success: true };
    }
    resetConfig(key) {
        if (key) {
            this.config.delete(key);
        }
        else {
            this.config.clear();
        }
        return { success: true };
    }
    exportConfig() {
        return {
            config: Object.fromEntries(this.config),
            exportedAt: new Date().toISOString(),
        };
    }
    importConfig(data) {
        try {
            if (data.config && typeof data.config === 'object') {
                Object.entries(data.config).forEach(([key, value]) => {
                    this.config.set(key, value);
                });
            }
            return { success: true };
        }
        catch (error) {
            console.error('Failed to import config:', error);
            return { success: false };
        }
    }
    async handleAuthLogin(email, signature) {
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
        }
        catch (error) {
            console.error('Authentication failed:', error);
            return { success: false, error: 'Authentication failed' };
        }
    }
    async handleAuthLogout() {
        this.authToken = null;
        this.authTokenExpiry = null;
        if (this.tokenRefreshTimer) {
            clearTimeout(this.tokenRefreshTimer);
            this.tokenRefreshTimer = null;
        }
        this.broadcastAuthStatusChange(false);
        return { success: true };
    }
    async verifyAuthToken(token) {
        if (this.authToken === token && this.authTokenExpiry && new Date() < this.authTokenExpiry) {
            return {
                valid: true,
                user: { id: 'admin-1', email: 'admin@lucid.io', role: 'admin' },
                expiresAt: this.authTokenExpiry.toISOString(),
            };
        }
        return { valid: false };
    }
    async refreshAuthToken() {
        try {
            // TODO: Implement actual token refresh
            this.authTokenExpiry = new Date(Date.now() + 3600000); // Extend by 1 hour
            this.scheduleTokenRefresh();
            return { success: true, expiresAt: this.authTokenExpiry.toISOString() };
        }
        catch (error) {
            console.error('Token refresh failed:', error);
            return { success: false };
        }
    }
    scheduleTokenRefresh() {
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
    broadcastAuthStatusChange(authenticated, user) {
        this.windows.forEach((window) => {
            window.webContents.send(ipc_channels_1.IPCChannels.AUTH_STATUS_CHANGED, {
                authenticated,
                user,
                timestamp: new Date().toISOString(),
            });
        });
    }
    // Public methods for window management
    async createGUIWindow(guiType, options = {}) {
        return await this.windowManager.createWindow(guiType, options);
    }
    async closeGUIWindow(windowId) {
        await this.windowManager.closeWindow(windowId);
    }
    getTorStatus() {
        return this.torManager.getStatus();
    }
    getDockerStatus() {
        return this.dockerService.getStatus();
    }
}
exports.LucidElectronApp = LucidElectronApp;
// Create and export app instance
const lucidApp = new LucidElectronApp();
// Start the application
if (require.main === module) {
    lucidApp.initialize().catch((error) => {
        console.error('Failed to start Lucid Electron App:', error);
        process.exit(1);
    });
}
