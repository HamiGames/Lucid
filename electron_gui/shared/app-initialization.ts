/**
 * Application Initialization Service
 * SPEC-1B Implementation for admin interface startup
 */

import { configLoader, ConfigLoaderService } from './config-loader';
import { HealthCheckMonitor } from './health-check-monitor';
import { LucidAPIClient } from './api-client';
import { LucidWebSocketService } from './websocket-service';
import { API_ENDPOINTS } from './constants';

export class AppInitializationService {
  private static instance: AppInitializationService;
  private isInitialized = false;
  private configLoader: ConfigLoaderService;
  private healthMonitor: HealthCheckMonitor | null = null;
  private wsService: LucidWebSocketService | null = null;

  private constructor() {
    this.configLoader = ConfigLoaderService.getInstance();
  }

  static getInstance(): AppInitializationService {
    if (!AppInitializationService.instance) {
      AppInitializationService.instance = new AppInitializationService();
    }
    return AppInitializationService.instance;
  }

  /**
   * Initialize the application
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      console.log('Application already initialized');
      return;
    }

    try {
      console.log('Starting application initialization...');

      // 1. Load configuration from api-services.conf
      await this.loadConfiguration();

      // 2. Initialize API client
      const apiClient = new LucidAPIClient(
        this.configLoader.getServiceEndpoint('API_GATEWAY', 'api_url')
      );

      // 3. Initialize health check monitor
      this.initializeHealthChecks(apiClient);

      // 4. Initialize WebSocket service for real-time updates
      await this.initializeWebSocket();

      // 5. Setup error handlers
      this.setupErrorHandlers();

      this.isInitialized = true;
      console.log('Application initialization completed successfully');
    } catch (error) {
      console.error('Application initialization failed:', error);
      throw error;
    }
  }

  /**
   * Load configuration from api-services.conf
   */
  private async loadConfiguration(): Promise<void> {
    try {
      console.log('Loading configuration...');

      // Get config path from environment or use default
      const configPath =
        process.env.ELECTRON_GUI_CONFIG_FILE || 
        '/configs/api-services.conf';

      await this.configLoader.load(configPath);

      console.log('Configuration loaded successfully');
    } catch (error) {
      console.error('Failed to load configuration:', error);
      throw error;
    }
  }

  /**
   * Initialize health checks for critical services
   */
  private initializeHealthChecks(apiClient: LucidAPIClient): void {
    try {
      console.log('Initializing health checks...');

      this.healthMonitor = HealthCheckMonitor.getInstance(apiClient);

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
        } catch (error) {
          console.warn(`Failed to register health check for ${service.name}:`, error);
        }
      }
    } catch (error) {
      console.error('Failed to initialize health checks:', error);
      // Continue without health checks
    }
  }

  /**
   * Initialize WebSocket service for real-time updates
   */
  private async initializeWebSocket(): Promise<void> {
    try {
      console.log('Initializing WebSocket service...');

      // Get WebSocket endpoint (usually same host as API gateway, different port)
      const apiUrl = this.configLoader.getServiceEndpoint('API_GATEWAY', 'api_url');
      const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://');
      const wsEndpoint = `${wsUrl.replace(/\/api\/v1$/, '')}/ws`;

      this.wsService = new LucidWebSocketService({
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
    } catch (error) {
      console.warn('Failed to initialize WebSocket service:', error);
      // Continue without WebSocket
    }
  }

  /**
   * Setup global error handlers
   */
  private setupErrorHandlers(): void {
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
  getConfigLoader(): ConfigLoaderService {
    return this.configLoader;
  }

  /**
   * Get health monitor instance
   */
  getHealthMonitor(): HealthCheckMonitor | null {
    return this.healthMonitor;
  }

  /**
   * Get WebSocket service instance
   */
  getWebSocketService(): LucidWebSocketService | null {
    return this.wsService;
  }

  /**
   * Connect WebSocket
   */
  async connectWebSocket(): Promise<void> {
    if (this.wsService) {
      await this.wsService.connect();
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket(): void {
    if (this.wsService) {
      this.wsService.disconnect();
    }
  }

  /**
   * Check if application is initialized
   */
  isAppInitialized(): boolean {
    return this.isInitialized;
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
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

export const appInitialization = AppInitializationService.getInstance();

export default AppInitializationService;
