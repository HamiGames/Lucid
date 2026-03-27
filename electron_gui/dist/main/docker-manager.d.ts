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
import { EventEmitter } from 'events';
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
export declare class DockerManager extends EventEmitter {
    private piConfig;
    private isConnected;
    private services;
    constructor(piConfig: PiConnectionConfig);
    /**
     * Setup IPC handlers for Docker operations
     */
    private setupIpcHandlers;
    /**
     * Test SSH connection to Raspberry Pi
     */
    testConnection(): Promise<boolean>;
    /**
     * Get current connection status
     */
    getConnectionStatus(): boolean;
    /**
     * Get all Docker services
     */
    getServices(): Promise<DockerService[]>;
    /**
     * Start a Docker service
     */
    startService(serviceName: string): Promise<boolean>;
    /**
     * Stop a Docker service
     */
    stopService(serviceName: string): Promise<boolean>;
    /**
     * Restart a Docker service
     */
    restartService(serviceName: string): Promise<boolean>;
    /**
     * Get service logs
     */
    getServiceLogs(serviceName: string, lines?: number): Promise<string>;
    /**
     * Get service health status
     */
    getServiceHealth(serviceName: string): Promise<string>;
    /**
     * Get Docker Compose services
     */
    getComposeServices(): Promise<DockerComposeService[]>;
    /**
     * Start Docker Compose services
     */
    startCompose(composeFile: string): Promise<boolean>;
    /**
     * Stop Docker Compose services
     */
    stopCompose(composeFile: string): Promise<boolean>;
    /**
     * Restart Docker Compose services
     */
    restartCompose(composeFile: string): Promise<boolean>;
    /**
     * Pull Docker images for compose file
     */
    pullImages(composeFile: string): Promise<boolean>;
    /**
     * Start a specific phase
     */
    startPhase(phase: string): Promise<boolean>;
    /**
     * Stop a specific phase
     */
    stopPhase(phase: string): Promise<boolean>;
    /**
     * Get phase status
     */
    getPhaseStatus(phase: string): Promise<DockerComposeService[]>;
    /**
     * Execute SSH command on Raspberry Pi
     */
    private executeSshCommand;
    /**
     * Parse Docker ps output
     */
    private parseDockerPsOutput;
    /**
     * Parse container status string
     */
    private parseContainerStatus;
    /**
     * Map container to service with phase information
     */
    private mapContainerToService;
    /**
     * Determine service phase based on container name
     */
    private determineServicePhase;
    /**
     * Determine service health based on container status
     */
    private determineServiceHealth;
}
export declare const defaultPiConfig: PiConnectionConfig;
export default DockerManager;
