// main/docker-service.ts - Docker container management
// Based on the electron-multi-gui-development.plan.md specifications

import Docker from 'dockerode';
import { EventEmitter } from 'events';
import { DOCKER_COMPOSE_FILES, SERVICE_NAMES } from '../shared/constants';
import { ServiceLevel } from '../shared/types';
import { isDevelopment } from '../shared/utils';

export interface DockerServiceStatus {
  service: string;
  status: 'starting' | 'running' | 'stopped' | 'error';
  containerId?: string;
  error?: string;
}

export interface DockerContainerInfo {
  containerId: string;
  status: string;
  name: string;
  image: string;
  ports: string[];
  health?: string;
  uptime: number;
}

export class DockerService extends EventEmitter {
  private docker: Docker;
  private isInitialized: boolean = false;
  private services: Map<string, DockerServiceStatus> = new Map();
  private containers: Map<string, DockerContainerInfo> = new Map();

  constructor() {
    super();
    this.docker = new Docker();
  }

  async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    try {
      console.log('Initializing Docker service...');
      
      // Test Docker connection
      await this.docker.ping();
      console.log('Docker connection established');
      
      // Load existing containers
      await this.loadExistingContainers();
      
      this.isInitialized = true;
      console.log('Docker service initialized');
    } catch (error) {
      console.error('Failed to initialize Docker service:', error);
      if (isDevelopment()) {
        console.warn('Continuing without Docker in development mode');
        this.isInitialized = true;
      } else {
        throw error;
      }
    }
  }

  async startServices(services: string[], level?: ServiceLevel): Promise<{
    success: boolean;
    started: string[];
    failed: Array<{ service: string; error: string }>;
  }> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const started: string[] = [];
    const failed: Array<{ service: string; error: string }> = [];

    try {
      console.log(`Starting services: ${services.join(', ')}`);
      
      for (const service of services) {
        try {
          await this.startService(service, level);
          started.push(service);
        } catch (error) {
          console.error(`Failed to start service ${service}:`, error);
          failed.push({
            service,
            error: error instanceof Error ? error.message : String(error),
          });
        }
      }

      return { success: failed.length === 0, started, failed };
    } catch (error) {
      console.error('Error starting services:', error);
      throw error;
    }
  }

  async stopServices(services: string[]): Promise<{
    success: boolean;
    stopped: string[];
    failed: Array<{ service: string; error: string }>;
  }> {
    const stopped: string[] = [];
    const failed: Array<{ service: string; error: string }> = [];

    try {
      console.log(`Stopping services: ${services.join(', ')}`);
      
      for (const service of services) {
        try {
          await this.stopService(service);
          stopped.push(service);
        } catch (error) {
          console.error(`Failed to stop service ${service}:`, error);
          failed.push({
            service,
            error: error instanceof Error ? error.message : String(error),
          });
        }
      }

      return { success: failed.length === 0, stopped, failed };
    } catch (error) {
      console.error('Error stopping services:', error);
      throw error;
    }
  }

  async restartServices(services: string[]): Promise<{
    success: boolean;
    started: string[];
    failed: Array<{ service: string; error: string }>;
  }> {
    try {
      console.log(`Restarting services: ${services.join(', ')}`);
      
      // Stop services first
      const stopResult = await this.stopServices(services);
      
      // Wait a moment
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Start services
      const startResult = await this.startServices(services);
      
      return {
        success: stopResult.success && startResult.success,
        started: startResult.started,
        failed: [...stopResult.failed, ...startResult.failed],
      };
    } catch (error) {
      console.error('Error restarting services:', error);
      throw error;
    }
  }

  async getServiceStatus(): Promise<{
    services: Array<{
      name: string;
      status: string;
      containerId?: string;
      image: string;
      ports: string[];
      health?: string;
      uptime: number;
    }>;
  }> {
    try {
      const containers = await this.docker.listContainers({ all: true });
      const services = containers.map(container => ({
        name: container.Names[0]?.replace('/', '') || 'unknown',
        status: container.State,
        containerId: container.Id,
        image: container.Image,
        ports: container.Ports.map(port => `${port.PrivatePort}:${port.PublicPort}`),
        health: container.Status.includes('healthy') ? 'healthy' : 'unhealthy',
        uptime: Math.floor((Date.now() - new Date(container.Created * 1000).getTime()) / 1000),
      }));

      return { services };
    } catch (error) {
      console.error('Error getting service status:', error);
      throw error;
    }
  }

  async getContainerLogs(containerId: string, lines?: number, follow?: boolean): Promise<{
    logs: string[];
    error?: string;
  }> {
    try {
      const container = this.docker.getContainer(containerId);
      const stream = await container.logs({
        stdout: true,
        stderr: true,
        tail: lines || 100,
        follow: follow || false,
        timestamps: true,
      });

      const logs: string[] = [];
      stream.on('data', (chunk) => {
        logs.push(chunk.toString());
      });

      return new Promise((resolve, reject) => {
        stream.on('end', () => resolve({ logs }));
        stream.on('error', (error) => reject({ logs: [], error: error.message }));
      });
    } catch (error) {
      console.error('Error getting container logs:', error);
      return { logs: [], error: error instanceof Error ? error.message : String(error) };
    }
  }

  async execCommand(
    containerId: string,
    command: string[],
    workingDir?: string,
    env?: Record<string, string>
  ): Promise<{
    success: boolean;
    output: string;
    error?: string;
    exitCode?: number;
  }> {
    try {
      const container = this.docker.getContainer(containerId);
      const exec = await container.exec({
        Cmd: command,
        WorkingDir: workingDir,
        Env: env ? Object.entries(env).map(([key, value]) => `${key}=${value}`) : undefined,
        AttachStdout: true,
        AttachStderr: true,
      });

      const stream = await exec.start({});
      let output = '';
      let errorOutput = '';

      return new Promise((resolve) => {
        stream.on('data', (chunk) => {
          const data = chunk.toString();
          if (chunk.stderr) {
            errorOutput += data;
          } else {
            output += data;
          }
        });

        stream.on('end', () => {
          resolve({
            success: errorOutput.length === 0,
            output,
            error: errorOutput || undefined,
            exitCode: 0,
          });
        });
      });
    } catch (error) {
      console.error('Error executing command:', error);
      return {
        success: false,
        output: '',
        error: error instanceof Error ? error.message : String(error),
        exitCode: 1,
      };
    }
  }

  async stop(): Promise<void> {
    try {
      console.log('Stopping Docker service...');
      
      // Stop all managed containers
      const containers = Array.from(this.containers.values());
      for (const container of containers) {
        try {
          await this.stopService(container.name);
        } catch (error) {
          console.error(`Error stopping container ${container.name}:`, error);
        }
      }
      
      this.services.clear();
      this.containers.clear();
      this.isInitialized = false;
      
      console.log('Docker service stopped');
    } catch (error) {
      console.error('Error stopping Docker service:', error);
      throw error;
    }
  }

  private async loadExistingContainers(): Promise<void> {
    try {
      const containers = await this.docker.listContainers({ all: true });
      
      for (const container of containers) {
        const containerInfo: DockerContainerInfo = {
          containerId: container.Id,
          status: container.State,
          name: container.Names[0]?.replace('/', '') || 'unknown',
          image: container.Image,
          ports: container.Ports.map(port => `${port.PrivatePort}:${port.PublicPort}`),
          health: container.Status.includes('healthy') ? 'healthy' : 'unhealthy',
          uptime: Math.floor((Date.now() - new Date(container.Created * 1000).getTime()) / 1000),
        };
        
        this.containers.set(containerInfo.name, containerInfo);
        
        const serviceStatus: DockerServiceStatus = {
          service: containerInfo.name,
          status: container.State === 'running' ? 'running' : 'stopped',
          containerId: container.Id,
        };
        
        this.services.set(containerInfo.name, serviceStatus);
      }
    } catch (error) {
      console.error('Error loading existing containers:', error);
    }
  }

  private async startService(service: string, level?: ServiceLevel): Promise<void> {
    try {
      console.log(`Starting service: ${service}`);
      
      // Check if service is already running
      const existingStatus = this.services.get(service);
      if (existingStatus?.status === 'running') {
        console.log(`Service ${service} is already running`);
        return;
      }
      
      // Update service status
      this.services.set(service, {
        service,
        status: 'starting',
      });
      
      this.emit('service-status', {
        service,
        status: 'starting',
      });
      
      // In a real implementation, this would start the actual Docker container
      // For now, we'll simulate the process
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Update service status to running
      this.services.set(service, {
        service,
        status: 'running',
        containerId: `mock-container-${service}`,
      });
      
      this.emit('service-status', {
        service,
        status: 'running',
        containerId: `mock-container-${service}`,
      });
      
      console.log(`Service ${service} started successfully`);
    } catch (error) {
      console.error(`Error starting service ${service}:`, error);
      
      this.services.set(service, {
        service,
        status: 'error',
        error: error instanceof Error ? error.message : String(error),
      });
      
      this.emit('service-status', {
        service,
        status: 'error',
        error: error instanceof Error ? error.message : String(error),
      });
      
      throw error;
    }
  }

  private async stopService(service: string): Promise<void> {
    try {
      console.log(`Stopping service: ${service}`);
      
      const serviceStatus = this.services.get(service);
      if (!serviceStatus || serviceStatus.status === 'stopped') {
        console.log(`Service ${service} is not running`);
        return;
      }
      
      // Update service status
      this.services.set(service, {
        service,
        status: 'stopped',
      });
      
      this.emit('service-status', {
        service,
        status: 'stopped',
      });
      
      // In a real implementation, this would stop the actual Docker container
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      console.log(`Service ${service} stopped successfully`);
    } catch (error) {
      console.error(`Error stopping service ${service}:`, error);
      
      this.services.set(service, {
        service,
        status: 'error',
        error: error instanceof Error ? error.message : String(error),
      });
      
      this.emit('service-status', {
        service,
        status: 'error',
        error: error instanceof Error ? error.message : String(error),
      });
      
      throw error;
    }
  }

  // Health monitoring
  startHealthMonitoring(): void {
    setInterval(async () => {
      try {
        await this.checkServiceHealth();
      } catch (error) {
        console.error('Health monitoring error:', error);
      }
    }, 30000); // Check every 30 seconds
  }

  private async checkServiceHealth(): Promise<void> {
    try {
      const containers = await this.docker.listContainers();
      
      for (const container of containers) {
        const serviceName = container.Names[0]?.replace('/', '') || 'unknown';
        const isHealthy = container.Status.includes('healthy') || container.Status.includes('Up');
        
        if (!isHealthy) {
          console.warn(`Service ${serviceName} is unhealthy`);
          
          this.emit('service-health', {
            service: serviceName,
            healthy: false,
            lastCheck: new Date().toISOString(),
            responseTime: 0,
          });
        }
      }
    } catch (error) {
      console.error('Health check error:', error);
    }
  }

  // Utility methods
  getServiceStatus(service: string): DockerServiceStatus | null {
    return this.services.get(service) || null;
  }

  getAllServices(): DockerServiceStatus[] {
    return Array.from(this.services.values());
  }

  getContainerInfo(containerId: string): DockerContainerInfo | null {
    return this.containers.get(containerId) || null;
  }

  getAllContainers(): DockerContainerInfo[] {
    return Array.from(this.containers.values());
  }

  isServiceRunning(service: string): boolean {
    const status = this.services.get(service);
    return status?.status === 'running';
  }

  isInitialized(): boolean {
    return this.isInitialized;
  }
}
