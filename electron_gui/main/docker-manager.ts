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

import { ipcMain } from 'electron';
import { spawn } from 'child_process';
import { EventEmitter } from 'events';
import path from 'path';
import { DOCKER_CONFIG } from '../shared/constants';

export interface DockerContainer {
  id: string;
  name: string;
  image: string;
  status: 'running' | 'stopped' | 'paused' | 'exited';
  ports: string[];
  created: string;
  size: string;
}

export interface DockerService {
  name: string;
  container: DockerContainer;
  health: 'healthy' | 'unhealthy' | 'starting' | 'unknown';
  phase: 'foundation' | 'core' | 'application' | 'support';
}

export interface DockerComposeService {
  name: string;
  status: 'running' | 'stopped' | 'restarting' | 'paused';
  health: 'healthy' | 'unhealthy' | 'starting' | 'unknown';
  ports: string[];
  restart_count: number;
}

export interface PiConnectionConfig {
  host: string;
  user: string;
  port: number;
  keyPath?: string;
  deployDir: string;
}

export class DockerManager extends EventEmitter {
  private piConfig: PiConnectionConfig;
  private isConnected: boolean = false;
  private services: Map<string, DockerService> = new Map();

  constructor(piConfig: PiConnectionConfig) {
    super();
    this.piConfig = piConfig;
    this.setupIpcHandlers();
  }

  /**
   * Setup IPC handlers for Docker operations
   */
  private setupIpcHandlers(): void {
    // Docker service management
    ipcMain.handle('docker:getServices', () => this.getServices());
    ipcMain.handle('docker:startService', (_, serviceName: string) => this.startService(serviceName));
    ipcMain.handle('docker:stopService', (_, serviceName: string) => this.stopService(serviceName));
    ipcMain.handle('docker:restartService', (_, serviceName: string) => this.restartService(serviceName));
    ipcMain.handle('docker:getServiceLogs', (_, serviceName: string, lines: number = 100) => this.getServiceLogs(serviceName, lines));
    ipcMain.handle('docker:getServiceHealth', (_, serviceName: string) => this.getServiceHealth(serviceName));

    // Docker Compose operations
    ipcMain.handle('docker:getComposeServices', () => this.getComposeServices());
    ipcMain.handle('docker:startCompose', (_, composeFile: string) => this.startCompose(composeFile));
    ipcMain.handle('docker:stopCompose', (_, composeFile: string) => this.stopCompose(composeFile));
    ipcMain.handle('docker:restartCompose', (_, composeFile: string) => this.restartCompose(composeFile));
    ipcMain.handle('docker:pullImages', (_, composeFile: string) => this.pullImages(composeFile));

    // Phase management
    ipcMain.handle('docker:startPhase', (_, phase: string) => this.startPhase(phase));
    ipcMain.handle('docker:stopPhase', (_, phase: string) => this.stopPhase(phase));
    ipcMain.handle('docker:getPhaseStatus', (_, phase: string) => this.getPhaseStatus(phase));

    // Connection management
    ipcMain.handle('docker:testConnection', () => this.testConnection());
    ipcMain.handle('docker:getConnectionStatus', () => this.getConnectionStatus());
  }

  /**
   * Test SSH connection to Raspberry Pi
   */
  async testConnection(): Promise<boolean> {
    try {
      const result = await this.executeSshCommand('docker --version');
      this.isConnected = result.success;
      this.emit('connectionStatus', this.isConnected);
      return this.isConnected;
    } catch (error) {
      console.error('Connection test failed:', error);
      this.isConnected = false;
      this.emit('connectionStatus', false);
      return false;
    }
  }

  /**
   * Get current connection status
   */
  getConnectionStatus(): boolean {
    return this.isConnected;
  }

  /**
   * Get all Docker services
   */
  async getServices(): Promise<DockerService[]> {
    if (!this.isConnected) {
      throw new Error('Not connected to Raspberry Pi');
    }

    try {
      const result = await this.executeSshCommand('docker ps -a --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.CreatedAt}}\t{{.Size}}"');
      
      if (!result.success) {
        throw new Error(`Failed to get services: ${result.error}`);
      }

      const services = this.parseDockerPsOutput(result.stdout);
      return services.map(container => this.mapContainerToService(container));
    } catch (error) {
      console.error('Error getting services:', error);
      throw error;
    }
  }

  /**
   * Start a Docker service
   */
  async startService(serviceName: string): Promise<boolean> {
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
    } catch (error) {
      console.error(`Error starting service ${serviceName}:`, error);
      throw error;
    }
  }

  /**
   * Stop a Docker service
   */
  async stopService(serviceName: string): Promise<boolean> {
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
    } catch (error) {
      console.error(`Error stopping service ${serviceName}:`, error);
      throw error;
    }
  }

  /**
   * Restart a Docker service
   */
  async restartService(serviceName: string): Promise<boolean> {
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
    } catch (error) {
      console.error(`Error restarting service ${serviceName}:`, error);
      throw error;
    }
  }

  /**
   * Get service logs
   */
  async getServiceLogs(serviceName: string, lines: number = 100): Promise<string> {
    if (!this.isConnected) {
      throw new Error('Not connected to Raspberry Pi');
    }

    try {
      const result = await this.executeSshCommand(`docker logs --tail ${lines} ${serviceName}`);
      return result.stdout;
    } catch (error) {
      console.error(`Error getting logs for ${serviceName}:`, error);
      throw error;
    }
  }

  /**
   * Get service health status
   */
  async getServiceHealth(serviceName: string): Promise<string> {
    if (!this.isConnected) {
      throw new Error('Not connected to Raspberry Pi');
    }

    try {
      const result = await this.executeSshCommand(`docker inspect --format='{{.State.Health.Status}}' ${serviceName}`);
      return result.stdout.trim();
    } catch (error) {
      console.error(`Error getting health for ${serviceName}:`, error);
      return 'unknown';
    }
  }

  /**
   * Get Docker Compose services
   */
  async getComposeServices(): Promise<DockerComposeService[]> {
    if (!this.isConnected) {
      throw new Error('Not connected to Raspberry Pi');
    }

    try {
      const result = await this.executeSshCommand('docker-compose ps --format json');
      
      if (!result.success) {
        throw new Error(`Failed to get compose services: ${result.error}`);
      }

      const services = JSON.parse(result.stdout);
      return services.map((service: any) => ({
        name: service.Name,
        status: service.State,
        health: service.Health || 'unknown',
        ports: service.Ports ? service.Ports.split(',').map((p: string) => p.trim()) : [],
        restart_count: parseInt(service.RestartCount) || 0
      }));
    } catch (error) {
      console.error('Error getting compose services:', error);
      throw error;
    }
  }

  /**
   * Start Docker Compose services
   */
  async startCompose(composeFile: string): Promise<boolean> {
    if (!this.isConnected) {
      throw new Error('Not connected to Raspberry Pi');
    }

    try {
      const composePath = path.join(this.piConfig.deployDir, composeFile);
      const result = await this.executeSshCommand(`cd ${this.piConfig.deployDir} && docker-compose -f ${composeFile} up -d`);
      return result.success;
    } catch (error) {
      console.error(`Error starting compose ${composeFile}:`, error);
      throw error;
    }
  }

  /**
   * Stop Docker Compose services
   */
  async stopCompose(composeFile: string): Promise<boolean> {
    if (!this.isConnected) {
      throw new Error('Not connected to Raspberry Pi');
    }

    try {
      const result = await this.executeSshCommand(`cd ${this.piConfig.deployDir} && docker-compose -f ${composeFile} down`);
      return result.success;
    } catch (error) {
      console.error(`Error stopping compose ${composeFile}:`, error);
      throw error;
    }
  }

  /**
   * Restart Docker Compose services
   */
  async restartCompose(composeFile: string): Promise<boolean> {
    if (!this.isConnected) {
      throw new Error('Not connected to Raspberry Pi');
    }

    try {
      const result = await this.executeSshCommand(`cd ${this.piConfig.deployDir} && docker-compose -f ${composeFile} restart`);
      return result.success;
    } catch (error) {
      console.error(`Error restarting compose ${composeFile}:`, error);
      throw error;
    }
  }

  /**
   * Pull Docker images for compose file
   */
  async pullImages(composeFile: string): Promise<boolean> {
    if (!this.isConnected) {
      throw new Error('Not connected to Raspberry Pi');
    }

    try {
      const result = await this.executeSshCommand(`cd ${this.piConfig.deployDir} && docker-compose -f ${composeFile} pull`);
      return result.success;
    } catch (error) {
      console.error(`Error pulling images for ${composeFile}:`, error);
      throw error;
    }
  }

  /**
   * Start a specific phase
   */
  async startPhase(phase: string): Promise<boolean> {
    const phaseFiles = {
      'foundation': 'docker-compose.foundation.yml',
      'core': 'docker-compose.core.yml',
      'application': 'docker-compose.application.yml',
      'support': 'docker-compose.support.yml'
    };

    const composeFile = phaseFiles[phase as keyof typeof phaseFiles];
    if (!composeFile) {
      throw new Error(`Unknown phase: ${phase}`);
    }

    return this.startCompose(composeFile);
  }

  /**
   * Stop a specific phase
   */
  async stopPhase(phase: string): Promise<boolean> {
    const phaseFiles = {
      'foundation': 'docker-compose.foundation.yml',
      'core': 'docker-compose.core.yml',
      'application': 'docker-compose.application.yml',
      'support': 'docker-compose.support.yml'
    };

    const composeFile = phaseFiles[phase as keyof typeof phaseFiles];
    if (!composeFile) {
      throw new Error(`Unknown phase: ${phase}`);
    }

    return this.stopCompose(composeFile);
  }

  /**
   * Get phase status
   */
  async getPhaseStatus(phase: string): Promise<DockerComposeService[]> {
    const phaseFiles = {
      'foundation': 'docker-compose.foundation.yml',
      'core': 'docker-compose.core.yml',
      'application': 'docker-compose.application.yml',
      'support': 'docker-compose.support.yml'
    };

    const composeFile = phaseFiles[phase as keyof typeof phaseFiles];
    if (!composeFile) {
      throw new Error(`Unknown phase: ${phase}`);
    }

    try {
      const result = await this.executeSshCommand(`cd ${this.piConfig.deployDir} && docker-compose -f ${composeFile} ps --format json`);
      
      if (!result.success) {
        return [];
      }

      const services = JSON.parse(result.stdout);
      return services.map((service: any) => ({
        name: service.Name,
        status: service.State,
        health: service.Health || 'unknown',
        ports: service.Ports ? service.Ports.split(',').map((p: string) => p.trim()) : [],
        restart_count: parseInt(service.RestartCount) || 0
      }));
    } catch (error) {
      console.error(`Error getting phase status for ${phase}:`, error);
      return [];
    }
  }

  /**
   * Execute SSH command on Raspberry Pi
   */
  private async executeSshCommand(command: string): Promise<{ success: boolean; stdout: string; stderr: string }> {
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

      const sshProcess = spawn('ssh', sshArgs);
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
  private parseDockerPsOutput(output: string): DockerContainer[] {
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
  private parseContainerStatus(statusStr: string): 'running' | 'stopped' | 'paused' | 'exited' {
    if (statusStr.includes('Up')) return 'running';
    if (statusStr.includes('Exited')) return 'exited';
    if (statusStr.includes('Paused')) return 'paused';
    return 'stopped';
  }

  /**
   * Map container to service with phase information
   */
  private mapContainerToService(container: DockerContainer): DockerService {
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
  private determineServicePhase(containerName: string): 'foundation' | 'core' | 'application' | 'support' {
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
  private determineServiceHealth(status: string): 'healthy' | 'unhealthy' | 'starting' | 'unknown' {
    if (status === 'running') return 'healthy';
    if (status === 'exited') return 'unhealthy';
    if (status === 'paused') return 'unhealthy';
    return 'starting';
  }
}

// Default configuration for Raspberry Pi
export const defaultPiConfig: PiConnectionConfig = {
  host: DOCKER_CONFIG.PI_HOST,
  user: DOCKER_CONFIG.SSH_USER,
  port: DOCKER_CONFIG.SSH_PORT,
  deployDir: DOCKER_CONFIG.DEPLOY_DIR
};

export default DockerManager;
