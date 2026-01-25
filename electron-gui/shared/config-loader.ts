/**
 * Config Loader Service - Load api-services.conf at startup
 * SPEC-1B Implementation for dynamic endpoint resolution
 */

export interface ServiceConfig {
  [section: string]: {
    [key: string]: string | number | boolean;
  };
}

export class ConfigLoaderService {
  private static instance: ConfigLoaderService;
  private config: ServiceConfig = {};
  private isLoaded = false;

  private constructor() {}

  /**
   * Get singleton instance
   */
  static getInstance(): ConfigLoaderService {
    if (!ConfigLoaderService.instance) {
      ConfigLoaderService.instance = new ConfigLoaderService();
    }
    return ConfigLoaderService.instance;
  }

  /**
   * Load configuration from api-services.conf
   */
  async load(configPath: string = '/configs/api-services.conf'): Promise<void> {
    if (this.isLoaded) {
      console.log('Configuration already loaded');
      return;
    }

    try {
      console.log(`Loading configuration from: ${configPath}`);

      // Try to load the config file
      const response = await fetch(configPath);
      
      if (!response.ok) {
        throw new Error(`Failed to load config: ${response.statusCode}`);
      }

      const content = await response.text();
      this.config = this.parseConfig(content);
      this.isLoaded = true;

      console.log('Configuration loaded successfully', Object.keys(this.config));
    } catch (error) {
      console.error('Failed to load configuration:', error);
      // Use default configuration as fallback
      this.loadDefaults();
      this.isLoaded = true;
    }
  }

  /**
   * Parse INI-style configuration
   */
  private parseConfig(content: string): ServiceConfig {
    const config: ServiceConfig = {};
    let currentSection = '';

    const lines = content.split('\n');

    for (const line of lines) {
      const trimmed = line.trim();

      // Skip comments and empty lines
      if (!trimmed || trimmed.startsWith('#')) {
        continue;
      }

      // Section headers
      if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
        currentSection = trimmed.slice(1, -1);
        config[currentSection] = {};
        continue;
      }

      // Key-value pairs
      if (currentSection && trimmed.includes('=')) {
        const [key, ...valueParts] = trimmed.split('=');
        const value = valueParts.join('=').trim();

        config[currentSection][key.trim()] = this.parseValue(value);
      }
    }

    return config;
  }

  /**
   * Parse configuration value with type detection
   */
  private parseValue(value: string): string | number | boolean {
    if (value === 'true') return true;
    if (value === 'false') return false;
    if (!isNaN(Number(value)) && value !== '') return Number(value);
    return value;
  }

  /**
   * Get service endpoint
   */
  getServiceEndpoint(serviceName: string, key: string = 'api_url'): string {
    const service = this.config[serviceName];
    if (!service) {
      console.warn(`Service configuration not found: ${serviceName}`);
      return `http://localhost:8080/${serviceName}`;
    }

    const endpoint = service[key];
    if (!endpoint) {
      console.warn(`Endpoint key not found: ${serviceName}.${key}`);
      return `http://localhost:8080/${serviceName}`;
    }

    return String(endpoint);
  }

  /**
   * Get full service configuration
   */
  getServiceConfig(serviceName: string): any {
    return this.config[serviceName] || {};
  }

  /**
   * Get all configuration
   */
  getAllConfig(): ServiceConfig {
    return { ...this.config };
  }

  /**
   * Get configuration section
   */
  getSection(sectionName: string): any {
    return this.config[sectionName] || {};
  }

  /**
   * Load default configuration (fallback)
   */
  private loadDefaults(): void {
    this.config = {
      API_GATEWAY: {
        name: 'api-gateway',
        host: '172.20.0.10',
        port: 8080,
        api_url: 'http://172.20.0.10:8080/api/v1',
      },
      ADMIN_INTERFACE: {
        name: 'admin-interface',
        host: '172.20.0.26',
        port: 8083,
        api_url: 'http://172.20.0.26:8083/api/v1',
      },
      TRON_CLIENT: {
        name: 'tron-client',
        host: '172.20.0.27',
        port: 8091,
        api_url: 'http://172.20.0.27:8091/api/v1',
      },
      WALLET_MANAGER: {
        name: 'wallet-manager',
        host: '172.20.0.29',
        port: 8093,
        api_url: 'http://172.20.0.29:8093/api/v1',
      },
      PAYMENT_GATEWAY: {
        name: 'payment-gateway',
        host: '172.20.0.32',
        port: 8097,
        api_url: 'http://172.20.0.32:8097/api/v1',
      },
    };

    console.log('Loaded default configuration (config file not found)');
  }

  /**
   * Check if configuration is loaded
   */
  isConfigLoaded(): boolean {
    return this.isLoaded;
  }
}

export const configLoader = ConfigLoaderService.getInstance();

export default ConfigLoaderService;
