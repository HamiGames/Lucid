/**
 * Health Check Monitor Service - Monitor critical endpoints
 * SPEC-1B Implementation for admin interface
 */
import { LucidAPIClient } from './api-client';
export interface ServiceHealthCheck {
    service: string;
    url: string;
    status: 'healthy' | 'unhealthy' | 'unknown';
    lastCheck: string;
    responseTime: number;
    error?: string;
}
export declare class HealthCheckMonitor {
    private static instance;
    private services;
    private checkIntervals;
    private readonly defaultCheckInterval;
    private apiClient;
    private constructor();
    static getInstance(apiClient: LucidAPIClient): HealthCheckMonitor;
    /**
     * Register a service for health checks
     */
    registerService(serviceName: string, url: string, interval?: number): void;
    /**
     * Unregister a service
     */
    unregisterService(serviceName: string): void;
    /**
     * Perform health check for a service
     */
    private performHealthCheck;
    /**
     * Get service health status
     */
    getServiceHealth(serviceName: string): ServiceHealthCheck | undefined;
    /**
     * Get all services health status
     */
    getAllHealth(): ServiceHealthCheck[];
    /**
     * Get overall system health
     */
    getOverallHealth(): {
        overall: 'healthy' | 'degraded' | 'critical';
        healthyCount: number;
        unhealthyCount: number;
        unknownCount: number;
    };
    /**
     * Stop all health checks
     */
    stopAll(): void;
}
export default HealthCheckMonitor;
