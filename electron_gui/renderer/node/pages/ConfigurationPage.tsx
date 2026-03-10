import React, { useState, useEffect } from 'react';

// Types
interface NodeConfiguration {
  node_settings: {
    node_name: string;
    auto_start: boolean;
    max_concurrent_sessions: number;
    session_timeout: number;
    maintenance_mode: boolean;
    log_level: 'debug' | 'info' | 'warn' | 'error';
  };
  network_settings: {
    port: number;
    max_bandwidth: number;
    enable_tor: boolean;
    tor_socks_port: number;
    enable_ipv6: boolean;
  };
  resource_settings: {
    cpu_limit: number;
    memory_limit: number;
    disk_limit: number;
    auto_scale: boolean;
    min_resources: number;
    max_resources: number;
  };
  security_settings: {
    enable_encryption: boolean;
    encryption_key: string;
    enable_authentication: boolean;
    api_key: string;
    allowed_ips: string[];
    enable_ssl: boolean;
    ssl_certificate: string;
    ssl_private_key: string;
  };
  backup_settings: {
    enable_backup: boolean;
    backup_interval: number;
    backup_retention: number;
    backup_location: string;
    enable_compression: boolean;
  };
}

interface ConfigurationPageProps {
  nodeUser: any;
  systemHealth: any;
  onRouteChange: (route: string) => void;
  onNotification: (type: 'info' | 'warning' | 'error' | 'success', message: string) => void;
}

const ConfigurationPage: React.FC<ConfigurationPageProps> = ({
  nodeUser,
  systemHealth,
  onRouteChange,
  onNotification
}) => {
  const [configuration, setConfiguration] = useState<NodeConfiguration | null>(null);
  const [originalConfiguration, setOriginalConfiguration] = useState<NodeConfiguration | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'general' | 'network' | 'resources' | 'security' | 'backup'>('general');
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    loadConfiguration();
  }, []);

  useEffect(() => {
    // Check for changes
    if (configuration && originalConfiguration) {
      const changed = JSON.stringify(configuration) !== JSON.stringify(originalConfiguration);
      setHasChanges(changed);
    }
  }, [configuration, originalConfiguration]);

  const loadConfiguration = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch('/api/node/configuration');
      if (response.ok) {
        const data = await response.json();
        setConfiguration(data);
        setOriginalConfiguration(JSON.parse(JSON.stringify(data))); // Deep copy
        onNotification('success', 'Configuration loaded successfully');
      } else {
        throw new Error('Failed to load configuration');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load configuration';
      setError(errorMessage);
      onNotification('error', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const saveConfiguration = async () => {
    try {
      setIsSaving(true);
      setError(null);

      const response = await fetch('/api/node/configuration', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(configuration),
      });

      if (response.ok) {
        setOriginalConfiguration(JSON.parse(JSON.stringify(configuration))); // Deep copy
        setHasChanges(false);
        onNotification('success', 'Configuration saved successfully');
      } else {
        throw new Error('Failed to save configuration');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save configuration';
      setError(errorMessage);
      onNotification('error', errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const resetConfiguration = () => {
    if (originalConfiguration) {
      setConfiguration(JSON.parse(JSON.stringify(originalConfiguration))); // Deep copy
      setHasChanges(false);
      onNotification('info', 'Configuration reset to last saved state');
    }
  };

  const handleConfigurationChange = (section: keyof NodeConfiguration, key: string, value: any) => {
    if (configuration) {
      setConfiguration(prev => ({
        ...prev!,
        [section]: {
          ...prev![section],
          [key]: value
        }
      }));
    }
  };

  const handleTestConnection = async () => {
    try {
      const response = await fetch('/api/node/test-connection', {
        method: 'POST',
      });

      if (response.ok) {
        onNotification('success', 'Connection test successful');
      } else {
        throw new Error('Connection test failed');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Connection test failed';
      onNotification('error', errorMessage);
    }
  };

  const handleBackupNow = async () => {
    try {
      const response = await fetch('/api/node/backup', {
        method: 'POST',
      });

      if (response.ok) {
        onNotification('success', 'Backup initiated successfully');
      } else {
        throw new Error('Backup failed');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Backup failed';
      onNotification('error', errorMessage);
    }
  };

  const renderGeneralSettings = () => {
    if (!configuration) return null;

    return (
      <div className="configuration-section">
        <h3>General Settings</h3>
        <div className="form-grid">
          <div className="form-group">
            <label>Node Name</label>
            <input
              type="text"
              value={configuration.node_settings.node_name}
              onChange={(e) => handleConfigurationChange('node_settings', 'node_name', e.target.value)}
              className="form-input"
              placeholder="Enter node name"
            />
          </div>
          <div className="form-group">
            <label>Auto Start</label>
            <input
              type="checkbox"
              checked={configuration.node_settings.auto_start}
              onChange={(e) => handleConfigurationChange('node_settings', 'auto_start', e.target.checked)}
              className="form-checkbox"
            />
          </div>
          <div className="form-group">
            <label>Max Concurrent Sessions</label>
            <input
              type="number"
              value={configuration.node_settings.max_concurrent_sessions}
              onChange={(e) => handleConfigurationChange('node_settings', 'max_concurrent_sessions', parseInt(e.target.value))}
              className="form-input"
              min="1"
              max="100"
            />
          </div>
          <div className="form-group">
            <label>Session Timeout (minutes)</label>
            <input
              type="number"
              value={configuration.node_settings.session_timeout}
              onChange={(e) => handleConfigurationChange('node_settings', 'session_timeout', parseInt(e.target.value))}
              className="form-input"
              min="1"
              max="1440"
            />
          </div>
          <div className="form-group">
            <label>Maintenance Mode</label>
            <input
              type="checkbox"
              checked={configuration.node_settings.maintenance_mode}
              onChange={(e) => handleConfigurationChange('node_settings', 'maintenance_mode', e.target.checked)}
              className="form-checkbox"
            />
          </div>
          <div className="form-group">
            <label>Log Level</label>
            <select
              value={configuration.node_settings.log_level}
              onChange={(e) => handleConfigurationChange('node_settings', 'log_level', e.target.value)}
              className="form-select"
            >
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warn">Warning</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </div>
    );
  };

  const renderNetworkSettings = () => {
    if (!configuration) return null;

    return (
      <div className="configuration-section">
        <h3>Network Settings</h3>
        <div className="form-grid">
          <div className="form-group">
            <label>Port</label>
            <input
              type="number"
              value={configuration.network_settings.port}
              onChange={(e) => handleConfigurationChange('network_settings', 'port', parseInt(e.target.value))}
              className="form-input"
              min="1024"
              max="65535"
            />
          </div>
          <div className="form-group">
            <label>Max Bandwidth (Mbps)</label>
            <input
              type="number"
              value={configuration.network_settings.max_bandwidth}
              onChange={(e) => handleConfigurationChange('network_settings', 'max_bandwidth', parseInt(e.target.value))}
              className="form-input"
              min="1"
              max="10000"
            />
          </div>
          <div className="form-group">
            <label>Enable Tor</label>
            <input
              type="checkbox"
              checked={configuration.network_settings.enable_tor}
              onChange={(e) => handleConfigurationChange('network_settings', 'enable_tor', e.target.checked)}
              className="form-checkbox"
            />
          </div>
          <div className="form-group">
            <label>Tor SOCKS Port</label>
            <input
              type="number"
              value={configuration.network_settings.tor_socks_port}
              onChange={(e) => handleConfigurationChange('network_settings', 'tor_socks_port', parseInt(e.target.value))}
              className="form-input"
              min="1024"
              max="65535"
            />
          </div>
          <div className="form-group">
            <label>Enable IPv6</label>
            <input
              type="checkbox"
              checked={configuration.network_settings.enable_ipv6}
              onChange={(e) => handleConfigurationChange('network_settings', 'enable_ipv6', e.target.checked)}
              className="form-checkbox"
            />
          </div>
        </div>
        <div className="section-actions">
          <button
            onClick={handleTestConnection}
            className="node-action-btn"
            title="Test Network Connection"
          >
            🔗 Test Connection
          </button>
        </div>
      </div>
    );
  };

  const renderResourceSettings = () => {
    if (!configuration) return null;

    return (
      <div className="configuration-section">
        <h3>Resource Settings</h3>
        <div className="form-grid">
          <div className="form-group">
            <label>CPU Limit (%)</label>
            <input
              type="number"
              value={configuration.resource_settings.cpu_limit}
              onChange={(e) => handleConfigurationChange('resource_settings', 'cpu_limit', parseInt(e.target.value))}
              className="form-input"
              min="1"
              max="100"
            />
          </div>
          <div className="form-group">
            <label>Memory Limit (GB)</label>
            <input
              type="number"
              value={configuration.resource_settings.memory_limit}
              onChange={(e) => handleConfigurationChange('resource_settings', 'memory_limit', parseInt(e.target.value))}
              className="form-input"
              min="1"
              max="128"
            />
          </div>
          <div className="form-group">
            <label>Disk Limit (GB)</label>
            <input
              type="number"
              value={configuration.resource_settings.disk_limit}
              onChange={(e) => handleConfigurationChange('resource_settings', 'disk_limit', parseInt(e.target.value))}
              className="form-input"
              min="1"
              max="1000"
            />
          </div>
          <div className="form-group">
            <label>Auto Scale</label>
            <input
              type="checkbox"
              checked={configuration.resource_settings.auto_scale}
              onChange={(e) => handleConfigurationChange('resource_settings', 'auto_scale', e.target.checked)}
              className="form-checkbox"
            />
          </div>
          <div className="form-group">
            <label>Min Resources (%)</label>
            <input
              type="number"
              value={configuration.resource_settings.min_resources}
              onChange={(e) => handleConfigurationChange('resource_settings', 'min_resources', parseInt(e.target.value))}
              className="form-input"
              min="1"
              max="100"
            />
          </div>
          <div className="form-group">
            <label>Max Resources (%)</label>
            <input
              type="number"
              value={configuration.resource_settings.max_resources}
              onChange={(e) => handleConfigurationChange('resource_settings', 'max_resources', parseInt(e.target.value))}
              className="form-input"
              min="1"
              max="100"
            />
          </div>
        </div>
      </div>
    );
  };

  const renderSecuritySettings = () => {
    if (!configuration) return null;

    return (
      <div className="configuration-section">
        <h3>Security Settings</h3>
        <div className="form-grid">
          <div className="form-group">
            <label>Enable Encryption</label>
            <input
              type="checkbox"
              checked={configuration.security_settings.enable_encryption}
              onChange={(e) => handleConfigurationChange('security_settings', 'enable_encryption', e.target.checked)}
              className="form-checkbox"
            />
          </div>
          <div className="form-group">
            <label>Encryption Key</label>
            <input
              type="password"
              value={configuration.security_settings.encryption_key}
              onChange={(e) => handleConfigurationChange('security_settings', 'encryption_key', e.target.value)}
              className="form-input"
              placeholder="Enter encryption key"
            />
          </div>
          <div className="form-group">
            <label>Enable Authentication</label>
            <input
              type="checkbox"
              checked={configuration.security_settings.enable_authentication}
              onChange={(e) => handleConfigurationChange('security_settings', 'enable_authentication', e.target.checked)}
              className="form-checkbox"
            />
          </div>
          <div className="form-group">
            <label>API Key</label>
            <input
              type="password"
              value={configuration.security_settings.api_key}
              onChange={(e) => handleConfigurationChange('security_settings', 'api_key', e.target.value)}
              className="form-input"
              placeholder="Enter API key"
            />
          </div>
          <div className="form-group">
            <label>Allowed IPs</label>
            <textarea
              value={configuration.security_settings.allowed_ips.join('\n')}
              onChange={(e) => handleConfigurationChange('security_settings', 'allowed_ips', e.target.value.split('\n'))}
              className="form-textarea"
              placeholder="Enter IP addresses, one per line"
              rows={3}
            />
          </div>
          <div className="form-group">
            <label>Enable SSL</label>
            <input
              type="checkbox"
              checked={configuration.security_settings.enable_ssl}
              onChange={(e) => handleConfigurationChange('security_settings', 'enable_ssl', e.target.checked)}
              className="form-checkbox"
            />
          </div>
          <div className="form-group">
            <label>SSL Certificate</label>
            <textarea
              value={configuration.security_settings.ssl_certificate}
              onChange={(e) => handleConfigurationChange('security_settings', 'ssl_certificate', e.target.value)}
              className="form-textarea"
              placeholder="Enter SSL certificate"
              rows={5}
            />
          </div>
          <div className="form-group">
            <label>SSL Private Key</label>
            <textarea
              value={configuration.security_settings.ssl_private_key}
              onChange={(e) => handleConfigurationChange('security_settings', 'ssl_private_key', e.target.value)}
              className="form-textarea"
              placeholder="Enter SSL private key"
              rows={5}
            />
          </div>
        </div>
      </div>
    );
  };

  const renderBackupSettings = () => {
    if (!configuration) return null;

    return (
      <div className="configuration-section">
        <h3>Backup Settings</h3>
        <div className="form-grid">
          <div className="form-group">
            <label>Enable Backup</label>
            <input
              type="checkbox"
              checked={configuration.backup_settings.enable_backup}
              onChange={(e) => handleConfigurationChange('backup_settings', 'enable_backup', e.target.checked)}
              className="form-checkbox"
            />
          </div>
          <div className="form-group">
            <label>Backup Interval (hours)</label>
            <input
              type="number"
              value={configuration.backup_settings.backup_interval}
              onChange={(e) => handleConfigurationChange('backup_settings', 'backup_interval', parseInt(e.target.value))}
              className="form-input"
              min="1"
              max="168"
            />
          </div>
          <div className="form-group">
            <label>Backup Retention (days)</label>
            <input
              type="number"
              value={configuration.backup_settings.backup_retention}
              onChange={(e) => handleConfigurationChange('backup_settings', 'backup_retention', parseInt(e.target.value))}
              className="form-input"
              min="1"
              max="365}
            />
          </div>
          <div className="form-group">
            <label>Backup Location</label>
            <input
              type="text"
              value={configuration.backup_settings.backup_location}
              onChange={(e) => handleConfigurationChange('backup_settings', 'backup_location', e.target.value)}
              className="form-input"
              placeholder="Enter backup location path"
            />
          </div>
          <div className="form-group">
            <label>Enable Compression</label>
            <input
              type="checkbox"
              checked={configuration.backup_settings.enable_compression}
              onChange={(e) => handleConfigurationChange('backup_settings', 'enable_compression', e.target.checked)}
              className="form-checkbox"
            />
          </div>
        </div>
        <div className="section-actions">
          <button
            onClick={handleBackupNow}
            className="node-action-btn"
            title="Create Backup Now"
          >
            💾 Backup Now
          </button>
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="configuration-page">
        <div className="node-loading">
          <div className="spinner"></div>
          <span>Loading configuration...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="configuration-page">
        <div className="node-error">
          <h3>Configuration Error</h3>
          <p>{error}</p>
          <button onClick={loadConfiguration} className="node-action-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="configuration-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Node Configuration</h1>
          <p className="page-subtitle">Configure your node settings and preferences</p>
        </div>
        <div className="page-actions">
          {hasChanges && (
            <button
              onClick={resetConfiguration}
              className="node-action-btn warning"
              title="Reset Changes"
            >
              ↺ Reset
            </button>
          )}
          <button
            onClick={saveConfiguration}
            className="node-action-btn"
            disabled={!hasChanges || isSaving}
            title="Save Configuration"
          >
            {isSaving ? '⏳ Saving...' : '💾 Save'}
          </button>
        </div>
      </div>

      {/* Configuration Tabs */}
      <div className="configuration-tabs">
        <button
          className={`tab-button ${activeTab === 'general' ? 'active' : ''}`}
          onClick={() => setActiveTab('general')}
        >
          General
        </button>
        <button
          className={`tab-button ${activeTab === 'network' ? 'active' : ''}`}
          onClick={() => setActiveTab('network')}
        >
          Network
        </button>
        <button
          className={`tab-button ${activeTab === 'resources' ? 'active' : ''}`}
          onClick={() => setActiveTab('resources')}
        >
          Resources
        </button>
        <button
          className={`tab-button ${activeTab === 'security' ? 'active' : ''}`}
          onClick={() => setActiveTab('security')}
        >
          Security
        </button>
        <button
          className={`tab-button ${activeTab === 'backup' ? 'active' : ''}`}
          onClick={() => setActiveTab('backup')}
        >
          Backup
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'general' && renderGeneralSettings()}
        {activeTab === 'network' && renderNetworkSettings()}
        {activeTab === 'resources' && renderResourceSettings()}
        {activeTab === 'security' && renderSecuritySettings()}
        {activeTab === 'backup' && renderBackupSettings()}
      </div>

      {/* Save Status */}
      {hasChanges && (
        <div className="save-status">
          <div className="save-indicator">
            <span className="save-icon">⚠️</span>
            <span className="save-message">You have unsaved changes</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConfigurationPage;
