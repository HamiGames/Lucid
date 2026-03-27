// main/ipc/docker-handler.ts - Docker IPC handlers
// Based on the electron-multi-gui-development.plan.md specifications

import { ipcMain } from 'electron';
import { DockerService } from '../docker-service';
import { WindowManager } from '../window-manager';
import { 
  RENDERER_TO_MAIN_CHANNELS, 
  MAIN_TO_RENDERER_CHANNELS,
  DockerStartServicesRequest,
  DockerStartServicesResponse,
  DockerStopServicesRequest,
  DockerStopServicesResponse,
  DockerGetServiceStatusResponse,
  DockerGetContainerLogsRequest,
  DockerGetContainerLogsResponse,
  DockerExecCommandRequest,
  DockerExecCommandResponse,
  DockerServiceMessage,
  DockerContainerMessage,
  DockerHealthMessage
} from '../../shared/ipc-channels';

function broadcastDockerServiceStatus(
  windowManager: WindowManager,
  status: Omit<DockerServiceMessage, 'timestamp'>
): void {
  const message: DockerServiceMessage = {
    ...status,
    timestamp: new Date().toISOString(),
  };
  windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.DOCKER_SERVICE_STATUS, message);
}

export function setupDockerHandlers(dockerService: DockerService, windowManager: WindowManager): void {
  console.log('Setting up Docker IPC handlers...');

  // Start Docker services handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_START_SERVICES, async (event, request: DockerStartServicesRequest) => {
    try {
      const { services, level } = request;
      
      console.log(`Starting Docker services: ${services.join(', ')} with level: ${level}`);
      
      // Start services using DockerService
      const result = await dockerService.startServices(services, level);
      
      // Broadcast service status updates
      if (result.started.length > 0) {
        for (const serviceName of result.started) {
          const serviceStatus = await dockerService.findServiceStateByName(serviceName);
          if (serviceStatus) {
            broadcastDockerServiceStatus(windowManager, {
              service: serviceName,
              status: serviceStatus.status,
              containerId: serviceStatus.containerId,
              error: serviceStatus.error
            });
          }
        }
      }
      
      // Broadcast failed services
      if (result.failed.length > 0) {
        for (const failure of result.failed) {
          broadcastDockerServiceStatus(windowManager, {
            service: failure.service,
            status: 'error',
            error: failure.error
          });
        }
      }
      
      return {
        success: result.success,
        started: result.started,
        failed: result.failed,
      } as unknown as DockerStartServicesResponse;
    } catch (error) {
      console.error('Docker start services error:', error);
      
      return {
        success: false,
        started: [],
        failed: [{
          service: 'unknown',
          error: error instanceof Error ? error.message : 'Unknown start error'
        }]
      } as unknown as DockerStartServicesResponse;
    }
  });

  // Stop Docker services handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_STOP_SERVICES, async (event, request: DockerStopServicesRequest) => {
    try {
      const { services } = request;
      
      console.log(`Stopping Docker services: ${services.join(', ')}`);
      
      // Stop services using DockerService
      const result = await dockerService.stopServices(services);
      
      // Broadcast service status updates
      if (result.stopped.length > 0) {
        for (const serviceName of result.stopped) {
          broadcastDockerServiceStatus(windowManager, {
            service: serviceName,
            status: 'stopped'
          });
        }
      }
      
      // Broadcast failed services
      if (result.failed.length > 0) {
        for (const failure of result.failed) {
          broadcastDockerServiceStatus(windowManager, {
            service: failure.service,
            status: 'error',
            error: failure.error
          });
        }
      }
      
      return {
        success: result.success,
        stopped: result.stopped,
        failed: result.failed
      } as unknown as DockerStopServicesResponse;
    } catch (error) {
      console.error('Docker stop services error:', error);
      
      return {
        success: false,
        stopped: [],
        failed: [{
          service: 'unknown',
          error: error instanceof Error ? error.message : 'Unknown stop error'
        }]
      } as unknown as DockerStopServicesResponse;
    }
  });

  // Restart Docker services handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_RESTART_SERVICES, async (event, { services }) => {
    try {
      console.log(`Restarting Docker services: ${services.join(', ')}`);
      
      // Restart services using DockerService
      const result = await dockerService.restartServices(services);
      
      // Broadcast service status updates
      if (result.started.length > 0) {
        for (const serviceName of result.started) {
          const serviceStatus = await dockerService.findServiceStateByName(serviceName);
          if (serviceStatus) {
            broadcastDockerServiceStatus(windowManager, {
              service: serviceName,
              status: serviceStatus.status,
              containerId: serviceStatus.containerId,
              error: serviceStatus.error
            });
          }
        }
      }
      
      // Broadcast failed services
      if (result.failed.length > 0) {
        for (const failure of result.failed) {
          broadcastDockerServiceStatus(windowManager, {
            service: failure.service,
            status: 'error',
            error: failure.error
          });
        }
      }
      
      return {
        success: result.success,
        started: result.started,
        failed: result.failed
      } as unknown as DockerStartServicesResponse;
    } catch (error) {
      console.error('Docker restart services error:', error);
      
      return {
        success: false,
        started: [],
        failed: [{
          service: 'unknown',
          error: error instanceof Error ? error.message : 'Unknown restart error'
        }]
      } as unknown as DockerStartServicesResponse;
    }
  });

  // Get Docker service status handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_SERVICE_STATUS, async (event, serviceName?: string) => {
    try {
      console.log(`Getting Docker service status${serviceName ? ` for: ${serviceName}` : ' for all services'}`);
      
      // Get service status using DockerService
      const result = await dockerService.getOrchestratedServiceStatus();
      return result as DockerGetServiceStatusResponse;
    } catch (error) {
      console.error('Docker get service status error:', error);
      
      return {
        services: [],
        generatedAt: new Date().toISOString(),
      } as DockerGetServiceStatusResponse;
    }
  });

  // Get Docker container logs handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_CONTAINER_LOGS, async (event, request: DockerGetContainerLogsRequest) => {
    try {
      const { containerId, lines = 100, follow = false } = request;
      
      console.log(`Getting Docker container logs for: ${containerId}, lines: ${lines}, follow: ${follow}`);
      
      // Get container logs using DockerService
      const result = await dockerService.getContainerLogs(containerId, lines, follow);
      
      return {
        containerId,
        logs: result.logs,
        error: result.error,
        generatedAt: new Date().toISOString(),
      } as DockerGetContainerLogsResponse;
    } catch (error) {
      console.error('Docker get container logs error:', error);
      
      return {
        containerId: request.containerId,
        logs: [],
        error: error instanceof Error ? error.message : 'Unknown logs error',
        generatedAt: new Date().toISOString(),
      } as DockerGetContainerLogsResponse;
    }
  });

  // Execute command in Docker container handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_EXEC_COMMAND, async (event, request: DockerExecCommandRequest) => {
    try {
      const { containerId, command, workingDir, env } = request;
      
      console.log(`Executing command in Docker container: ${containerId}, command: ${command.join(' ')}`);
      
      const startedAt = new Date().toISOString();
      // Execute command using DockerService
      const result = await dockerService.execCommand(containerId, command, workingDir, env);
      
      return {
        success: result.success,
        containerId,
        output: result.output,
        error: result.error,
        exitCode: result.exitCode,
        startedAt,
        finishedAt: new Date().toISOString(),
      } as DockerExecCommandResponse;
    } catch (error) {
      console.error('Docker exec command error:', error);
      
      const finishedAt = new Date().toISOString();
      return {
        success: false,
        containerId: request.containerId,
        output: '',
        error: error instanceof Error ? error.message : 'Unknown exec error',
        exitCode: -1,
        startedAt: finishedAt,
        finishedAt,
      } as DockerExecCommandResponse;
    }
  });

  // Setup Docker event listeners for real-time updates
  setupDockerEventListeners(dockerService, windowManager);

  console.log('Docker IPC handlers setup complete');
}

// Setup Docker event listeners for real-time status updates
function setupDockerEventListeners(dockerService: DockerService, windowManager: WindowManager): void {
  // Listen for service status changes
  dockerService.on('serviceStatusChanged', (service, status, containerId, error) => {
    broadcastDockerServiceStatus(windowManager, {
      service,
      status,
      containerId,
      error,
    });
  });

  // Listen for container updates
  dockerService.on('containerUpdated', (containerInfo) => {
    const message: DockerContainerMessage = {
      containerId: containerInfo.containerId,
      status: containerInfo.status as any,
      name: containerInfo.name,
      image: containerInfo.image,
      ports: containerInfo.ports,
      health: containerInfo.health as any,
      updatedAt: new Date().toISOString(),
    };
    
    windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.DOCKER_CONTAINER_UPDATE, message);
  });

  // Listen for health check updates
  dockerService.on('healthCheckUpdated', (service, healthy, lastCheck, responseTime, error) => {
    const message: DockerHealthMessage = {
      service,
      healthy,
      lastCheck: new Date(lastCheck).toISOString(),
      responseTime,
      error
    };
    
    windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.DOCKER_HEALTH_CHECK, message);
  });

  // Listen for Docker errors
  dockerService.on('error', (err) => {
    console.error('Docker error event:', err);
    const error = err instanceof Error ? err : new Error(String(err));
    
    // Broadcast error to all windows
    windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.ERROR_OCCURRED, {
      code: 'DOCKER_ERROR',
      message: error.message || 'Unknown Docker error',
      details: err,
      stack: error.stack,
      timestamp: new Date().toISOString()
    });
  });
}

// Export helper functions for use by other modules
export { broadcastDockerServiceStatus, setupDockerEventListeners };
