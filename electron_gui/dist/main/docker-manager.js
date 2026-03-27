"use strict";
/**
 * Docker Service Manager for Electron GUI
 *
 * Manages Docker container lifecycle operations for Lucid backend services
 * Communicates with Raspberry Pi via SSH for container management
 *
 * @file docker-manager.ts
 * @author LUCID Project Team
 * @version 1.0.0
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultPiConfig = exports.DockerManager = void 0;
const electron_1 = require("electron");
const child_process_1 = require("child_process");
const events_1 = require("events");
const path_1 = __importDefault(require("path"));
const constants_1 = require("../shared/constants");
class DockerManager extends events_1.EventEmitter {
    constructor(piConfig) {
        super();
        this.isConnected = false;
        this.services = new Map();
        this.piConfig = piConfig;
        this.setupIpcHandlers();
    }
    /**
     * Setup IPC handlers for Docker operations
     */
    setupIpcHandlers() {
        // Docker service management
        electron_1.ipcMain.handle('docker:getServices', () => this.getServices());
        electron_1.ipcMain.handle('docker:startService', (_, serviceName) => this.startService(serviceName));
        electron_1.ipcMain.handle('docker:stopService', (_, serviceName) => this.stopService(serviceName));
        electron_1.ipcMain.handle('docker:restartService', (_, serviceName) => this.restartService(serviceName));
        electron_1.ipcMain.handle('docker:getServiceLogs', (_, serviceName, lines = 100) => this.getServiceLogs(serviceName, lines));
        electron_1.ipcMain.handle('docker:getServiceHealth', (_, serviceName) => this.getServiceHealth(serviceName));
        // Docker Compose operations
        electron_1.ipcMain.handle('docker:getComposeServices', () => this.getComposeServices());
        electron_1.ipcMain.handle('docker:startCompose', (_, composeFile) => this.startCompose(composeFile));
        electron_1.ipcMain.handle('docker:stopCompose', (_, composeFile) => this.stopCompose(composeFile));
        electron_1.ipcMain.handle('docker:restartCompose', (_, composeFile) => this.restartCompose(composeFile));
        electron_1.ipcMain.handle('docker:pullImages', (_, composeFile) => this.pullImages(composeFile));
        // Phase management
        electron_1.ipcMain.handle('docker:startPhase', (_, phase) => this.startPhase(phase));
        electron_1.ipcMain.handle('docker:stopPhase', (_, phase) => this.stopPhase(phase));
        electron_1.ipcMain.handle('docker:getPhaseStatus', (_, phase) => this.getPhaseStatus(phase));
        // Connection management
        electron_1.ipcMain.handle('docker:testConnection', () => this.testConnection());
        electron_1.ipcMain.handle('docker:getConnectionStatus', () => this.getConnectionStatus());
    }
    /**
     * Test SSH connection to Raspberry Pi
     */
    async testConnection() {
        try {
            const result = await this.executeSshCommand('docker --version');
            this.isConnected = result.success;
            this.emit('connectionStatus', this.isConnected);
            return this.isConnected;
        }
        catch (error) {
            console.error('Connection test failed:', error);
            this.isConnected = false;
            this.emit('connectionStatus', false);
            return false;
        }
    }
    /**
     * Get current connection status
     */
    getConnectionStatus() {
        return this.isConnected;
    }
    /**
     * Get all Docker services
     */
    async getServices() {
        if (!this.isConnected) {
            throw new Error('Not connected to Raspberry Pi');
        }
        try {
            const result = await this.executeSshCommand('docker ps -a --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.CreatedAt}}\t{{.Size}}"');
            if (!result.success) {
                throw new Error(`Failed to get services: ${result.stderr}`);
            }
            const services = this.parseDockerPsOutput(result.stdout);
            return services.map(container => this.mapContainerToService(container));
        }
        catch (error) {
            console.error('Error getting services:', error);
            throw error;
        }
    }
    /**
     * Start a Docker service
     */
    async startService(serviceName) {
        if (!this.isConnected) {
            throw new Error('Not connected to Raspberry Pi');
        }
        try {
            const result = await this.executeSshCommand(`docker start ${serviceName}`);
            if (result.success) {
                this.emit('serviceStatusChanged', { name: serviceName, status: 'running' });
                return true;
            }
            return false;
        }
        catch (error) {
            console.error(`Error starting service ${serviceName}:`, error);
            throw error;
        }
    }
    /**
     * Stop a Docker service
     */
    async stopService(serviceName) {
        if (!this.isConnected) {
            throw new Error('Not connected to Raspberry Pi');
        }
        try {
            const result = await this.executeSshCommand(`docker stop ${serviceName}`);
            if (result.success) {
                this.emit('serviceStatusChanged', { name: serviceName, status: 'stopped' });
                return true;
            }
            return false;
        }
        catch (error) {
            console.error(`Error stopping service ${serviceName}:`, error);
            throw error;
        }
    }
    /**
     * Restart a Docker service
     */
    async restartService(serviceName) {
        if (!this.isConnected) {
            throw new Error('Not connected to Raspberry Pi');
        }
        try {
            const result = await this.executeSshCommand(`docker restart ${serviceName}`);
            if (result.success) {
                this.emit('serviceStatusChanged', { name: serviceName, status: 'running' });
                return true;
            }
            return false;
        }
        catch (error) {
            console.error(`Error restarting service ${serviceName}:`, error);
            throw error;
        }
    }
    /**
     * Get service logs
     */
    async getServiceLogs(serviceName, lines = 100) {
        if (!this.isConnected) {
            throw new Error('Not connected to Raspberry Pi');
        }
        try {
            const result = await this.executeSshCommand(`docker logs --tail ${lines} ${serviceName}`);
            return result.stdout;
        }
        catch (error) {
            console.error(`Error getting logs for ${serviceName}:`, error);
            throw error;
        }
    }
    /**
     * Get service health status
     */
    async getServiceHealth(serviceName) {
        if (!this.isConnected) {
            throw new Error('Not connected to Raspberry Pi');
        }
        try {
            const result = await this.executeSshCommand(`docker inspect --format='{{.State.Health.Status}}' ${serviceName}`);
            return result.stdout.trim();
        }
        catch (error) {
            console.error(`Error getting health for ${serviceName}:`, error);
            return 'unknown';
        }
    }
    /**
     * Get Docker Compose services
     */
    async getComposeServices() {
        if (!this.isConnected) {
            throw new Error('Not connected to Raspberry Pi');
        }
        try {
            const result = await this.executeSshCommand('docker-compose ps --format json');
            if (!result.success) {
                throw new Error(`Failed to get compose services: ${result.stderr}`);
            }
            const services = JSON.parse(result.stdout);
            return services.map((service) => ({
                name: service.Name,
                status: service.State,
                health: service.Health || 'unknown',
                ports: service.Ports ? service.Ports.split(',').map((p) => p.trim()) : [],
                restart_count: parseInt(service.RestartCount) || 0
            }));
        }
        catch (error) {
            console.error('Error getting compose services:', error);
            throw error;
        }
    }
    /**
     * Start Docker Compose services
     */
    async startCompose(composeFile) {
        if (!this.isConnected) {
            throw new Error('Not connected to Raspberry Pi');
        }
        try {
            const composePath = path_1.default.join(this.piConfig.deployDir, composeFile);
            const result = await this.executeSshCommand(`cd ${this.piConfig.deployDir} && docker-compose -f ${composeFile} up -d`);
            return result.success;
        }
        catch (error) {
            console.error(`Error starting compose ${composeFile}:`, error);
            throw error;
        }
    }
    /**
     * Stop Docker Compose services
     */
    async stopCompose(composeFile) {
        if (!this.isConnected) {
            throw new Error('Not connected to Raspberry Pi');
        }
        try {
            const result = await this.executeSshCommand(`cd ${this.piConfig.deployDir} && docker-compose -f ${composeFile} down`);
            return result.success;
        }
        catch (error) {
            console.error(`Error stopping compose ${composeFile}:`, error);
            throw error;
        }
    }
    /**
     * Restart Docker Compose services
     */
    async restartCompose(composeFile) {
        if (!this.isConnected) {
            throw new Error('Not connected to Raspberry Pi');
        }
        try {
            const result = await this.executeSshCommand(`cd ${this.piConfig.deployDir} && docker-compose -f ${composeFile} restart`);
            return result.success;
        }
        catch (error) {
            console.error(`Error restarting compose ${composeFile}:`, error);
            throw error;
        }
    }
    /**
     * Pull Docker images for compose file
     */
    async pullImages(composeFile) {
        if (!this.isConnected) {
            throw new Error('Not connected to Raspberry Pi');
        }
        try {
            const result = await this.executeSshCommand(`cd ${this.piConfig.deployDir} && docker-compose -f ${composeFile} pull`);
            return result.success;
        }
        catch (error) {
            console.error(`Error pulling images for ${composeFile}:`, error);
            throw error;
        }
    }
    /**
     * Start a specific phase
     */
    async startPhase(phase) {
        const phaseFiles = {
            'foundation': 'docker-compose.foundation.yml',
            'core': 'docker-compose.core.yml',
            'application': 'docker-compose.application.yml',
            'support': 'docker-compose.support.yml'
        };
        const composeFile = phaseFiles[phase];
        if (!composeFile) {
            throw new Error(`Unknown phase: ${phase}`);
        }
        return this.startCompose(composeFile);
    }
    /**
     * Stop a specific phase
     */
    async stopPhase(phase) {
        const phaseFiles = {
            'foundation': 'docker-compose.foundation.yml',
            'core': 'docker-compose.core.yml',
            'application': 'docker-compose.application.yml',
            'support': 'docker-compose.support.yml'
        };
        const composeFile = phaseFiles[phase];
        if (!composeFile) {
            throw new Error(`Unknown phase: ${phase}`);
        }
        return this.stopCompose(composeFile);
    }
    /**
     * Get phase status
     */
    async getPhaseStatus(phase) {
        const phaseFiles = {
            'foundation': 'docker-compose.foundation.yml',
            'core': 'docker-compose.core.yml',
            'application': 'docker-compose.application.yml',
            'support': 'docker-compose.support.yml'
        };
        const composeFile = phaseFiles[phase];
        if (!composeFile) {
            throw new Error(`Unknown phase: ${phase}`);
        }
        try {
            const result = await this.executeSshCommand(`cd ${this.piConfig.deployDir} && docker-compose -f ${composeFile} ps --format json`);
            if (!result.success) {
                return [];
            }
            const services = JSON.parse(result.stdout);
            return services.map((service) => ({
                name: service.Name,
                status: service.State,
                health: service.Health || 'unknown',
                ports: service.Ports ? service.Ports.split(',').map((p) => p.trim()) : [],
                restart_count: parseInt(service.RestartCount) || 0
            }));
        }
        catch (error) {
            console.error(`Error getting phase status for ${phase}:`, error);
            return [];
        }
    }
    /**
     * Execute SSH command on Raspberry Pi
     */
    async executeSshCommand(command) {
        return new Promise((resolve) => {
            const sshArgs = [
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'ConnectTimeout=10',
                `${this.piConfig.user}@${this.piConfig.host}`,
                command
            ];
            if (this.piConfig.keyPath) {
                sshArgs.unshift('-i', this.piConfig.keyPath);
            }
            const sshProcess = (0, child_process_1.spawn)('ssh', sshArgs);
            let stdout = '';
            let stderr = '';
            sshProcess.stdout.on('data', (data) => {
                stdout += data.toString();
            });
            sshProcess.stderr.on('data', (data) => {
                stderr += data.toString();
            });
            sshProcess.on('close', (code) => {
                resolve({
                    success: code === 0,
                    stdout,
                    stderr
                });
            });
            sshProcess.on('error', (error) => {
                resolve({
                    success: false,
                    stdout: '',
                    stderr: error.message
                });
            });
        });
    }
    /**
     * Parse Docker ps output
     */
    parseDockerPsOutput(output) {
        const lines = output.trim().split('\n').slice(1); // Skip header
        return lines.map(line => {
            const parts = line.split('\t');
            return {
                id: parts[0],
                name: parts[1],
                image: parts[2],
                status: this.parseContainerStatus(parts[3]),
                ports: parts[4] ? parts[4].split(',') : [],
                created: parts[5],
                size: parts[6]
            };
        });
    }
    /**
     * Parse container status string
     */
    parseContainerStatus(statusStr) {
        if (statusStr.includes('Up'))
            return 'running';
        if (statusStr.includes('Exited'))
            return 'exited';
        if (statusStr.includes('Paused'))
            return 'paused';
        return 'stopped';
    }
    /**
     * Map container to service with phase information
     */
    mapContainerToService(container) {
        const phase = this.determineServicePhase(container.name);
        return {
            name: container.name,
            container,
            health: this.determineServiceHealth(container.status),
            phase
        };
    }
    /**
     * Determine service phase based on container name
     */
    determineServicePhase(containerName) {
        if (containerName.includes('mongodb') || containerName.includes('redis') || containerName.includes('elasticsearch') || containerName.includes('auth')) {
            return 'foundation';
        }
        if (containerName.includes('api-gateway') || containerName.includes('blockchain') || containerName.includes('service-mesh')) {
            return 'core';
        }
        if (containerName.includes('session') || containerName.includes('rdp') || containerName.includes('node')) {
            return 'application';
        }
        if (containerName.includes('admin') || containerName.includes('tron') || containerName.includes('payment')) {
            return 'support';
        }
        return 'core'; // Default fallback
    }
    /**
     * Determine service health based on container status
     */
    determineServiceHealth(status) {
        if (status === 'running')
            return 'healthy';
        if (status === 'exited')
            return 'unhealthy';
        if (status === 'paused')
            return 'unhealthy';
        return 'starting';
    }
}
exports.DockerManager = DockerManager;
// Default configuration for Raspberry Pi
exports.defaultPiConfig = {
    host: constants_1.DOCKER_CONFIG.PI_HOST,
    user: constants_1.DOCKER_CONFIG.SSH_USER,
    port: constants_1.DOCKER_CONFIG.SSH_PORT,
    deployDir: constants_1.DOCKER_CONFIG.DEPLOY_DIR
};
exports.default = DockerManager;
