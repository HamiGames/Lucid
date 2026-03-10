/**
 * Configuration Service - Handles system configuration management for admin interface
 * Provides configuration backup, restore, and management functionality
 */

import { adminApi, ConfigurationBackup } from './adminApi';

export interface SystemConfiguration {
  [key: string]: any;
}

export interface ConfigurationSection {
  name: string;
  display_name: string;
  description: string;
  settings: ConfigurationSetting[];
  validation_rules?: ValidationRule[];
}

export interface ConfigurationSetting {
  key: string;
  display_name: string;
  description: string;
  type: 'string' | 'number' | 'boolean' | 'select' | 'array' | 'object';
  value: any;
  default_value: any;
  options?: Array<{ value: any; label: string }>;
  validation_rules?: ValidationRule[];
  is_sensitive?: boolean;
  requires_restart?: boolean;
  category?: string;
}

export interface ValidationRule {
  type: 'required' | 'min' | 'max' | 'pattern' | 'custom';
  value?: any;
  message: string;
  validator?: (value: any) => boolean;
}

export interface ConfigurationValidationResult {
  is_valid: boolean;
  errors: Array<{
    setting_key: string;
    error_message: string;
  }>;
  warnings: Array<{
    setting_key: string;
    warning_message: string;
  }>;
}

export interface ConfigurationBackupOptions {
  include_sensitive_data: boolean;
  include_user_data: boolean;
  include_system_data: boolean;
  compression: boolean;
  encryption: boolean;
}

export interface ConfigurationRestoreOptions {
  restore_sensitive_data: boolean;
  restore_user_data: boolean;
  restore_system_data: boolean;
  create_backup_before_restore: boolean;
  validate_before_restore: boolean;
}

export interface ConfigurationChange {
  setting_key: string;
  old_value: any;
  new_value: any;
  timestamp: string;
  changed_by: string;
  reason?: string;
}

export interface ConfigurationHistory {
  changes: ConfigurationChange[];
  total_changes: number;
  last_modified: string;
  last_modified_by: string;
}

class ConfigService {
  private configurationCache: SystemConfiguration | null = null;
  private sectionsCache: ConfigurationSection[] | [];
  private backupListCache: ConfigurationBackup[] = [];
  private lastConfigUpdate: number = 0;
  private lastSectionsUpdate: number = 0;
  private lastBackupUpdate: number = 0;
  private readonly CACHE_DURATION = 300000; // 5 minutes

  /**
   * Get system configuration
   */
  async getSystemConfiguration(forceRefresh: boolean = false): Promise<SystemConfiguration> {
    const now = Date.now();
    const isCacheValid = (now - this.lastConfigUpdate) < this.CACHE_DURATION;

    if (!forceRefresh && isCacheValid && this.configurationCache) {
      return this.configurationCache;
    }

    try {
      const config = await adminApi.getSystemConfiguration();
      
      this.configurationCache = config;
      this.lastConfigUpdate = now;
      
      return config;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Update system configuration
   */
  async updateSystemConfiguration(
    updates: Partial<SystemConfiguration>,
    reason?: string
  ): Promise<{ success: boolean; message: string; validation_result?: ConfigurationValidationResult }> {
    try {
      // Validate configuration before update
      const validationResult = await this.validateConfiguration(updates);
      
      if (!validationResult.is_valid) {
        return {
          success: false,
          message: 'Configuration validation failed',
          validation_result: validationResult
        };
      }

      const result = await adminApi.updateSystemConfiguration(updates);
      
      // Clear cache to force refresh
      this.configurationCache = null;
      this.lastConfigUpdate = 0;
      
      return {
        success: result.success,
        message: result.message,
        validation_result: validationResult
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to update configuration: ${error.message}`
      };
    }
  }

  /**
   * Get configuration sections
   */
  async getConfigurationSections(): Promise<ConfigurationSection[]> {
    const now = Date.now();
    const isCacheValid = (now - this.lastSectionsUpdate) < this.CACHE_DURATION;

    if (isCacheValid && this.sectionsCache.length > 0) {
      return this.sectionsCache;
    }

    try {
      // This would typically come from a specific API endpoint
      // For now, we'll generate sections from the configuration
      const config = await this.getSystemConfiguration();
      const sections = this.generateConfigurationSections(config);
      
      this.sectionsCache = sections;
      this.lastSectionsUpdate = now;
      
      return sections;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get configuration section by name
   */
  async getConfigurationSection(sectionName: string): Promise<ConfigurationSection | null> {
    try {
      const sections = await this.getConfigurationSections();
      return sections.find(section => section.name === sectionName) || null;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Update configuration section
   */
  async updateConfigurationSection(
    sectionName: string,
    updates: Record<string, any>,
    reason?: string
  ): Promise<{ success: boolean; message: string }> {
    try {
      // Get current configuration
      const currentConfig = await this.getSystemConfiguration();
      
      // Apply updates to the specific section
      const updatedConfig = { ...currentConfig };
      Object.keys(updates).forEach(key => {
        updatedConfig[key] = updates[key];
      });

      return await this.updateSystemConfiguration(updatedConfig, reason);
    } catch (error) {
      return {
        success: false,
        message: `Failed to update configuration section: ${error.message}`
      };
    }
  }

  /**
   * Validate configuration
   */
  async validateConfiguration(config: Partial<SystemConfiguration>): Promise<ConfigurationValidationResult> {
    try {
      const sections = await this.getConfigurationSections();
      const result: ConfigurationValidationResult = {
        is_valid: true,
        errors: [],
        warnings: []
      };

      // Validate each setting
      Object.keys(config).forEach(key => {
        const section = sections.find(s => s.settings.some(setting => setting.key === key));
        if (section) {
          const setting = section.settings.find(s => s.key === key);
          if (setting && setting.validation_rules) {
            setting.validation_rules.forEach(rule => {
              const validation = this.validateSetting(setting.key, config[key], rule);
              if (!validation.is_valid) {
                result.is_valid = false;
                result.errors.push({
                  setting_key: setting.key,
                  error_message: validation.message
                });
              }
              if (validation.warning) {
                result.warnings.push({
                  setting_key: setting.key,
                  warning_message: validation.message
                });
              }
            });
          }
        }
      });

      return result;
    } catch (error) {
      return {
        is_valid: false,
        errors: [{ setting_key: 'general', error_message: `Validation error: ${error.message}` }],
        warnings: []
      };
    }
  }

  /**
   * Create configuration backup
   */
  async createConfigurationBackup(options?: ConfigurationBackupOptions): Promise<ConfigurationBackup> {
    try {
      const backup = await adminApi.createConfigurationBackup();
      
      // Clear backup cache
      this.backupListCache = [];
      this.lastBackupUpdate = 0;
      
      return backup;
    } catch (error) {
      throw error;
    }
  }

  /**
   * List configuration backups
   */
  async listConfigurationBackups(): Promise<ConfigurationBackup[]> {
    const now = Date.now();
    const isCacheValid = (now - this.lastBackupUpdate) < this.CACHE_DURATION;

    if (isCacheValid && this.backupListCache.length > 0) {
      return this.backupListCache;
    }

    try {
      const backups = await adminApi.listConfigurationBackups();
      
      this.backupListCache = backups;
      this.lastBackupUpdate = now;
      
      return backups;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Restore configuration backup
   */
  async restoreConfigurationBackup(
    backupId: string,
    options?: ConfigurationRestoreOptions
  ): Promise<{ success: boolean; message: string }> {
    try {
      const result = await adminApi.restoreConfigurationBackup(backupId);
      
      // Clear all caches
      this.clearCache();
      
      return result;
    } catch (error) {
      return {
        success: false,
        message: `Failed to restore configuration backup: ${error.message}`
      };
    }
  }

  /**
   * Get configuration history
   */
  async getConfigurationHistory(limit: number = 50): Promise<ConfigurationHistory> {
    try {
      // This would typically come from a specific API endpoint
      // For now, we'll return mock data
      return {
        changes: [],
        total_changes: 0,
        last_modified: new Date().toISOString(),
        last_modified_by: 'admin'
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Reset configuration to defaults
   */
  async resetConfigurationToDefaults(
    sectionName?: string,
    reason?: string
  ): Promise<{ success: boolean; message: string }> {
    try {
      if (sectionName) {
        // Reset specific section
        const section = await this.getConfigurationSection(sectionName);
        if (!section) {
          return {
            success: false,
            message: `Configuration section '${sectionName}' not found`
          };
        }

        const defaultValues: Record<string, any> = {};
        section.settings.forEach(setting => {
          defaultValues[setting.key] = setting.default_value;
        });

        return await this.updateConfigurationSection(sectionName, defaultValues, reason);
      } else {
        // Reset entire configuration
        const sections = await this.getConfigurationSections();
        const defaultConfig: SystemConfiguration = {};
        
        sections.forEach(section => {
          section.settings.forEach(setting => {
            defaultConfig[setting.key] = setting.default_value;
          });
        });

        return await this.updateSystemConfiguration(defaultConfig, reason);
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to reset configuration: ${error.message}`
      };
    }
  }

  /**
   * Export configuration
   */
  async exportConfiguration(
    format: 'json' | 'yaml' | 'toml' = 'json',
    includeSensitive: boolean = false
  ): Promise<Blob> {
    try {
      const config = await this.getSystemConfiguration();
      
      // Filter sensitive data if requested
      const exportConfig = includeSensitive ? config : this.filterSensitiveData(config);
      
      let content: string;
      let mimeType: string;
      
      switch (format) {
        case 'json':
          content = JSON.stringify(exportConfig, null, 2);
          mimeType = 'application/json';
          break;
        case 'yaml':
          // Would need a YAML library
          content = JSON.stringify(exportConfig, null, 2);
          mimeType = 'application/x-yaml';
          break;
        case 'toml':
          // Would need a TOML library
          content = JSON.stringify(exportConfig, null, 2);
          mimeType = 'application/toml';
          break;
        default:
          throw new Error(`Unsupported export format: ${format}`);
      }

      return new Blob([content], { type: mimeType });
    } catch (error) {
      throw error;
    }
  }

  /**
   * Import configuration
   */
  async importConfiguration(
    configData: string | Blob,
    format: 'json' | 'yaml' | 'toml' = 'json',
    validateOnly: boolean = false
  ): Promise<{ success: boolean; message: string; validation_result?: ConfigurationValidationResult }> {
    try {
      let config: SystemConfiguration;
      
      // Parse configuration data
      if (configData instanceof Blob) {
        const text = await configData.text();
        config = this.parseConfigurationData(text, format);
      } else {
        config = this.parseConfigurationData(configData, format);
      }

      // Validate configuration
      const validationResult = await this.validateConfiguration(config);
      
      if (!validationResult.is_valid) {
        return {
          success: false,
          message: 'Configuration validation failed',
          validation_result: validationResult
        };
      }

      if (validateOnly) {
        return {
          success: true,
          message: 'Configuration is valid',
          validation_result: validationResult
        };
      }

      // Apply configuration
      return await this.updateSystemConfiguration(config, 'Configuration imported');
    } catch (error) {
      return {
        success: false,
        message: `Failed to import configuration: ${error.message}`
      };
    }
  }

  /**
   * Get configuration setting value
   */
  async getSettingValue(settingKey: string): Promise<any> {
    try {
      const config = await this.getSystemConfiguration();
      return config[settingKey];
    } catch (error) {
      throw error;
    }
  }

  /**
   * Set configuration setting value
   */
  async setSettingValue(
    settingKey: string,
    value: any,
    reason?: string
  ): Promise<{ success: boolean; message: string }> {
    try {
      const updates = { [settingKey]: value };
      return await this.updateSystemConfiguration(updates, reason);
    } catch (error) {
      return {
        success: false,
        message: `Failed to set setting value: ${error.message}`
      };
    }
  }

  /**
   * Clear configuration cache
   */
  clearCache(): void {
    this.configurationCache = null;
    this.sectionsCache = [];
    this.backupListCache = [];
    this.lastConfigUpdate = 0;
    this.lastSectionsUpdate = 0;
    this.lastBackupUpdate = 0;
  }

  // Private helper methods
  private generateConfigurationSections(config: SystemConfiguration): ConfigurationSection[] {
    // This would typically come from a configuration schema
    // For now, we'll generate basic sections from the configuration keys
    const sections: ConfigurationSection[] = [];

    // Group settings by category
    const categories = new Map<string, ConfigurationSetting[]>();
    
    Object.keys(config).forEach(key => {
      const setting: ConfigurationSetting = {
        key,
        display_name: this.formatDisplayName(key),
        description: `Configuration setting for ${key}`,
        type: this.inferSettingType(config[key]),
        value: config[key],
        default_value: config[key],
        is_sensitive: this.isSensitiveKey(key),
        requires_restart: this.requiresRestart(key)
      };

      const category = this.getCategoryForKey(key);
      if (!categories.has(category)) {
        categories.set(category, []);
      }
      categories.get(category)!.push(setting);
    });

    // Create sections from categories
    categories.forEach((settings, categoryName) => {
      sections.push({
        name: categoryName.toLowerCase().replace(/\s+/g, '_'),
        display_name: categoryName,
        description: `Configuration settings for ${categoryName}`,
        settings
      });
    });

    return sections;
  }

  private formatDisplayName(key: string): string {
    return key
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .trim()
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  }

  private inferSettingType(value: any): ConfigurationSetting['type'] {
    if (typeof value === 'boolean') return 'boolean';
    if (typeof value === 'number') return 'number';
    if (Array.isArray(value)) return 'array';
    if (typeof value === 'object' && value !== null) return 'object';
    return 'string';
  }

  private isSensitiveKey(key: string): boolean {
    const sensitiveKeys = ['password', 'secret', 'key', 'token', 'auth'];
    return sensitiveKeys.some(sensitive => key.toLowerCase().includes(sensitive));
  }

  private requiresRestart(key: string): boolean {
    const restartKeys = ['port', 'host', 'database', 'network'];
    return restartKeys.some(restart => key.toLowerCase().includes(restart));
  }

  private getCategoryForKey(key: string): string {
    if (key.includes('database') || key.includes('db')) return 'Database';
    if (key.includes('network') || key.includes('port')) return 'Network';
    if (key.includes('auth') || key.includes('security')) return 'Security';
    if (key.includes('logging') || key.includes('log')) return 'Logging';
    if (key.includes('cache') || key.includes('redis')) return 'Cache';
    return 'General';
  }

  private validateSetting(key: string, value: any, rule: ValidationRule): { 
    is_valid: boolean; 
    message: string; 
    warning?: boolean 
  } {
    switch (rule.type) {
      case 'required':
        if (value === null || value === undefined || value === '') {
          return { is_valid: false, message: rule.message };
        }
        break;
      case 'min':
        if (typeof value === 'number' && value < rule.value) {
          return { is_valid: false, message: rule.message };
        }
        break;
      case 'max':
        if (typeof value === 'number' && value > rule.value) {
          return { is_valid: false, message: rule.message };
        }
        break;
      case 'pattern':
        if (typeof value === 'string' && !new RegExp(rule.value).test(value)) {
          return { is_valid: false, message: rule.message };
        }
        break;
      case 'custom':
        if (rule.validator && !rule.validator(value)) {
          return { is_valid: false, message: rule.message };
        }
        break;
    }

    return { is_valid: true, message: '' };
  }

  private filterSensitiveData(config: SystemConfiguration): SystemConfiguration {
    const filtered = { ...config };
    
    Object.keys(filtered).forEach(key => {
      if (this.isSensitiveKey(key)) {
        filtered[key] = '[REDACTED]';
      }
    });

    return filtered;
  }

  private parseConfigurationData(data: string, format: string): SystemConfiguration {
    switch (format) {
      case 'json':
        return JSON.parse(data);
      case 'yaml':
        // Would need a YAML parser
        throw new Error('YAML parsing not implemented');
      case 'toml':
        // Would need a TOML parser
        throw new Error('TOML parsing not implemented');
      default:
        throw new Error(`Unsupported configuration format: ${format}`);
    }
  }
}

// Export singleton instance
export const configService = new ConfigService();
