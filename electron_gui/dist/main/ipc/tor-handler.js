"use strict";
// main/ipc/tor-handler.ts - Tor IPC handlers
// Based on the electron-multi-gui-development.plan.md specifications
Object.defineProperty(exports, "__esModule", { value: true });
exports.setupTorEventListeners = exports.broadcastTorStatus = exports.setupTorHandlers = exports.mapTorStatusForIpc = exports.torBootstrapProgress = void 0;
const electron_1 = require("electron");
const ipc_channels_1 = require("../../shared/ipc-channels");
function torBootstrapProgress(status) {
    if (status.status === 'connected')
        return 100;
    if (status.status === 'starting')
        return 50;
    return 0;
}
exports.torBootstrapProgress = torBootstrapProgress;
function mapTorStatusForIpc(status) {
    return {
        connected: status.connected,
        connecting: status.status === 'starting',
        bootstrapProgress: torBootstrapProgress(status),
        circuits: [],
        proxyPort: status.socksPort,
        controlPort: status.controlPort,
        error: status.error,
    };
}
exports.mapTorStatusForIpc = mapTorStatusForIpc;
function setupTorHandlers(torManager, windowManager) {
    console.log('Setting up Tor IPC handlers...');
    // Tor start handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_START, async (event, request) => {
        try {
            console.log('Starting Tor with config:', request.config);
            // Start Tor with provided configuration
            await torManager.start();
            // Get status after start
            const status = torManager.getStatus();
            // Broadcast status update
            broadcastTorStatus(windowManager, {
                status: status.connected ? 'connected' : status.status === 'starting' ? 'connecting' : 'disconnected',
                progress: torBootstrapProgress(status),
                circuits: status.circuits ?? 0,
                proxyPort: status.socksPort,
            });
            return {
                success: true,
                pid: process.pid, // Tor runs as part of main process
                error: undefined
            };
        }
        catch (error) {
            console.error('Tor start error:', error);
            // Broadcast error status
            broadcastTorStatus(windowManager, {
                status: 'disconnected',
                error: error instanceof Error ? error.message : 'Unknown start error'
            });
            return {
                success: false,
                pid: undefined,
                error: error instanceof Error ? error.message : 'Unknown start error'
            };
        }
    });
    // Tor stop handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_STOP, async (event, request) => {
        try {
            console.log('Stopping Tor, force:', request.force);
            // Stop Tor
            await torManager.stop();
            // Broadcast disconnection
            broadcastTorStatus(windowManager, {
                status: 'disconnected'
            });
            return {
                success: true,
                error: undefined
            };
        }
        catch (error) {
            console.error('Tor stop error:', error);
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Unknown stop error'
            };
        }
    });
    // Tor restart handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_RESTART, async (event, request) => {
        try {
            console.log('Restarting Tor with config:', request.config);
            // Restart Tor
            await torManager.restart();
            // Get status after restart
            const status = torManager.getStatus();
            // Broadcast status update
            broadcastTorStatus(windowManager, {
                status: status.connected ? 'connected' : status.status === 'starting' ? 'connecting' : 'disconnected',
                progress: torBootstrapProgress(status),
                circuits: status.circuits ?? 0,
                proxyPort: status.socksPort,
            });
            return {
                success: true,
                pid: process.pid,
                error: undefined
            };
        }
        catch (error) {
            console.error('Tor restart error:', error);
            // Broadcast error status
            broadcastTorStatus(windowManager, {
                status: 'disconnected',
                error: error instanceof Error ? error.message : 'Unknown restart error'
            });
            return {
                success: false,
                pid: undefined,
                error: error instanceof Error ? error.message : 'Unknown restart error'
            };
        }
    });
    // Get Tor status handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_GET_STATUS, async (event) => {
        try {
            const status = torManager.getStatus();
            return mapTorStatusForIpc(status);
        }
        catch (error) {
            console.error('Tor get status error:', error);
            return {
                connected: false,
                connecting: false,
                bootstrapProgress: 0,
                circuits: [],
                proxyPort: 0,
                controlPort: 0,
                error: error instanceof Error ? error.message : 'Unknown status error'
            };
        }
    });
    // Get Tor metrics handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_GET_METRICS, async (event) => {
        try {
            const metrics = await torManager.getMetrics();
            return {
                uptimeSeconds: metrics.uptimeSeconds ?? 0,
                bytesRead: metrics.bytesRead || 0,
                bytesWritten: metrics.bytesWritten || 0,
                circuitsBuilt: metrics.circuitsBuilt || 0,
                circuitsFailed: metrics.circuitsFailed || 0,
                lastUpdated: metrics.lastUpdated ?? new Date().toISOString(),
            };
        }
        catch (error) {
            console.error('Tor get metrics error:', error);
            return {
                uptimeSeconds: 0,
                bytesRead: 0,
                bytesWritten: 0,
                circuitsBuilt: 0,
                circuitsFailed: 0,
                lastUpdated: new Date().toISOString(),
            };
        }
    });
    // Test Tor connection handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_TEST_CONNECTION, async (event, request) => {
        try {
            const { url, timeout = 10000 } = request;
            if (!url) {
                return {
                    success: false,
                    responseTime: 0,
                    error: 'URL is required'
                };
            }
            const startTime = Date.now();
            const testResult = await torManager.testConnection({
                url,
                timeout
            });
            const responseTime = Date.now() - startTime;
            return {
                success: testResult,
                responseTime,
                error: testResult ? undefined : 'Connection test failed'
            };
        }
        catch (error) {
            console.error('Tor test connection error:', error);
            return {
                success: false,
                responseTime: 0,
                error: error instanceof Error ? error.message : 'Unknown test error'
            };
        }
    });
    // Tor health check handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.TOR_HEALTH_CHECK, async (event) => {
        try {
            const healthCheck = await torManager.healthCheck();
            return {
                healthy: healthCheck.healthy,
                lastCheck: new Date().toISOString(),
                responseTime: healthCheck.responseTime || 0,
                tests: {
                    socksProxy: healthCheck.socksProxy || false,
                    controlPort: healthCheck.controlPort || false,
                    bootstrap: healthCheck.bootstrap || false,
                    circuitBuild: healthCheck.circuitBuild || false
                },
                error: healthCheck.error
            };
        }
        catch (error) {
            console.error('Tor health check error:', error);
            return {
                healthy: false,
                lastCheck: new Date().toISOString(),
                responseTime: 0,
                tests: {
                    socksProxy: false,
                    controlPort: false,
                    bootstrap: false,
                    circuitBuild: false
                },
                error: error instanceof Error ? error.message : 'Unknown health check error'
            };
        }
    });
    // Setup Tor event listeners for real-time updates
    setupTorEventListeners(torManager, windowManager);
    console.log('Tor IPC handlers setup complete');
}
exports.setupTorHandlers = setupTorHandlers;
// Setup Tor event listeners for real-time status updates
function setupTorEventListeners(torManager, windowManager) {
    // Listen for Tor status changes
    torManager.addEventListener('statusChanged', (...args) => {
        const status = args[0];
        const message = {
            status: status.connected
                ? 'connected'
                : status.status === 'starting'
                    ? 'connecting'
                    : 'disconnected',
            progress: torBootstrapProgress(status),
            error: status.error,
            circuits: status.circuits ?? 0,
            proxyPort: status.socksPort,
        };
        broadcastTorStatus(windowManager, message);
    });
    // Listen for Tor connection changes
    torManager.addEventListener('connectionChanged', (...args) => {
        const connected = args[0];
        const error = args[1];
        const message = {
            connected,
            timestamp: new Date().toISOString(),
            error
        };
        windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.TOR_CONNECTION_CHANGED, message);
    });
    // Listen for Tor bootstrap progress updates
    torManager.addEventListener('bootstrapProgress', (...args) => {
        const progress = args[0];
        const summary = args[1];
        const warning = args[2];
        const message = {
            progress,
            summary,
            warning
        };
        windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.TOR_BOOTSTRAP_PROGRESS, message);
    });
    // Listen for Tor circuit updates
    torManager.addEventListener('circuitUpdate', (...args) => {
        const circuit = args[0];
        const message = {
            circuitId: circuit.id,
            status: circuit.status,
            path: circuit.path,
            age: circuit.age
        };
        windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.TOR_CIRCUIT_UPDATE, message);
    });
    // Listen for Tor errors
    torManager.addEventListener('error', (...args) => {
        const error = args[0];
        const err = error instanceof Error ? error : new Error(String(error));
        console.error('Tor error event:', err);
        // Broadcast error to all windows
        windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.ERROR_OCCURRED, {
            code: 'TOR_ERROR',
            message: err.message || 'Unknown Tor error',
            details: error,
            stack: err.stack,
            timestamp: new Date().toISOString()
        });
    });
}
exports.setupTorEventListeners = setupTorEventListeners;
// Helper function to broadcast Tor status updates
function broadcastTorStatus(windowManager, status) {
    windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.TOR_STATUS_UPDATE, status);
}
exports.broadcastTorStatus = broadcastTorStatus;
