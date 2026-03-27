"use strict";
/**
 * LUCID Docker Service - SPEC-1B Implementation
 * Manages Docker containers for Pi backend services
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DockerService = void 0;
const child_process_1 = require("child_process");
const events_1 = require("events");
class DockerService extends events_1.EventEmitter {
    constructor() {
        super();
        this.sshConfig = null;
        this.isConnected = false;
        this.status = {
            connected: false
        };
    }
    containerToServiceState(c) {
        let st = 'stopped';
        if (c.status === 'running')
            st = 'running';
        else if (c.status === 'restarting')
            st = 'starting';
        else if (c.status === 'dead')
            st = 'error';
        return {
            service: c.name,
            displayName: c.name,
            image: c.image,
            level: 'core',
            plane: 'core',
            status: st,
            containerId: c.id,
            ports: c.ports,
            updatedAt: new Date().toISOString(),
        };
    }
    async startServices(services, _level) {
        const started = [];
        const failed = [];
        for (const name of services) {
            try {
                const ok = await this.startContainer(name);
                if (ok)
                    started.push(name);
                else
                    failed.push({ service: name, error: 'docker start failed' });
            }
            catch (e) {
                failed.push({
                    service: name,
                    error: e instanceof Error ? e.message : String(e),
                });
            }
        }
        return { success: failed.length === 0, started, failed };
    }
    async stopServices(services) {
        const stopped = [];
        const failed = [];
        for (const name of services) {
            try {
                const ok = await this.stopContainer(name);
                if (ok)
                    stopped.push(name);
                else
                    failed.push({ service: name, error: 'docker stop failed' });
            }
            catch (e) {
                failed.push({
                    service: name,
                    error: e instanceof Error ? e.message : String(e),
                });
            }
        }
        return { success: failed.length === 0, stopped, failed };
    }
    async restartServices(services) {
        const started = [];
        const failed = [];
        for (const name of services) {
            try {
                const ok = await this.restartContainer(name);
                if (ok)
                    started.push(name);
                else
                    failed.push({ service: name, error: 'docker restart failed' });
            }
            catch (e) {
                failed.push({
                    service: name,
                    error: e instanceof Error ? e.message : String(e),
                });
            }
        }
        return { success: failed.length === 0, started, failed };
    }
    async getOrchestratedServiceStatus() {
        const containers = await this.getContainers();
        return {
            services: containers.map((c) => this.containerToServiceState(c)),
            generatedAt: new Date().toISOString(),
        };
    }
    async findServiceStateByName(serviceName) {
        const containers = await this.getContainers();
        const c = containers.find((x) => x.name === serviceName || x.id === serviceName);
        return c ? this.containerToServiceState(c) : null;
    }
    async execCommand(containerId, command, workingDir, env) {
        try {
            if (!this.isConnected) {
                throw new Error('Docker service not connected');
            }
            const wdFlag = workingDir ? `-w ${workingDir} ` : '';
            const envPrefix = env
                ? Object.entries(env)
                    .map(([k, v]) => `-e ${k}=${JSON.stringify(v)}`)
                    .join(' ') + ' '
                : '';
            const inner = command.map((p) => JSON.stringify(p)).join(' ');
            const full = `docker exec ${wdFlag}${envPrefix}${containerId} ${inner}`;
            const output = await this.executeDockerCommand(full);
            return {
                success: true,
                output,
                exitCode: 0,
            };
        }
        catch (e) {
            return {
                success: false,
                output: '',
                error: e instanceof Error ? e.message : String(e),
                exitCode: -1,
            };
        }
    }
    async initialize() {
        try {
            console.log('Initializing Docker Service...');
            // Check if Docker is available locally
            const localDocker = await this.checkLocalDocker();
            if (localDocker) {
                console.log('Local Docker available');
                this.isConnected = true;
                this.status.connected = true;
                await this.getDockerInfo();
            }
            else {
                console.log('Local Docker not available, will use SSH connection');
                this.status.connected = false;
            }
            console.log('Docker Service initialized successfully');
        }
        catch (error) {
            console.error('Failed to initialize Docker Service:', error);
            throw error;
        }
    }
    async connectSSH(config) {
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
            }
            else {
                this.status.error = 'Failed to connect via SSH';
                return false;
            }
        }
        catch (error) {
            console.error('Failed to connect to Docker via SSH:', error);
            this.status.error = error instanceof Error ? error.message : String(error);
            return false;
        }
    }
    async getContainers() {
        try {
            if (!this.isConnected) {
                throw new Error('Docker service not connected');
            }
            const command = 'docker ps -a --format "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.State}}\t{{.Ports}}\t{{.CreatedAt}}\t{{.Command}}\t{{.Labels}}"';
            const output = await this.executeDockerCommand(command);
            return this.parseContainerList(output);
        }
        catch (error) {
            console.error('Failed to get containers:', error);
            throw error;
        }
    }
    async getContainer(containerId) {
        try {
            const containers = await this.getContainers();
            return containers.find(c => c.id === containerId) || null;
        }
        catch (error) {
            console.error(`Failed to get container ${containerId}:`, error);
            return null;
        }
    }
    async startContainer(containerId) {
        try {
            if (!this.isConnected) {
                throw new Error('Docker service not connected');
            }
            console.log(`Starting container ${containerId}...`);
            const command = `docker start ${containerId}`;
            await this.executeDockerCommand(command);
            console.log(`Container ${containerId} started successfully`);
            return true;
        }
        catch (error) {
            console.error(`Failed to start container ${containerId}:`, error);
            return false;
        }
    }
    async stopContainer(containerId) {
        try {
            if (!this.isConnected) {
                throw new Error('Docker service not connected');
            }
            console.log(`Stopping container ${containerId}...`);
            const command = `docker stop ${containerId}`;
            await this.executeDockerCommand(command);
            console.log(`Container ${containerId} stopped successfully`);
            return true;
        }
        catch (error) {
            console.error(`Failed to stop container ${containerId}:`, error);
            return false;
        }
    }
    async restartContainer(containerId) {
        try {
            if (!this.isConnected) {
                throw new Error('Docker service not connected');
            }
            console.log(`Restarting container ${containerId}...`);
            const command = `docker restart ${containerId}`;
            await this.executeDockerCommand(command);
            console.log(`Container ${containerId} restarted successfully`);
            return true;
        }
        catch (error) {
            console.error(`Failed to restart container ${containerId}:`, error);
            return false;
        }
    }
    async removeContainer(containerId, force = false) {
        try {
            if (!this.isConnected) {
                throw new Error('Docker service not connected');
            }
            console.log(`Removing container ${containerId}...`);
            const command = `docker rm ${force ? '-f ' : ''}${containerId}`;
            await this.executeDockerCommand(command);
            console.log(`Container ${containerId} removed successfully`);
            return true;
        }
        catch (error) {
            console.error(`Failed to remove container ${containerId}:`, error);
            return false;
        }
    }
    async getContainerLogs(containerId, lines = 100, _follow = false) {
        try {
            if (!this.isConnected) {
                throw new Error('Docker service not connected');
            }
            const command = `docker logs --tail ${lines} ${containerId}`;
            const output = await this.executeDockerCommand(command);
            return {
                logs: output.split('\n').filter((line) => line.trim() !== ''),
            };
        }
        catch (error) {
            console.error(`Failed to get logs for container ${containerId}:`, error);
            return {
                logs: [],
                error: error instanceof Error ? error.message : String(error),
            };
        }
    }
    async getContainerStats(containerId) {
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
        }
        catch (error) {
            console.error(`Failed to get stats for container ${containerId}:`, error);
            return null;
        }
    }
    async getAllContainerStats() {
        try {
            const containers = await this.getContainers();
            const stats = [];
            for (const container of containers) {
                if (container.status === 'running') {
                    const containerStats = await this.getContainerStats(container.id);
                    if (containerStats) {
                        stats.push(containerStats);
                    }
                }
            }
            return stats;
        }
        catch (error) {
            console.error('Failed to get all container stats:', error);
            return [];
        }
    }
    async pullImage(imageName) {
        try {
            if (!this.isConnected) {
                throw new Error('Docker service not connected');
            }
            console.log(`Pulling image ${imageName}...`);
            const command = `docker pull ${imageName}`;
            await this.executeDockerCommand(command);
            console.log(`Image ${imageName} pulled successfully`);
            return true;
        }
        catch (error) {
            console.error(`Failed to pull image ${imageName}:`, error);
            return false;
        }
    }
    async getImages() {
        try {
            if (!this.isConnected) {
                throw new Error('Docker service not connected');
            }
            const command = 'docker images --format "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"';
            const output = await this.executeDockerCommand(command);
            return this.parseImageList(output);
        }
        catch (error) {
            console.error('Failed to get images:', error);
            return [];
        }
    }
    getStatus() {
        return { ...this.status };
    }
    async checkLocalDocker() {
        try {
            const result = await this.executeCommand('docker --version');
            return result.includes('Docker version');
        }
        catch (error) {
            return false;
        }
    }
    async testSSHConnection() {
        if (!this.sshConfig) {
            return false;
        }
        try {
            const command = `ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p ${this.sshConfig.port} ${this.sshConfig.username}@${this.sshConfig.host} "echo 'SSH connection test'"`;
            const result = await this.executeCommand(command);
            return result.includes('SSH connection test');
        }
        catch (error) {
            return false;
        }
    }
    async getDockerInfo() {
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
        }
        catch (error) {
            console.warn('Failed to get Docker info:', error);
        }
    }
    async getDockerInfoSSH() {
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
        }
        catch (error) {
            console.warn('Failed to get Docker info via SSH:', error);
        }
    }
    async executeDockerCommand(command) {
        if (this.sshConfig) {
            return await this.executeDockerCommandSSH(command);
        }
        else {
            return await this.executeCommand(command);
        }
    }
    async executeDockerCommandSSH(command) {
        if (!this.sshConfig) {
            throw new Error('SSH config not set');
        }
        const sshCommand = `ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p ${this.sshConfig.port} ${this.sshConfig.username}@${this.sshConfig.host} "${command}"`;
        return await this.executeCommand(sshCommand);
    }
    async executeCommand(command) {
        return new Promise((resolve, reject) => {
            const shell = process.platform === 'win32' ? 'cmd.exe' : 'sh';
            const shellArgs = process.platform === 'win32' ? ['/c', command] : ['-c', command];
            const child = (0, child_process_1.spawn)(shell, shellArgs, {
                stdio: ['pipe', 'pipe', 'pipe'],
                shell: process.platform === 'win32' ? true : false,
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
                }
                else {
                    reject(new Error(`Command failed with code ${code}: ${stderr}`));
                }
            });
            child.on('error', (error) => {
                reject(error);
            });
        });
    }
    parseContainerList(output) {
        const containers = [];
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
    parseContainerStatus(status) {
        if (status.includes('Up'))
            return 'running';
        if (status.includes('Exited'))
            return 'stopped';
        if (status.includes('Paused'))
            return 'paused';
        if (status.includes('Restarting'))
            return 'restarting';
        if (status.includes('Dead'))
            return 'dead';
        return 'created';
    }
    parseLabels(labelsString) {
        const labels = {};
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
    parseContainerStats(output, containerId) {
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
    parseMemoryUsage(usage) {
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
    parseNetworkUsage(usage) {
        return this.parseMemoryUsage(usage);
    }
    parseBlockUsage(usage) {
        return this.parseMemoryUsage(usage);
    }
    parseImageList(output) {
        const images = [];
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
    async cleanup() {
        try {
            console.log('Cleaning up Docker Service...');
            // Close any active connections
            this.isConnected = false;
            this.sshConfig = null;
            this.status.connected = false;
            console.log('Docker Service cleanup completed');
        }
        catch (error) {
            console.error('Failed to cleanup Docker Service:', error);
        }
    }
}
exports.DockerService = DockerService;
