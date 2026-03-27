/**
 * LUCID Docker Service - SPEC-1B Implementation
 * Manages Docker containers for Pi backend services
 */
import { EventEmitter } from 'events';
import type { DockerServiceState } from '../shared/ipc-channels';
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
export declare class DockerService extends EventEmitter {
    private status;
    private sshConfig;
    private isConnected;
    constructor();
    private containerToServiceState;
    startServices(services: string[], _level?: string): Promise<{
        success: boolean;
        started: string[];
        failed: Array<{
            service: string;
            error: string;
        }>;
    }>;
    stopServices(services: string[]): Promise<{
        success: boolean;
        stopped: string[];
        failed: Array<{
            service: string;
            error: string;
        }>;
    }>;
    restartServices(services: string[]): Promise<{
        success: boolean;
        started: string[];
        failed: Array<{
            service: string;
            error: string;
        }>;
    }>;
    getOrchestratedServiceStatus(): Promise<{
        services: DockerServiceState[];
        generatedAt: string;
    }>;
    findServiceStateByName(serviceName: string): Promise<DockerServiceState | null>;
    execCommand(containerId: string, command: string[], workingDir?: string, env?: Record<string, string>): Promise<{
        success: boolean;
        output: string;
        error?: string;
        exitCode: number;
    }>;
    initialize(): Promise<void>;
    connectSSH(config: SSHConfig): Promise<boolean>;
    getContainers(): Promise<ContainerInfo[]>;
    getContainer(containerId: string): Promise<ContainerInfo | null>;
    startContainer(containerId: string): Promise<boolean>;
    stopContainer(containerId: string): Promise<boolean>;
    restartContainer(containerId: string): Promise<boolean>;
    removeContainer(containerId: string, force?: boolean): Promise<boolean>;
    getContainerLogs(containerId: string, lines?: number, _follow?: boolean): Promise<{
        logs: string[];
        error?: string;
    }>;
    getContainerStats(containerId: string): Promise<ContainerStats | null>;
    getAllContainerStats(): Promise<ContainerStats[]>;
    pullImage(imageName: string): Promise<boolean>;
    getImages(): Promise<any[]>;
    getStatus(): DockerStatus;
    private checkLocalDocker;
    private testSSHConnection;
    private getDockerInfo;
    private getDockerInfoSSH;
    private executeDockerCommand;
    private executeDockerCommandSSH;
    private executeCommand;
    private parseContainerList;
    private parseContainerStatus;
    private parseLabels;
    private parseContainerStats;
    private parseMemoryUsage;
    private parseNetworkUsage;
    private parseBlockUsage;
    private parseImageList;
    cleanup(): Promise<void>;
}
