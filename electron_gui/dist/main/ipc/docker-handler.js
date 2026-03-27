"use strict";
// main/ipc/docker-handler.ts - Docker IPC handlers
// Based on the electron-multi-gui-development.plan.md specifications
Object.defineProperty(exports, "__esModule", { value: true });
exports.setupDockerEventListeners = exports.broadcastDockerServiceStatus = exports.setupDockerHandlers = void 0;
const electron_1 = require("electron");
const ipc_channels_1 = require("../../shared/ipc-channels");
function broadcastDockerServiceStatus(windowManager, status) {
    const message = {
        ...status,
        timestamp: new Date().toISOString(),
    };
    windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.DOCKER_SERVICE_STATUS, message);
}
exports.broadcastDockerServiceStatus = broadcastDockerServiceStatus;
function setupDockerHandlers(dockerService, windowManager) {
    console.log('Setting up Docker IPC handlers...');
    // Start Docker services handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_START_SERVICES, async (event, request) => {
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
            };
        }
        catch (error) {
            console.error('Docker start services error:', error);
            return {
                success: false,
                started: [],
                failed: [{
                        service: 'unknown',
                        error: error instanceof Error ? error.message : 'Unknown start error'
                    }]
            };
        }
    });
    // Stop Docker services handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_STOP_SERVICES, async (event, request) => {
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
            };
        }
        catch (error) {
            console.error('Docker stop services error:', error);
            return {
                success: false,
                stopped: [],
                failed: [{
                        service: 'unknown',
                        error: error instanceof Error ? error.message : 'Unknown stop error'
                    }]
            };
        }
    });
    // Restart Docker services handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_RESTART_SERVICES, async (event, { services }) => {
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
            };
        }
        catch (error) {
            console.error('Docker restart services error:', error);
            return {
                success: false,
                started: [],
                failed: [{
                        service: 'unknown',
                        error: error instanceof Error ? error.message : 'Unknown restart error'
                    }]
            };
        }
    });
    // Get Docker service status handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_SERVICE_STATUS, async (event, serviceName) => {
        try {
            console.log(`Getting Docker service status${serviceName ? ` for: ${serviceName}` : ' for all services'}`);
            // Get service status using DockerService
            const result = await dockerService.getOrchestratedServiceStatus();
            return result;
        }
        catch (error) {
            console.error('Docker get service status error:', error);
            return {
                services: [],
                generatedAt: new Date().toISOString(),
            };
        }
    });
    // Get Docker container logs handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_CONTAINER_LOGS, async (event, request) => {
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
            };
        }
        catch (error) {
            console.error('Docker get container logs error:', error);
            return {
                containerId: request.containerId,
                logs: [],
                error: error instanceof Error ? error.message : 'Unknown logs error',
                generatedAt: new Date().toISOString(),
            };
        }
    });
    // Execute command in Docker container handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.DOCKER_EXEC_COMMAND, async (event, request) => {
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
            };
        }
        catch (error) {
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
            };
        }
    });
    // Setup Docker event listeners for real-time updates
    setupDockerEventListeners(dockerService, windowManager);
    console.log('Docker IPC handlers setup complete');
}
exports.setupDockerHandlers = setupDockerHandlers;
// Setup Docker event listeners for real-time status updates
function setupDockerEventListeners(dockerService, windowManager) {
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
        const message = {
            containerId: containerInfo.containerId,
            status: containerInfo.status,
            name: containerInfo.name,
            image: containerInfo.image,
            ports: containerInfo.ports,
            health: containerInfo.health,
            updatedAt: new Date().toISOString(),
        };
        windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.DOCKER_CONTAINER_UPDATE, message);
    });
    // Listen for health check updates
    dockerService.on('healthCheckUpdated', (service, healthy, lastCheck, responseTime, error) => {
        const message = {
            service,
            healthy,
            lastCheck: new Date(lastCheck).toISOString(),
            responseTime,
            error
        };
        windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.DOCKER_HEALTH_CHECK, message);
    });
    // Listen for Docker errors
    dockerService.on('error', (err) => {
        console.error('Docker error event:', err);
        const error = err instanceof Error ? err : new Error(String(err));
        // Broadcast error to all windows
        windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.ERROR_OCCURRED, {
            code: 'DOCKER_ERROR',
            message: error.message || 'Unknown Docker error',
            details: err,
            stack: error.stack,
            timestamp: new Date().toISOString()
        });
    });
}
exports.setupDockerEventListeners = setupDockerEventListeners;
