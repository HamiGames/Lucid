// main/ipc-handlers.ts - IPC event handlers for all windows
// Based on the electron-multi-gui-development.plan.md specifications

import { ipcMain, BrowserWindow } from 'electron';
import { WindowManager } from './window-manager';
import { TorManager } from './tor-manager';
import { DockerService } from './docker-service';
import {
  RENDERER_TO_MAIN_CHANNELS,
  MAIN_TO_RENDERER_CHANNELS,
  BIDIRECTIONAL_CHANNELS,
  TorStatusMessage,
  TorConnectionMessage,
  TorBootstrapMessage,
  TorCircuitMessage,
  DockerServiceMessage,
  DockerContainerMessage,
  DockerHealthMessage,
  SystemNotificationMessage,
  ErrorMessage,
  WarningMessage,
  APIResponseMessage,
  APIErrorMessage,
  AuthStatusMessage,
  AuthTokenExpiredMessage,
  ConfigUpdatedMessage,
  SettingsChangedMessage,
} from '../shared/ipc-channels';

export function setupIpcHandlers(
  windowManager: WindowManager,
  torManager: TorManager,
  dockerService: DockerService
): void {
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

function setupTorHandlers(torManager: TorManager, windowManager: WindowManager): void {
  // Tor start
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_START, async (event, data) => {
    try {
      await torManager.start();
      const status = await torManager.getStatus();
      broadcastTorStatus(windowManager, status);
      return { success: true, pid: process.pid };
    } catch (error) {
      console.error('Tor start error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Tor stop
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_STOP, async (event, data) => {
    try {
      await torManager.stop();
      const status = await torManager.getStatus();
      broadcastTorStatus(windowManager, status);
      return { success: true };
    } catch (error) {
      console.error('Tor stop error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Tor restart
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_RESTART, async (event, data) => {
    try {
      await torManager.restart();
      const status = await torManager.getStatus();
      broadcastTorStatus(windowManager, status);
      return { success: true, pid: process.pid };
    } catch (error) {
      console.error('Tor restart error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Tor get status
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_GET_STATUS, async (event, data) => {
    try {
      const status = await torManager.getStatus();
      return {
        connected: status.is_connected,
        bootstrapProgress: status.bootstrap_progress,
        circuits: status.circuits.map(circuit => ({
          id: circuit.id,
          status: circuit.status,
          path: circuit.path,
          age: circuit.age,
        })),
        proxyPort: status.proxy_port,
        error: status.error,
      };
    } catch (error) {
      console.error('Tor get status error:', error);
      return { error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Tor get metrics
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_GET_METRICS, async (event, data) => {
    try {
      const metrics = await torManager.getMetrics();
      return metrics;
    } catch (error) {
      console.error('Tor get metrics error:', error);
      return { error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Tor test connection
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_TEST_CONNECTION, async (event, data) => {
    try {
      const success = await torManager.testConnection(data);
      return { success, responseTime: 0 };
    } catch (error) {
      console.error('Tor test connection error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Tor health check
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_HEALTH_CHECK, async (event, data) => {
    try {
      const health = await torManager.healthCheck();
      return health;
    } catch (error) {
      console.error('Tor health check error:', error);
      return { healthy: false, error: error instanceof Error ? error.message : String(error) };
    }
  });
}

function setupWindowHandlers(windowManager: WindowManager): void {
  // Window minimize
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.WINDOW_MINIMIZE, async (event, data) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (window) {
      window.minimize();
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  // Window maximize
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.WINDOW_MAXIMIZE, async (event, data) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (window) {
      window.maximize();
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  // Window restore
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.WINDOW_RESTORE, async (event, data) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (window) {
      window.restore();
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  // Window close
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.WINDOW_CLOSE, async (event, data) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (window) {
      window.close();
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  // Window set size
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.WINDOW_SET_SIZE, async (event, data) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (window) {
      window.setSize(data.width, data.height);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  // Window set position
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.WINDOW_SET_POSITION, async (event, data) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (window) {
      window.setPosition(data.x, data.y);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  // Window center
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.WINDOW_CENTER, async (event, data) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (window) {
      window.center();
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  // Window set always on top
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.WINDOW_SET_ALWAYS_ON_TOP, async (event, data) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (window) {
      window.setAlwaysOnTop(data.alwaysOnTop);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });
}

function setupDockerHandlers(dockerService: DockerService, windowManager: WindowManager): void {
  // Docker start services
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_START_SERVICES, async (event, data) => {
    try {
      const result = await dockerService.startServices(data.services, data.level);
      broadcastDockerServiceStatus(windowManager, result);
      return result;
    } catch (error) {
      console.error('Docker start services error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Docker stop services
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_STOP_SERVICES, async (event, data) => {
    try {
      const result = await dockerService.stopServices(data.services);
      broadcastDockerServiceStatus(windowManager, result);
      return result;
    } catch (error) {
      console.error('Docker stop services error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Docker restart services
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_RESTART_SERVICES, async (event, data) => {
    try {
      const result = await dockerService.restartServices(data.services);
      broadcastDockerServiceStatus(windowManager, result);
      return result;
    } catch (error) {
      console.error('Docker restart services error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Docker get service status
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_SERVICE_STATUS, async (event, data) => {
    try {
      const status = await dockerService.getServiceStatus();
      return status;
    } catch (error) {
      console.error('Docker get service status error:', error);
      return { error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Docker get container logs
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_CONTAINER_LOGS, async (event, data) => {
    try {
      const logs = await dockerService.getContainerLogs(data.containerId, data.lines, data.follow);
      return logs;
    } catch (error) {
      console.error('Docker get container logs error:', error);
      return { error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Docker exec command
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_EXEC_COMMAND, async (event, data) => {
    try {
      const result = await dockerService.execCommand(data.containerId, data.command, data.workingDir, data.env);
      return result;
    } catch (error) {
      console.error('Docker exec command error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });
}

function setupApiHandlers(windowManager: WindowManager): void {
  // API request
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.API_REQUEST, async (event, data) => {
    try {
      // This would typically proxy the request through Tor
      const response = await fetch(data.url, {
        method: data.method,
        headers: data.headers,
        body: data.data ? JSON.stringify(data.data) : undefined,
      });
      
      const responseData = await response.json();
      
      const apiResponse: APIResponseMessage = {
        requestId: data.id || 'unknown',
        data: responseData,
        status: response.status,
        headers: Object.fromEntries(response.headers.entries()),
      };
      
      return apiResponse;
    } catch (error) {
      console.error('API request error:', error);
      const apiError: APIErrorMessage = {
        requestId: data.id || 'unknown',
        error: error instanceof Error ? error.message : String(error),
        status: 500,
      };
      return apiError;
    }
  });
}

function setupAuthHandlers(windowManager: WindowManager): void {
  // Auth login
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.AUTH_LOGIN, async (event, data) => {
    try {
      // This would typically authenticate with the Lucid API
      const authStatus: AuthStatusMessage = {
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
    } catch (error) {
      console.error('Auth login error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Auth logout
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.AUTH_LOGOUT, async (event, data) => {
    try {
      const authStatus: AuthStatusMessage = {
        authenticated: false,
      };
      
      broadcastAuthStatus(windowManager, authStatus);
      return { success: true };
    } catch (error) {
      console.error('Auth logout error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Auth verify token
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.AUTH_VERIFY_TOKEN, async (event, data) => {
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
    } catch (error) {
      console.error('Auth verify token error:', error);
      return { valid: false, error: error instanceof Error ? error.message : String(error) };
    }
  });
}

function setupConfigHandlers(windowManager: WindowManager): void {
  // Config get
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.CONFIG_GET, async (event, data) => {
    try {
      // This would typically read from a config file or database
      return { value: null, exists: false };
    } catch (error) {
      console.error('Config get error:', error);
      return { error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Config set
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.CONFIG_SET, async (event, data) => {
    try {
      // This would typically save to a config file or database
      const configUpdate: ConfigUpdatedMessage = {
        key: data.key,
        value: data.value,
        timestamp: new Date().toISOString(),
      };
      
      broadcastConfigUpdated(windowManager, configUpdate);
      return { success: true };
    } catch (error) {
      console.error('Config set error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });
}

function setupFileHandlers(windowManager: WindowManager): void {
  // File operations would be implemented here
  // For security reasons, file operations should be carefully controlled
}

function setupSystemHandlers(windowManager: WindowManager): void {
  // System get info
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.SYSTEM_GET_INFO, async (event, data) => {
    try {
      return {
        platform: process.platform,
        arch: process.arch,
        version: process.version,
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        cpu: process.cpuUsage(),
      };
    } catch (error) {
      console.error('System get info error:', error);
      return { error: error instanceof Error ? error.message : String(error) };
    }
  });
}

function setupLoggingHandlers(windowManager: WindowManager): void {
  // Log info
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.LOG_INFO, async (event, data) => {
    console.log(`[INFO] ${data.message}`);
    return { success: true };
  });

  // Log warn
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.LOG_WARN, async (event, data) => {
    console.warn(`[WARN] ${data.message}`);
    return { success: true };
  });

  // Log error
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.LOG_ERROR, async (event, data) => {
    console.error(`[ERROR] ${data.message}`);
    return { success: true };
  });

  // Log debug
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.LOG_DEBUG, async (event, data) => {
    console.debug(`[DEBUG] ${data.message}`);
    return { success: true };
  });
}

function setupUpdateHandlers(windowManager: WindowManager): void {
  // Update handlers would be implemented here
  // This would typically integrate with auto-updater
}

function setupBidirectionalHandlers(windowManager: WindowManager): void {
  // Window send message
  ipcMain.handle(BIDIRECTIONAL_CHANNELS.WINDOW_SEND_MESSAGE, async (event, data) => {
    try {
      const targetWindow = windowManager.getWindow(data.targetWindow);
      if (targetWindow) {
        targetWindow.webContents.send(data.channel, data.data);
        return { success: true };
      }
      return { success: false, error: 'Target window not found' };
    } catch (error) {
      console.error('Window send message error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Window broadcast
  ipcMain.handle(BIDIRECTIONAL_CHANNELS.WINDOW_BROADCAST, async (event, data) => {
    try {
      windowManager.broadcastToAllWindows(data.channel, data.data);
      return { success: true };
    } catch (error) {
      console.error('Window broadcast error:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });
}

// Broadcast helper functions
function broadcastTorStatus(windowManager: WindowManager, status: any): void {
  const message: TorStatusMessage = {
    status: status.status,
    progress: status.bootstrap_progress,
    circuits: status.circuits?.length || 0,
  };
  
  windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.TOR_STATUS_UPDATE, message);
}

function broadcastDockerServiceStatus(windowManager: WindowManager, status: any): void {
  windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.DOCKER_SERVICE_STATUS, status);
}

function broadcastAuthStatus(windowManager: WindowManager, status: AuthStatusMessage): void {
  windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.AUTH_STATUS_CHANGED, status);
}

function broadcastConfigUpdated(windowManager: WindowManager, config: ConfigUpdatedMessage): void {
  windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.CONFIG_UPDATED, config);
}
