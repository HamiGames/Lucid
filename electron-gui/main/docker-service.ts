/**
 * LUCID Docker Service - SPEC-1B Implementation
 * Manages Docker containers for Pi backend services
 */

import { spawn, ChildProcess } from 'child_process';
import * as net from 'net';

export interface ContainerInfo {
  id: string;
  name: string;
  image: string;
  status: 'running' | 'stopped' | 'paused' | 'restarting' | 'dead' | 'created';
  state: string;
  ports: string[];
  created: string;
  command: string;
  labels: Record<string, string>;
}

export interface ContainerStats {
  id: string;
  name: string;
  cpu_percent: number;
  memory_usage: number;
  memory_limit: number;
  memory_percent: number;
  network_rx: number;
  network_tx: number;
  block_read: number;
  block_write: number;
  pids: number;
  timestamp: string;
}

export interface DockerStatus {
  connected: boolean;
  version?: string;
  api_version?: string;
  arch?: string;
  os?: string;
  containers?: number;
  images?: number;
  error?: string;
}

export interface SSHConfig {
  host: string;
  port: number;
  username: string;
  keyPath?: string;
  password?: string;
}

export class DockerService {
  private status: DockerStatus;
  private sshConfig: SSHConfig | null = null;
  private isConnected = false;

  constructor() {
    this.status = {
      connected: false
    };
  }

  async initialize(): Promise<void> {
    try {
      console.log('Initializing Docker Service...');

      // Check if Docker is available locally
      const localDocker = await this.checkLocalDocker();
      
      if (localDocker) {
        console.log('Local Docker available');
        this.isConnected = true;
        this.status.connected = true;
        await this.getDockerInfo();
      } else {
        console.log('Local Docker not available, will use SSH connection');
        this.status.connected = false;
      }

      console.log('Docker Service initialized successfully');

    } catch (error) {
      console.error('Failed to initialize Docker Service:', error);
      throw error;
    }
  }

  async connectSSH(config: SSHConfig): Promise<boolean> {
    try {
      console.log(`Connecting to Docker via SSH: ${config.username}@${config.host}:${config.port}`);

      this.sshConfig = config;

      // Test SSH connection
      const isConnected = await this.testSSHConnection();
      
      if (isConnected) {
        this.isConnected = true;
        this.status.connected = true;
        console.log('SSH connection to Docker successful');
        
        // Get Docker info via SSH
        await this.getDockerInfoSSH();
        
        return true;
      } else {
        this.status.error = 'Failed to connect via SSH';
        return false;
      }

    } catch (error) {
      console.error('Failed to connect to Docker via SSH:', error);
      this.status.error = error.message;
      return false;
    }
  }

  async getContainers(): Promise<ContainerInfo[]> {
    try {
      if (!this.isConnected) {
        throw new Error('Docker service not connected');
      }

      const command = 'docker ps -a --format "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.State}}\t{{.Ports}}\t{{.CreatedAt}}\t{{.Command}}\t{{.Labels}}"';
      const output = await this.executeDockerCommand(command);
      
      return this.parseContainerList(output);

    } catch (error) {
      console.error('Failed to get containers:', error);
      throw error;
    }
  }

  async getContainer(containerId: string): Promise<ContainerInfo | null> {
    try {
      const containers = await this.getContainers();
      return containers.find(c => c.id === containerId) || null;

    } catch (error) {
      console.error(`Failed to get container ${containerId}:`, error);
      return null;
    }
  }

  async startContainer(containerId: string): Promise<boolean> {
    try {
      if (!this.isConnected) {
        throw new Error('Docker service not connected');
      }

      console.log(`Starting container ${containerId}...`);

      const command = `docker start ${containerId}`;
      await this.executeDockerCommand(command);

      console.log(`Container ${containerId} started successfully`);
      return true;

    } catch (error) {
      console.error(`Failed to start container ${containerId}:`, error);
      return false;
    }
  }

  async stopContainer(containerId: string): Promise<boolean> {
    try {
      if (!this.isConnected) {
        throw new Error('Docker service not connected');
      }

      console.log(`Stopping container ${containerId}...`);

      const command = `docker stop ${containerId}`;
      await this.executeDockerCommand(command);

      console.log(`Container ${containerId} stopped successfully`);
      return true;

    } catch (error) {
      console.error(`Failed to stop container ${containerId}:`, error);
      return false;
    }
  }

  async restartContainer(containerId: string): Promise<boolean> {
    try {
      if (!this.isConnected) {
        throw new Error('Docker service not connected');
      }

      console.log(`Restarting container ${containerId}...`);

      const command = `docker restart ${containerId}`;
      await this.executeDockerCommand(command);

      console.log(`Container ${containerId} restarted successfully`);
      return true;

    } catch (error) {
      console.error(`Failed to restart container ${containerId}:`, error);
      return false;
    }
  }

  async removeContainer(containerId: string, force: boolean = false): Promise<boolean> {
    try {
      if (!this.isConnected) {
        throw new Error('Docker service not connected');
      }

      console.log(`Removing container ${containerId}...`);

      const command = `docker rm ${force ? '-f ' : ''}${containerId}`;
      await this.executeDockerCommand(command);

      console.log(`Container ${containerId} removed successfully`);
      return true;

    } catch (error) {
      console.error(`Failed to remove container ${containerId}:`, error);
      return false;
    }
  }

  async getContainerLogs(containerId: string, lines: number = 100): Promise<string[]> {
    try {
      if (!this.isConnected) {
        throw new Error('Docker service not connected');
      }

      const command = `docker logs --tail ${lines} ${containerId}`;
      const output = await this.executeDockerCommand(command);
      
      return output.split('\n').filter(line => line.trim() !== '');

    } catch (error) {
      console.error(`Failed to get logs for container ${containerId}:`, error);
      throw error;
    }
  }

  async getContainerStats(containerId: string): Promise<ContainerStats | null> {
    try {
      if (!this.isConnected) {
        throw new Error('Docker service not connected');
      }

      const command = `docker stats --no-stream --format "{{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}" ${containerId}`;
      const output = await this.executeDockerCommand(command);
      
      if (!output.trim()) {
        return null;
      }

      return this.parseContainerStats(output, containerId);

    } catch (error) {
      console.error(`Failed to get stats for container ${containerId}:`, error);
      return null;
    }
  }

  async getAllContainerStats(): Promise<ContainerStats[]> {
    try {
      const containers = await this.getContainers();
      const stats: ContainerStats[] = [];

      for (const container of containers) {
        if (container.status === 'running') {
          const containerStats = await this.getContainerStats(container.id);
          if (containerStats) {
            stats.push(containerStats);
          }
        }
      }

      return stats;

    } catch (error) {
      console.error('Failed to get all container stats:', error);
      return [];
    }
  }

  async pullImage(imageName: string): Promise<boolean> {
    try {
      if (!this.isConnected) {
        throw new Error('Docker service not connected');
      }

      console.log(`Pulling image ${imageName}...`);

      const command = `docker pull ${imageName}`;
      await this.executeDockerCommand(command);

      console.log(`Image ${imageName} pulled successfully`);
      return true;

    } catch (error) {
      console.error(`Failed to pull image ${imageName}:`, error);
      return false;
    }
  }

  async getImages(): Promise<any[]> {
    try {
      if (!this.isConnected) {
        throw new Error('Docker service not connected');
      }

      const command = 'docker images --format "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"';
      const output = await this.executeDockerCommand(command);
      
      return this.parseImageList(output);

    } catch (error) {
      console.error('Failed to get images:', error);
      return [];
    }
  }

  getStatus(): DockerStatus {
    return { ...this.status };
  }

  private async checkLocalDocker(): Promise<boolean> {
    try {
      const result = await this.executeCommand('docker --version');
      return result.includes('Docker version');
    } catch (error) {
      return false;
    }
  }

  private async testSSHConnection(): Promise<boolean> {
    if (!this.sshConfig) {
      return false;
    }

    try {
      const command = `ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p ${this.sshConfig.port} ${this.sshConfig.username}@${this.sshConfig.host} "echo 'SSH connection test'"`;
      const result = await this.executeCommand(command);
      return result.includes('SSH connection test');
    } catch (error) {
      return false;
    }
  }

  private async getDockerInfo(): Promise<void> {
    try {
      const version = await this.executeDockerCommand('docker --version');
      this.status.version = version.trim();

      const info = await this.executeDockerCommand('docker info --format "{{.ServerVersion}}\t{{.Architecture}}\t{{.OperatingSystem}}"');
      const parts = info.trim().split('\t');
      if (parts.length >= 3) {
        this.status.api_version = parts[0];
        this.status.arch = parts[1];
        this.status.os = parts[2];
      }

    } catch (error) {
      console.warn('Failed to get Docker info:', error);
    }
  }

  private async getDockerInfoSSH(): Promise<void> {
    try {
      const version = await this.executeDockerCommandSSH('docker --version');
      this.status.version = version.trim();

      const info = await this.executeDockerCommandSSH('docker info --format "{{.ServerVersion}}\t{{.Architecture}}\t{{.OperatingSystem}}"');
      const parts = info.trim().split('\t');
      if (parts.length >= 3) {
        this.status.api_version = parts[0];
        this.status.arch = parts[1];
        this.status.os = parts[2];
      }

    } catch (error) {
      console.warn('Failed to get Docker info via SSH:', error);
    }
  }

  private async executeDockerCommand(command: string): Promise<string> {
    if (this.sshConfig) {
      return await this.executeDockerCommandSSH(command);
    } else {
      return await this.executeCommand(command);
    }
  }

  private async executeDockerCommandSSH(command: string): Promise<string> {
    if (!this.sshConfig) {
      throw new Error('SSH config not set');
    }

    const sshCommand = `ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p ${this.sshConfig.port} ${this.sshConfig.username}@${this.sshConfig.host} "${command}"`;
    return await this.executeCommand(sshCommand);
  }

  private async executeCommand(command: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const child = spawn('sh', ['-c', command], {
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stdout = '';
      let stderr = '';

      child.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      child.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      child.on('close', (code) => {
        if (code === 0) {
          resolve(stdout);
        } else {
          reject(new Error(`Command failed with code ${code}: ${stderr}`));
        }
      });

      child.on('error', (error) => {
        reject(error);
      });
    });
  }

  private parseContainerList(output: string): ContainerInfo[] {
    const containers: ContainerInfo[] = [];
    const lines = output.trim().split('\n');

    for (const line of lines) {
      if (line.trim()) {
        const parts = line.split('\t');
        if (parts.length >= 8) {
          containers.push({
            id: parts[0],
            name: parts[1],
            image: parts[2],
            status: this.parseContainerStatus(parts[3]),
            state: parts[4],
            ports: parts[5] ? parts[5].split(',') : [],
            created: parts[6],
            command: parts[7],
            labels: parts[8] ? this.parseLabels(parts[8]) : {}
          });
        }
      }
    }

    return containers;
  }

  private parseContainerStatus(status: string): ContainerInfo['status'] {
    if (status.includes('Up')) return 'running';
    if (status.includes('Exited')) return 'stopped';
    if (status.includes('Paused')) return 'paused';
    if (status.includes('Restarting')) return 'restarting';
    if (status.includes('Dead')) return 'dead';
    return 'created';
  }

  private parseLabels(labelsString: string): Record<string, string> {
    const labels: Record<string, string> = {};
    
    if (labelsString) {
      const pairs = labelsString.split(',');
      for (const pair of pairs) {
        const [key, value] = pair.split('=');
        if (key && value) {
          labels[key] = value;
        }
      }
    }
    
    return labels;
  }

  private parseContainerStats(output: string, containerId: string): ContainerStats {
    const parts = output.trim().split('\t');
    
    return {
      id: containerId,
      name: parts[0] || containerId,
      cpu_percent: parseFloat(parts[1]?.replace('%', '') || '0'),
      memory_usage: this.parseMemoryUsage(parts[2] || '0B'),
      memory_limit: this.parseMemoryUsage(parts[2]?.split(' / ')[1] || '0B'),
      memory_percent: parseFloat(parts[3]?.replace('%', '') || '0'),
      network_rx: this.parseNetworkUsage(parts[4]?.split(' / ')[0] || '0B'),
      network_tx: this.parseNetworkUsage(parts[4]?.split(' / ')[1] || '0B'),
      block_read: this.parseBlockUsage(parts[5]?.split(' / ')[0] || '0B'),
      block_write: this.parseBlockUsage(parts[5]?.split(' / ')[1] || '0B'),
      pids: parseInt(parts[6] || '0'),
      timestamp: new Date().toISOString()
    };
  }

  private parseMemoryUsage(usage: string): number {
    const match = usage.match(/(\d+(?:\.\d+)?)([KMGT]?B)/);
    if (match) {
      const value = parseFloat(match[1]);
      const unit = match[2];
      
      switch (unit) {
        case 'KB': return value * 1024;
        case 'MB': return value * 1024 * 1024;
        case 'GB': return value * 1024 * 1024 * 1024;
        case 'TB': return value * 1024 * 1024 * 1024 * 1024;
        default: return value;
      }
    }
    return 0;
  }

  private parseNetworkUsage(usage: string): number {
    return this.parseMemoryUsage(usage);
  }

  private parseBlockUsage(usage: string): number {
    return this.parseMemoryUsage(usage);
  }

  private parseImageList(output: string): any[] {
    const images: any[] = [];
    const lines = output.trim().split('\n');

    for (const line of lines) {
      if (line.trim()) {
        const parts = line.split('\t');
        if (parts.length >= 5) {
          images.push({
            repository: parts[0],
            tag: parts[1],
            id: parts[2],
            created: parts[3],
            size: parts[4]
          });
        }
      }
    }

    return images;
  }

  async cleanup(): Promise<void> {
    try {
      console.log('Cleaning up Docker Service...');
      
      // Close any active connections
      this.isConnected = false;
      this.sshConfig = null;
      this.status.connected = false;
      
      console.log('Docker Service cleanup completed');
      
    } catch (error) {
      console.error('Failed to cleanup Docker Service:', error);
    }
  }
}