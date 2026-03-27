"use strict";
/**
 * Health Check Monitor Service - Monitor critical endpoints
 * SPEC-1B Implementation for admin interface
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.HealthCheckMonitor = void 0;
class HealthCheckMonitor {
    constructor(apiClient) {
        this.services = new Map();
        this.checkIntervals = new Map();
        this.defaultCheckInterval = 30000; // 30 seconds
        this.apiClient = apiClient;
    }
    static getInstance(apiClient) {
        if (!HealthCheckMonitor.instance) {
            HealthCheckMonitor.instance = new HealthCheckMonitor(apiClient);
        }
        return HealthCheckMonitor.instance;
    }
    /**
     * Register a service for health checks
     */
    registerService(serviceName, url, interval = this.defaultCheckInterval) {
        this.services.set(serviceName, {
            service: serviceName,
            url,
            status: 'unknown',
            lastCheck: new Date().toISOString(),
            responseTime: 0,
        });
        // Clear existing interval if any
        if (this.checkIntervals.has(serviceName)) {
            clearInterval(this.checkIntervals.get(serviceName));
        }
        // Start health checks
        this.performHealthCheck(serviceName);
        const intervalId = setInterval(() => {
            this.performHealthCheck(serviceName);
        }, interval);
        this.checkIntervals.set(serviceName, intervalId);
    }
    /**
     * Unregister a service
     */
    unregisterService(serviceName) {
        const intervalId = this.checkIntervals.get(serviceName);
        if (intervalId) {
            clearInterval(intervalId);
            this.checkIntervals.delete(serviceName);
        }
        this.services.delete(serviceName);
    }
    /**
     * Perform health check for a service
     */
    async performHealthCheck(serviceName) {
        const service = this.services.get(serviceName);
        if (!service) {
            return;
        }
        const startTime = Date.now();
        try {
            // Try to reach the health endpoint
            const response = await fetch(`${service.url}/health`, {
                method: 'GET',
                timeout: 10000,
            });
            const responseTime = Date.now() - startTime;
            if (response.ok || response.status === 200) {
                service.status = 'healthy';
                service.responseTime = responseTime;
                service.error = undefined;
            }
            else {
                service.status = 'unhealthy';
                service.responseTime = responseTime;
                service.error = `HTTP ${response.status}`;
            }
        }
        catch (error) {
            service.status = 'unhealthy';
            service.responseTime = Date.now() - startTime;
            service.error = error instanceof Error ? error.message : 'Unknown error';
        }
        service.lastCheck = new Date().toISOString();
    }
    /**
     * Get service health status
     */
    getServiceHealth(serviceName) {
        return this.services.get(serviceName);
    }
    /**
     * Get all services health status
     */
    getAllHealth() {
        return Array.from(this.services.values());
    }
    /**
     * Get overall system health
     */
    getOverallHealth() {
        const health = Array.from(this.services.values());
        const healthyCount = health.filter((s) => s.status === 'healthy').length;
        const unhealthyCount = health.filter((s) => s.status === 'unhealthy').length;
        const unknownCount = health.filter((s) => s.status === 'unknown').length;
        let overall;
        if (unhealthyCount > health.length * 0.5) {
            overall = 'critical';
        }
        else if (unhealthyCount > 0) {
            overall = 'degraded';
        }
        else {
            overall = 'healthy';
        }
        return {
            overall,
            healthyCount,
            unhealthyCount,
            unknownCount,
        };
    }
    /**
     * Stop all health checks
     */
    stopAll() {
        this.checkIntervals.forEach((intervalId) => {
            clearInterval(intervalId);
        });
        this.checkIntervals.clear();
        this.services.clear();
    }
}
exports.HealthCheckMonitor = HealthCheckMonitor;
exports.default = HealthCheckMonitor;
