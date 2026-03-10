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
          const serviceStatus = dockerService.getServiceStatus(serviceName);
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
      } as DockerStartServicesResponse;
    } catch (error) {
      console.error('Docker start services error:', error);
      
      return {
        success: false,
        started: [],
        failed: [{
          service: 'unknown',
          error: error instanceof Error ? error.message : 'Unknown start error'
        }]
      } as DockerStartServicesResponse;
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
      } as DockerStopServicesResponse;
    } catch (error) {
      console.error('Docker stop services error:', error);
      
      return {
        success: false,
        stopped: [],
        failed: [{
          service: 'unknown',
          error: error instanceof Error ? error.message : 'Unknown stop error'
        }]
      } as DockerStopServicesResponse;
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
          const serviceStatus = dockerService.getServiceStatus(serviceName);
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
      } as DockerStartServicesResponse;
    } catch (error) {
      console.error('Docker restart services error:', error);
      
      return {
        success: false,
        started: [],
        failed: [{
          service: 'unknown',
          error: error instanceof Error ? error.message : 'Unknown restart error'
        }]
      } as DockerStartServicesResponse;
    }
  });

  // Get Docker service status handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_SERVICE_STATUS, async (event, serviceName?: string) => {
    try {
      console.log(`Getting Docker service status${serviceName ? ` for: ${serviceName}` : ' for all services'}`);
      
      // Get service status using DockerService
      const result = await dockerService.getServiceStatus();
      
      return {
        services: result.services.map(service => ({
          name: service.name,
          status: service.status,
          containerId: service.containerId,
          image: service.image,
          ports: service.ports,
          health: service.health,
          uptime: service.uptime
        }))
      } as DockerGetServiceStatusResponse;
    } catch (error) {
      console.error('Docker get service status error:', error);
      
      return {
        services: []
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
        logs: result.logs,
        error: result.error
      } as DockerGetContainerLogsResponse;
    } catch (error) {
      console.error('Docker get container logs error:', error);
      
      return {
        logs: [],
        error: error instanceof Error ? error.message : 'Unknown logs error'
      } as DockerGetContainerLogsResponse;
    }
  });

  // Execute command in Docker container handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.DOCKER_EXEC_COMMAND, async (event, request: DockerExecCommandRequest) => {
    try {
      const { containerId, command, workingDir, env } = request;
      
      console.log(`Executing command in Docker container: ${containerId}, command: ${command.join(' ')}`);
      
      // Execute command using DockerService
      const result = await dockerService.execCommand(containerId, command, workingDir, env);
      
      return {
        success: result.success,
        output: result.output,
        error: result.error,
        exitCode: result.exitCode
      } as DockerExecCommandResponse;
    } catch (error) {
      console.error('Docker exec command error:', error);
      
      return {
        success: false,
        output: '',
        error: error instanceof Error ? error.message : 'Unknown exec error',
        exitCode: -1
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
    const message: DockerServiceMessage = {
      service,
      status,
      containerId,
      error
    };
    
    broadcastDockerServiceStatus(windowManager, message);
  });

  // Listen for container updates
  dockerService.on('containerUpdated', (containerInfo) => {
    const message: DockerContainerMessage = {
      containerId: containerInfo.containerId,
      status: containerInfo.status as any,
      name: containerInfo.name,
      image: containerInfo.image,
      ports: containerInfo.ports,
      health: containerInfo.health as any
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
  dockerService.on('error', (error) => {
    console.error('Docker error event:', error);
    
    // Broadcast error to all windows
    windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.ERROR_OCCURRED, {
      code: 'DOCKER_ERROR',
      message: error.message || 'Unknown Docker error',
      details: error,
      stack: error.stack,
      timestamp: new Date().toISOString()
    });
  });
}

// Helper function to broadcast Docker service status updates
function broadcastDockerServiceStatus(windowManager: WindowManager, status: DockerServiceMessage): void {
  windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.DOCKER_SERVICE_STATUS, status);
}

// Export helper functions for use by other modules
export { broadcastDockerServiceStatus, setupDockerEventListeners };
