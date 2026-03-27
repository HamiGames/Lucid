"use strict";
// main/ipc-handlers.ts - IPC event handlers for all windows
// Based on the electron-multi-gui-development.plan.md specifications
Object.defineProperty(exports, "__esModule", { value: true });
exports.setupIpcHandlers = void 0;
const electron_1 = require("electron");
const tor_handler_1 = require("./ipc/tor-handler");
const ipc_channels_1 = require("../shared/ipc-channels");
function setupIpcHandlers(windowManager, torManager, dockerService) {
    console.log('Setting up IPC handlers...');
    // Tor control handlers
    setupTorHandlers(torManager, windowManager);
    // Window control handlers
    setupWindowHandlers(windowManager);
    // Docker control handlers
    setupDockerHandlers(dockerService, windowManager);
    // API request handlers
    setupApiHandlers(windowManager);
    // Authentication handlers
    setupAuthHandlers(windowManager);
    // Configuration handlers
    setupConfigHandlers(windowManager);
    // File operation handlers
    setupFileHandlers(windowManager);
    // System operation handlers
    setupSystemHandlers(windowManager);
    // Logging handlers
    setupLoggingHandlers(windowManager);
    // Update handlers
    setupUpdateHandlers(windowManager);
    // Bidirectional communication handlers
    setupBidirectionalHandlers(windowManager);
    console.log('IPC handlers setup complete');
}
exports.setupIpcHandlers = setupIpcHandlers;
function setupTorHandlers(torManager, windowManager) {
    // Tor start
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_START, async (event, data) => {
        try {
            await torManager.start();
            const status = await torManager.getStatus();
            broadcastTorStatus(windowManager, status);
            return { success: true, pid: process.pid };
        }
        catch (error) {
            console.error('Tor start error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Tor stop
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_STOP, async (event, data) => {
        try {
            await torManager.stop();
            const status = await torManager.getStatus();
            broadcastTorStatus(windowManager, status);
            return { success: true };
        }
        catch (error) {
            console.error('Tor stop error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Tor restart
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_RESTART, async (event, data) => {
        try {
            await torManager.restart();
            const status = await torManager.getStatus();
            broadcastTorStatus(windowManager, status);
            return { success: true, pid: process.pid };
        }
        catch (error) {
            console.error('Tor restart error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Tor get status
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_GET_STATUS, async (event, data) => {
        try {
            const status = torManager.getStatus();
            return (0, tor_handler_1.mapTorStatusForIpc)(status);
        }
        catch (error) {
            console.error('Tor get status error:', error);
            return { error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Tor get metrics
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_GET_METRICS, async (event, data) => {
        try {
            const metrics = await torManager.getMetrics();
            return metrics;
        }
        catch (error) {
            console.error('Tor get metrics error:', error);
            return { error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Tor test connection
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_TEST_CONNECTION, async (event, data) => {
        try {
            const success = await torManager.testConnection(data);
            return { success, responseTime: 0 };
        }
        catch (error) {
            console.error('Tor test connection error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Tor health check
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_HEALTH_CHECK, async (event, data) => {
        try {
            const health = await torManager.healthCheck();
            return health;
        }
        catch (error) {
            console.error('Tor health check error:', error);
            return { healthy: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
}
function setupWindowHandlers(windowManager) {
    // Window minimize
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.WINDOW_MINIMIZE, async (event, data) => {
        const window = electron_1.BrowserWindow.fromWebContents(event.sender);
        if (window) {
            window.minimize();
            return { success: true };
        }
        return { success: false, error: 'Window not found' };
    });
    // Window maximize
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.WINDOW_MAXIMIZE, async (event, data) => {
        const window = electron_1.BrowserWindow.fromWebContents(event.sender);
        if (window) {
            window.maximize();
            return { success: true };
        }
        return { success: false, error: 'Window not found' };
    });
    // Window restore
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.WINDOW_RESTORE, async (event, data) => {
        const window = electron_1.BrowserWindow.fromWebContents(event.sender);
        if (window) {
            window.restore();
            return { success: true };
        }
        return { success: false, error: 'Window not found' };
    });
    // Window close
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.WINDOW_CLOSE, async (event, data) => {
        const window = electron_1.BrowserWindow.fromWebContents(event.sender);
        if (window) {
            window.close();
            return { success: true };
        }
        return { success: false, error: 'Window not found' };
    });
    // Window set size
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.WINDOW_SET_SIZE, async (event, data) => {
        const window = electron_1.BrowserWindow.fromWebContents(event.sender);
        if (window) {
            window.setSize(data.width, data.height);
            return { success: true };
        }
        return { success: false, error: 'Window not found' };
    });
    // Window set position
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.WINDOW_SET_POSITION, async (event, data) => {
        const window = electron_1.BrowserWindow.fromWebContents(event.sender);
        if (window) {
            window.setPosition(data.x, data.y);
            return { success: true };
        }
        return { success: false, error: 'Window not found' };
    });
    // Window center
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.WINDOW_CENTER, async (event, data) => {
        const window = electron_1.BrowserWindow.fromWebContents(event.sender);
        if (window) {
            window.center();
            return { success: true };
        }
        return { success: false, error: 'Window not found' };
    });
    // Window set always on top
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.WINDOW_SET_ALWAYS_ON_TOP, async (event, data) => {
        const window = electron_1.BrowserWindow.fromWebContents(event.sender);
        if (window) {
            window.setAlwaysOnTop(data.alwaysOnTop);
            return { success: true };
        }
        return { success: false, error: 'Window not found' };
    });
}
function setupDockerHandlers(dockerService, windowManager) {
    // Docker start services
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_START_SERVICES, async (event, data) => {
        try {
            const result = await dockerService.startServices(data.services, data.level);
            broadcastDockerServiceStatus(windowManager, result);
            return result;
        }
        catch (error) {
            console.error('Docker start services error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Docker stop services
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_STOP_SERVICES, async (event, data) => {
        try {
            const result = await dockerService.stopServices(data.services);
            broadcastDockerServiceStatus(windowManager, result);
            return result;
        }
        catch (error) {
            console.error('Docker stop services error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Docker restart services
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_RESTART_SERVICES, async (event, data) => {
        try {
            const result = await dockerService.restartServices(data.services);
            broadcastDockerServiceStatus(windowManager, result);
            return result;
        }
        catch (error) {
            console.error('Docker restart services error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Docker get service status
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_SERVICE_STATUS, async (event, data) => {
        try {
            const status = await dockerService.getOrchestratedServiceStatus();
            return status;
        }
        catch (error) {
            console.error('Docker get service status error:', error);
            return { error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Docker get container logs
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_CONTAINER_LOGS, async (event, data) => {
        try {
            const { logs, error } = await dockerService.getContainerLogs(data.containerId, data.lines, data.follow);
            return { logs, error };
        }
        catch (error) {
            console.error('Docker get container logs error:', error);
            return { error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Docker exec command
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_EXEC_COMMAND, async (event, data) => {
        try {
            const result = await dockerService.execCommand(data.containerId, data.command, data.workingDir, data.env);
            return result;
        }
        catch (error) {
            console.error('Docker exec command error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
}
function setupApiHandlers(windowManager) {
    // API request
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.API_REQUEST, async (event, data) => {
        try {
            // This would typically proxy the request through Tor
            const response = await fetch(data.url, {
                method: data.method,
                headers: data.headers,
                body: data.data ? JSON.stringify(data.data) : undefined,
            });
            const responseData = await response.json();
            const apiResponse = {
                requestId: data.id || 'unknown',
                data: responseData,
                status: response.status,
                headers: Object.fromEntries(response.headers.entries()),
            };
            return apiResponse;
        }
        catch (error) {
            console.error('API request error:', error);
            const apiError = {
                requestId: data.id || 'unknown',
                error: error instanceof Error ? error.message : String(error),
                status: 500,
            };
            return apiError;
        }
    });
}
function setupAuthHandlers(windowManager) {
    // Auth login
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.AUTH_LOGIN, async (event, data) => {
        try {
            // This would typically authenticate with the Lucid API
            const authStatus = {
                authenticated: true,
                user: {
                    id: 'user-123',
                    email: data.email,
                    role: 'user',
                },
                token: 'mock-token',
                expiresAt: new Date(Date.now() + 3600000).toISOString(),
            };
            broadcastAuthStatus(windowManager, authStatus);
            return { success: true, token: 'mock-token', user: authStatus.user };
        }
        catch (error) {
            console.error('Auth login error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Auth logout
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.AUTH_LOGOUT, async (event, data) => {
        try {
            const authStatus = {
                authenticated: false,
            };
            broadcastAuthStatus(windowManager, authStatus);
            return { success: true };
        }
        catch (error) {
            console.error('Auth logout error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Auth verify token
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.AUTH_VERIFY_TOKEN, async (event, data) => {
        try {
            // This would typically verify the token with the Lucid API
            return {
                valid: true,
                user: {
                    id: 'user-123',
                    email: 'user@example.com',
                    role: 'user',
                },
                expiresAt: new Date(Date.now() + 3600000).toISOString(),
            };
        }
        catch (error) {
            console.error('Auth verify token error:', error);
            return { valid: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
}
function setupConfigHandlers(windowManager) {
    // Config get
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.CONFIG_GET, async (event, data) => {
        try {
            // This would typically read from a config file or database
            return { value: null, exists: false };
        }
        catch (error) {
            console.error('Config get error:', error);
            return { error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Config set
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.CONFIG_SET, async (event, data) => {
        try {
            // This would typically save to a config file or database
            const configUpdate = {
                key: data.key,
                value: data.value,
                scope: 'system',
                updatedAt: new Date().toISOString(),
            };
            broadcastConfigUpdated(windowManager, configUpdate);
            return { success: true };
        }
        catch (error) {
            console.error('Config set error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
}
function setupFileHandlers(windowManager) {
    // File operations would be implemented here
    // For security reasons, file operations should be carefully controlled
}
function setupSystemHandlers(windowManager) {
    // System get info
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.SYSTEM_GET_INFO, async (event, data) => {
        try {
            return {
                platform: process.platform,
                arch: process.arch,
                version: process.version,
                uptime: process.uptime(),
                memory: process.memoryUsage(),
                cpu: process.cpuUsage(),
            };
        }
        catch (error) {
            console.error('System get info error:', error);
            return { error: error instanceof Error ? error.message : String(error) };
        }
    });
}
function setupLoggingHandlers(windowManager) {
    // Log info
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.LOG_INFO, async (event, data) => {
        console.log(`[INFO] ${data.message}`);
        return { success: true };
    });
    // Log warn
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.LOG_WARN, async (event, data) => {
        console.warn(`[WARN] ${data.message}`);
        return { success: true };
    });
    // Log error
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.LOG_ERROR, async (event, data) => {
        console.error(`[ERROR] ${data.message}`);
        return { success: true };
    });
    // Log debug
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.LOG_DEBUG, async (event, data) => {
        console.debug(`[DEBUG] ${data.message}`);
        return { success: true };
    });
}
function setupUpdateHandlers(windowManager) {
    // Update handlers would be implemented here
    // This would typically integrate with auto-updater
}
function setupBidirectionalHandlers(windowManager) {
    // Window send message
    electron_1.ipcMain.handle(ipc_channels_1.BIDIRECTIONAL_CHANNELS.WINDOW_SEND_MESSAGE, async (event, data) => {
        try {
            const targetWindow = windowManager.getWindow(data.targetWindow);
            if (targetWindow) {
                targetWindow.window.webContents.send(data.channel, data.data);
                return { success: true };
            }
            return { success: false, error: 'Target window not found' };
        }
        catch (error) {
            console.error('Window send message error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
    // Window broadcast
    electron_1.ipcMain.handle(ipc_channels_1.BIDIRECTIONAL_CHANNELS.WINDOW_BROADCAST, async (event, data) => {
        try {
            windowManager.broadcastToAllWindows(data.channel, data.data);
            return { success: true };
        }
        catch (error) {
            console.error('Window broadcast error:', error);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });
}
// Broadcast helper functions
function broadcastTorStatus(windowManager, status) {
    const message = {
        status: status.connected
            ? 'connected'
            : status.status === 'starting'
                ? 'connecting'
                : 'disconnected',
        progress: (0, tor_handler_1.torBootstrapProgress)(status),
        circuits: status.circuits ?? 0,
        proxyPort: status.socksPort,
        error: status.error,
    };
    windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.TOR_STATUS_UPDATE, message);
}
function broadcastDockerServiceStatus(windowManager, status) {
    windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.DOCKER_SERVICE_STATUS, status);
}
function broadcastAuthStatus(windowManager, status) {
    windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.AUTH_STATUS_CHANGED, status);
}
function broadcastConfigUpdated(windowManager, config) {
    windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.CONFIG_UPDATED, config);
}
