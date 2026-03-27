/**
 * LUCID Tor Manager - SPEC-1B Implementation
 * Manages Tor daemon for secure .onion routing
 */
import { EventEmitter } from 'events';
export interface TorStatus {
    connected: boolean;
    status: 'stopped' | 'starting' | 'connected' | 'error';
    socksPort: number;
    controlPort: number;
    version?: string;
    error?: string;
    circuits?: number;
    bandwidth?: {
        read: number;
        written: number;
    };
}
export interface TorConfig {
    socksPort: number;
    controlPort: number;
    dataDirectory: string;
    logLevel: 'debug' | 'info' | 'notice' | 'warn' | 'err';
    exitNodes?: string[];
    strictNodes?: boolean;
    allowSingleHopExits?: boolean;
}
export declare class TorManager extends EventEmitter {
    private torProcess;
    private status;
    private config;
    private controlSocket;
    private isInitialized;
    constructor();
    initialize(): Promise<void>;
    start(): Promise<boolean>;
    stop(): Promise<boolean>;
    getStatus(): TorStatus;
    getVersion(): Promise<string | null>;
    getCircuits(): Promise<number>;
    getBandwidth(): Promise<{
        read: number;
        written: number;
    } | null>;
    private ensureDataDirectory;
    private checkTorBinary;
    private getTorBinaryPath;
    private loadConfiguration;
    private createDefaultConfiguration;
    private generateHashedPassword;
    private startTorProcess;
    private waitForTorReady;
    private testControlConnection;
    private sendControlCommand;
    private startMonitoring;
    getSocksProxyUrl(): string;
    getControlPort(): number;
    isConnected(): boolean;
    restart(): Promise<boolean>;
    addEventListener(type: string, listener: (...args: unknown[]) => void): this;
    getMetrics(): Promise<{
        uptimeSeconds: number;
        bytesRead: number;
        bytesWritten: number;
        circuitsBuilt: number;
        circuitsFailed: number;
        lastUpdated: string;
    }>;
    testConnection(options: {
        url: string;
        timeout?: number;
    } | string): Promise<boolean>;
    healthCheck(): Promise<{
        healthy: boolean;
        responseTime?: number;
        socksProxy?: boolean;
        controlPort?: boolean;
        bootstrap?: boolean;
        circuitBuild?: boolean;
        error?: string;
    }>;
}
