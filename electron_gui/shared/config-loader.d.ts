/**
 * Config Loader Service - Load api-services.conf at startup
 * SPEC-1B Implementation for dynamic endpoint resolution
 */
export interface ServiceConfig {
    [section: string]: {
        [key: string]: string | number | boolean;
    };
}
export declare class ConfigLoaderService {
    private static instance;
    private config;
    private isLoaded;
    private constructor();
    /**
     * Get singleton instance
     */
    static getInstance(): ConfigLoaderService;
    /**
     * Load configuration from api-services.conf
     */
    load(configPath?: string): Promise<void>;
    /**
     * Parse INI-style configuration
     */
    private parseConfig;
    /**
     * Parse configuration value with type detection
     */
    private parseValue;
    /**
     * Get service endpoint
     */
    getServiceEndpoint(serviceName: string, key?: string): string;
    /**
     * Get full service configuration
     */
    getServiceConfig(serviceName: string): any;
    /**
     * Get all configuration
     */
    getAllConfig(): ServiceConfig;
    /**
     * Get configuration section
     */
    getSection(sectionName: string): any;
    /**
     * Load default configuration (fallback)
     */
    private loadDefaults;
    /**
     * Check if configuration is loaded
     */
    isConfigLoaded(): boolean;
}
export declare const configLoader: ConfigLoaderService;
export default ConfigLoaderService;
