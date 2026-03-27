/**
 * Application Initialization Service
 * SPEC-1B Implementation for admin interface startup
 */
import { ConfigLoaderService } from './config-loader';
import { HealthCheckMonitor } from './health-check-monitor';
import { LucidWebSocketService } from './websocket-service';
export declare class AppInitializationService {
    private static instance;
    private isInitialized;
    private configLoader;
    private healthMonitor;
    private wsService;
    private constructor();
    static getInstance(): AppInitializationService;
    /**
     * Initialize the application
     */
    initialize(): Promise<void>;
    /**
     * Load configuration from api-services.conf
     */
    private loadConfiguration;
    /**
     * Initialize health checks for critical services
     */
    private initializeHealthChecks;
    /**
     * Initialize WebSocket service for real-time updates
     */
    private initializeWebSocket;
    /**
     * Setup global error handlers
     */
    private setupErrorHandlers;
    /**
     * Get configuration loader instance
     */
    getConfigLoader(): ConfigLoaderService;
    /**
     * Get health monitor instance
     */
    getHealthMonitor(): HealthCheckMonitor | null;
    /**
     * Get WebSocket service instance
     */
    getWebSocketService(): LucidWebSocketService | null;
    /**
     * Connect WebSocket
     */
    connectWebSocket(): Promise<void>;
    /**
     * Disconnect WebSocket
     */
    disconnectWebSocket(): void;
    /**
     * Check if application is initialized
     */
    isAppInitialized(): boolean;
    /**
     * Cleanup resources
     */
    cleanup(): void;
}
export declare const appInitialization: AppInitializationService;
export default AppInitializationService;
