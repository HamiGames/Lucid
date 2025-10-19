// main/ipc/tor-handler.ts - Tor IPC handlers
// Based on the electron-multi-gui-development.plan.md specifications

import { ipcMain } from 'electron';
import { TorManager } from '../tor-manager';
import { WindowManager } from '../window-manager';
import { 
  RENDERER_TO_MAIN_CHANNELS, 
  MAIN_TO_RENDERER_CHANNELS,
  TorStartRequest,
  TorStartResponse,
  TorStopRequest,
  TorStopResponse,
  TorRestartRequest,
  TorRestartResponse,
  TorGetStatusResponse,
  TorGetMetricsResponse,
  TorTestConnectionRequest,
  TorTestConnectionResponse,
  TorHealthCheckResponse,
  TorStatusMessage,
  TorConnectionMessage,
  TorBootstrapMessage,
  TorCircuitMessage
} from '../../shared/ipc-channels';

export function setupTorHandlers(torManager: TorManager, windowManager: WindowManager): void {
  console.log('Setting up Tor IPC handlers...');

  // Tor start handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_START, async (event, request: TorStartRequest) => {
    try {
      console.log('Starting Tor with config:', request.config);
      
      // Start Tor with provided configuration
      await torManager.start();
      
      // Get status after start
      const status = await torManager.getStatus();
      
      // Broadcast status update
      broadcastTorStatus(windowManager, {
        status: status.connected ? 'connected' : 'connecting',
        progress: status.bootstrapProgress,
        circuits: status.circuits.length
      });

      return {
        success: true,
        pid: process.pid, // Tor runs as part of main process
        error: undefined
      } as TorStartResponse;
    } catch (error) {
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
      } as TorStartResponse;
    }
  });

  // Tor stop handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_STOP, async (event, request: TorStopRequest) => {
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
      } as TorStopResponse;
    } catch (error) {
      console.error('Tor stop error:', error);
      
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown stop error'
      } as TorStopResponse;
    }
  });

  // Tor restart handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_RESTART, async (event, request: TorRestartRequest) => {
    try {
      console.log('Restarting Tor with config:', request.config);
      
      // Restart Tor
      await torManager.restart();
      
      // Get status after restart
      const status = await torManager.getStatus();
      
      // Broadcast status update
      broadcastTorStatus(windowManager, {
        status: status.connected ? 'connected' : 'connecting',
        progress: status.bootstrapProgress,
        circuits: status.circuits.length
      });

      return {
        success: true,
        pid: process.pid,
        error: undefined
      } as TorRestartResponse;
    } catch (error) {
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
      } as TorRestartResponse;
    }
  });

  // Get Tor status handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_GET_STATUS, async (event) => {
    try {
      const status = await torManager.getStatus();
      
      return {
        connected: status.connected,
        bootstrapProgress: status.bootstrapProgress,
        circuits: status.circuits.map(circuit => ({
          id: circuit.id,
          status: circuit.status,
          path: circuit.path,
          age: circuit.age
        })),
        proxyPort: status.proxyPort,
        error: status.error
      } as TorGetStatusResponse;
    } catch (error) {
      console.error('Tor get status error:', error);
      
      return {
        connected: false,
        bootstrapProgress: 0,
        circuits: [],
        proxyPort: 0,
        error: error instanceof Error ? error.message : 'Unknown status error'
      } as TorGetStatusResponse;
    }
  });

  // Get Tor metrics handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_GET_METRICS, async (event) => {
    try {
      const metrics = await torManager.getMetrics();
      
      return {
        bytesRead: metrics.bytesRead || 0,
        bytesWritten: metrics.bytesWritten || 0,
        circuitsBuilt: metrics.circuitsBuilt || 0,
        circuitsFailed: metrics.circuitsFailed || 0,
        bootstrapTime: metrics.bootstrapTime || 0,
        uptime: metrics.uptime || 0
      } as TorGetMetricsResponse;
    } catch (error) {
      console.error('Tor get metrics error:', error);
      
      return {
        bytesRead: 0,
        bytesWritten: 0,
        circuitsBuilt: 0,
        circuitsFailed: 0,
        bootstrapTime: 0,
        uptime: 0
      } as TorGetMetricsResponse;
    }
  });

  // Test Tor connection handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_TEST_CONNECTION, async (event, request: TorTestConnectionRequest) => {
    try {
      const { url, timeout = 10000 } = request;
      
      if (!url) {
        return {
          success: false,
          responseTime: 0,
          error: 'URL is required'
        } as TorTestConnectionResponse;
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
      } as TorTestConnectionResponse;
    } catch (error) {
      console.error('Tor test connection error:', error);
      
      return {
        success: false,
        responseTime: 0,
        error: error instanceof Error ? error.message : 'Unknown test error'
      } as TorTestConnectionResponse;
    }
  });

  // Tor health check handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.TOR_HEALTH_CHECK, async (event) => {
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
      } as TorHealthCheckResponse;
    } catch (error) {
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
      } as TorHealthCheckResponse;
    }
  });

  // Setup Tor event listeners for real-time updates
  setupTorEventListeners(torManager, windowManager);

  console.log('Tor IPC handlers setup complete');
}

// Setup Tor event listeners for real-time status updates
function setupTorEventListeners(torManager: TorManager, windowManager: WindowManager): void {
  // Listen for Tor status changes
  torManager.addEventListener('statusChanged', (status) => {
    const message: TorStatusMessage = {
      status: status.connected ? 'connected' : status.connecting ? 'connecting' : 'disconnected',
      progress: status.bootstrapProgress,
      error: status.error,
      circuits: status.circuits.length
    };
    
    broadcastTorStatus(windowManager, message);
  });

  // Listen for Tor connection changes
  torManager.addEventListener('connectionChanged', (connected, error) => {
    const message: TorConnectionMessage = {
      connected,
      timestamp: new Date().toISOString(),
      error
    };
    
    windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.TOR_CONNECTION_CHANGED, message);
  });

  // Listen for Tor bootstrap progress updates
  torManager.addEventListener('bootstrapProgress', (progress, summary, warning) => {
    const message: TorBootstrapMessage = {
      progress,
      summary,
      warning
    };
    
    windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.TOR_BOOTSTRAP_PROGRESS, message);
  });

  // Listen for Tor circuit updates
  torManager.addEventListener('circuitUpdate', (circuit) => {
    const message: TorCircuitMessage = {
      circuitId: circuit.id,
      status: circuit.status as any,
      path: circuit.path,
      age: circuit.age
    };
    
    windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.TOR_CIRCUIT_UPDATE, message);
  });

  // Listen for Tor errors
  torManager.addEventListener('error', (error) => {
    console.error('Tor error event:', error);
    
    // Broadcast error to all windows
    windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.ERROR_OCCURRED, {
      code: 'TOR_ERROR',
      message: error.message || 'Unknown Tor error',
      details: error,
      stack: error.stack,
      timestamp: new Date().toISOString()
    });
  });
}

// Helper function to broadcast Tor status updates
function broadcastTorStatus(windowManager: WindowManager, status: TorStatusMessage): void {
  windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.TOR_STATUS_UPDATE, status);
}

// Export helper functions for use by other modules
export { broadcastTorStatus, setupTorEventListeners };
