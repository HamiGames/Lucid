"use strict";
/**
 * Application Initialization Service
 * SPEC-1B Implementation for admin interface startup
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.appInitialization = exports.AppInitializationService = void 0;
const config_loader_1 = require("./config-loader");
const health_check_monitor_1 = require("./health-check-monitor");
const api_client_1 = require("./api-client");
const websocket_service_1 = require("./websocket-service");
class AppInitializationService {
    constructor() {
        this.isInitialized = false;
        this.healthMonitor = null;
        this.wsService = null;
        this.configLoader = config_loader_1.ConfigLoaderService.getInstance();
    }
    static getInstance() {
        if (!AppInitializationService.instance) {
            AppInitializationService.instance = new AppInitializationService();
        }
        return AppInitializationService.instance;
    }
    /**
     * Initialize the application
     */
    async initialize() {
        if (this.isInitialized) {
            console.log('Application already initialized');
            return;
        }
        try {
            console.log('Starting application initialization...');
            // 1. Load configuration from api-services.conf
            await this.loadConfiguration();
            // 2. Initialize API client
            const apiClient = new api_client_1.LucidAPIClient(this.configLoader.getServiceEndpoint('API_GATEWAY', 'api_url'));
            // 3. Initialize health check monitor
            this.initializeHealthChecks(apiClient);
            // 4. Initialize WebSocket service for real-time updates
            await this.initializeWebSocket();
            // 5. Setup error handlers
            this.setupErrorHandlers();
            this.isInitialized = true;
            console.log('Application initialization completed successfully');
        }
        catch (error) {
            console.error('Application initialization failed:', error);
            throw error;
        }
    }
    /**
     * Load configuration from api-services.conf
     */
    async loadConfiguration() {
        try {
            console.log('Loading configuration...');
            // Get config path from environment or use default
            const configPath = process.env.ELECTRON_GUI_CONFIG_FILE ||
                '/configs/api-services.conf';
            await this.configLoader.load(configPath);
            console.log('Configuration loaded successfully');
        }
        catch (error) {
            console.error('Failed to load configuration:', error);
            throw error;
        }
    }
    /**
     * Initialize health checks for critical services
     */
    initializeHealthChecks(apiClient) {
        try {
            console.log('Initializing health checks...');
            this.healthMonitor = health_check_monitor_1.HealthCheckMonitor.getInstance(apiClient);
            // Register critical services
            const criticalServices = [
                { name: 'API_GATEWAY', interval: 30000 },
                { name: 'ADMIN_INTERFACE', interval: 30000 },
                { name: 'TRON_CLIENT', interval: 30000 },
                { name: 'WALLET_MANAGER', interval: 30000 },
                { name: 'PAYMENT_GATEWAY', interval: 30000 },
            ];
            for (const service of criticalServices) {
                try {
                    const url = this.configLoader.getServiceEndpoint(service.name, 'api_url');
                    this.healthMonitor.registerService(service.name, url, service.interval);
                    console.log(`Registered health check for ${service.name}`);
                }
                catch (error) {
                    console.warn(`Failed to register health check for ${service.name}:`, error);
                }
            }
        }
        catch (error) {
            console.error('Failed to initialize health checks:', error);
            // Continue without health checks
        }
    }
    /**
     * Initialize WebSocket service for real-time updates
     */
    async initializeWebSocket() {
        try {
            console.log('Initializing WebSocket service...');
            // Get WebSocket endpoint (usually same host as API gateway, different port)
            const apiUrl = this.configLoader.getServiceEndpoint('API_GATEWAY', 'api_url');
            const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://');
            const wsEndpoint = `${wsUrl.replace(/\/api\/v1$/, '')}/ws`;
            this.wsService = new websocket_service_1.LucidWebSocketService({
                url: wsEndpoint,
                reconnectInterval: 5000,
                maxReconnectAttempts: 10,
            });
            // Setup WebSocket event handlers
            this.wsService.on('connected', () => {
                console.log('WebSocket connected');
            });
            this.wsService.on('disconnected', () => {
                console.log('WebSocket disconnected');
            });
            this.wsService.on('error', (error) => {
                console.error('WebSocket error:', error);
            });
            // Note: Don't auto-connect, let the app decide when to connect
            // Users can explicitly call connect()
            console.log('WebSocket service initialized');
        }
        catch (error) {
            console.warn('Failed to initialize WebSocket service:', error);
            // Continue without WebSocket
        }
    }
    /**
     * Setup global error handlers
     */
    setupErrorHandlers() {
        // Handle unhandled promise rejections
        if (typeof window !== 'undefined') {
            window.addEventListener('unhandledrejection', (event) => {
                console.error('Unhandled promise rejection:', event.reason);
            });
            // Handle global errors
            window.addEventListener('error', (event) => {
                console.error('Global error:', event.error);
            });
        }
    }
    /**
     * Get configuration loader instance
     */
    getConfigLoader() {
        return this.configLoader;
    }
    /**
     * Get health monitor instance
     */
    getHealthMonitor() {
        return this.healthMonitor;
    }
    /**
     * Get WebSocket service instance
     */
    getWebSocketService() {
        return this.wsService;
    }
    /**
     * Connect WebSocket
     */
    async connectWebSocket() {
        if (this.wsService) {
            await this.wsService.connect();
        }
    }
    /**
     * Disconnect WebSocket
     */
    disconnectWebSocket() {
        if (this.wsService) {
            this.wsService.disconnect();
        }
    }
    /**
     * Check if application is initialized
     */
    isAppInitialized() {
        return this.isInitialized;
    }
    /**
     * Cleanup resources
     */
    cleanup() {
        console.log('Cleaning up application resources...');
        if (this.healthMonitor) {
            this.healthMonitor.stopAll();
        }
        if (this.wsService) {
            this.wsService.disconnect();
        }
        this.isInitialized = false;
    }
}
exports.AppInitializationService = AppInitializationService;
exports.appInitialization = AppInitializationService.getInstance();
exports.default = AppInitializationService;
