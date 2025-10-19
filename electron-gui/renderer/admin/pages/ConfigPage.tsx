// electron-gui/renderer/admin/pages/ConfigPage.tsx
// Admin Configuration Page - System configuration editor, backup/restore functionality

import React, { useState, useEffect } from 'react';
import { DashboardLayout, GridLayout, CardLayout } from '../../common/components/Layout';
import { Modal, FormModal, ConfirmModal } from '../../common/components/Modal';
import { TorIndicator } from '../../common/components/TorIndicator';
import { useToast } from '../../common/components/Toast';
import { useApi } from '../../common/hooks/useApi';
import { useTorStatus } from '../../common/hooks/useTorStatus';
import { TorStatus } from '../../../shared/tor-types';

interface SystemConfig {
  // Tor Configuration
  tor: {
    socks_port: number;
    control_port: number;
    data_dir: string;
    bootstrap_timeout: number;
    circuit_build_timeout: number;
    exit_nodes: string[];
    entry_nodes: string[];
    strict_nodes: boolean;
    exclude_nodes: string[];
  };
  
  // API Configuration
  api: {
    gateway_port: number;
    gateway_https_port: number;
    admin_port: number;
    blockchain_port: number;
    session_port: number;
    node_port: number;
    auth_port: number;
    payment_port: number;
    timeout: number;
    rate_limit: number;
  };
  
  // Database Configuration
  database: {
    host: string;
    port: number;
    name: string;
    username: string;
    ssl_enabled: boolean;
    connection_pool_size: number;
    query_timeout: number;
  };
  
  // Security Configuration
  security: {
    jwt_secret: string;
    jwt_expiry: number;
    encryption_key: string;
    totp_issuer: string;
    password_min_length: number;
    max_login_attempts: number;
    lockout_duration: number;
  };
  
  // System Configuration
  system: {
    log_level: 'debug' | 'info' | 'warn' | 'error';
    max_log_size: number;
    log_retention_days: number;
    backup_enabled: boolean;
    backup_interval: number;
    backup_retention_days: number;
    maintenance_mode: boolean;
  };
  
  // Node Configuration
  nodes: {
    min_poot_score: number;
    max_nodes_per_pool: number;
    node_check_interval: number;
    resource_check_interval: number;
    auto_scale_enabled: boolean;
  };
  
  // Session Configuration
  sessions: {
    max_duration_minutes: number;
    max_chunk_size: number;
    compression_enabled: boolean;
    encryption_enabled: boolean;
    auto_anchor_enabled: boolean;
    anchor_interval_minutes: number;
  };
}

interface BackupInfo {
  id: string;
  name: string;
  created_at: string;
  size: number;
  type: 'full' | 'incremental';
  status: 'completed' | 'failed' | 'in_progress';
}

interface ConfigSection {
  id: string;
  title: string;
  description: string;
  icon: string;
  config: Partial<SystemConfig>;
}

const ConfigPage: React.FC = () => {
  const [config, setConfig] = useState<SystemConfig>({
    tor: {
      socks_port: 9050,
      control_port: 9051,
      data_dir: './tor-data',
      bootstrap_timeout: 60000,
      circuit_build_timeout: 60000,
      exit_nodes: [],
      entry_nodes: [],
      strict_nodes: false,
      exclude_nodes: [],
    },
    api: {
      gateway_port: 8080,
      gateway_https_port: 8081,
      admin_port: 8083,
      blockchain_port: 8084,
      session_port: 8087,
      node_port: 8095,
      auth_port: 8089,
      payment_port: 8085,
      timeout: 30000,
      rate_limit: 1000,
    },
    database: {
      host: 'localhost',
      port: 5432,
      name: 'lucid_db',
      username: 'lucid_user',
      ssl_enabled: true,
      connection_pool_size: 10,
      query_timeout: 5000,
    },
    security: {
      jwt_secret: '***HIDDEN***',
      jwt_expiry: 3600,
      encryption_key: '***HIDDEN***',
      totp_issuer: 'Lucid System',
      password_min_length: 8,
      max_login_attempts: 5,
      lockout_duration: 900,
    },
    system: {
      log_level: 'info',
      max_log_size: 10485760,
      log_retention_days: 30,
      backup_enabled: true,
      backup_interval: 86400,
      backup_retention_days: 7,
      maintenance_mode: false,
    },
    nodes: {
      min_poot_score: 0.5,
      max_nodes_per_pool: 10,
      node_check_interval: 300,
      resource_check_interval: 60,
      auto_scale_enabled: true,
    },
    sessions: {
      max_duration_minutes: 1440,
      max_chunk_size: 1048576,
      compression_enabled: true,
      encryption_enabled: true,
      auto_anchor_enabled: true,
      anchor_interval_minutes: 60,
    },
  });

  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showBackupModal, setShowBackupModal] = useState(false);
  const [showRestoreModal, setShowRestoreModal] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingAction, setPendingAction] = useState<() => void>(() => {});
  const [confirmMessage, setConfirmMessage] = useState('');
  const [editingSection, setEditingSection] = useState<string | null>(null);

  const torStatus = useTorStatus();
  const { showToast } = useToast();

  const configSections: ConfigSection[] = [
    {
      id: 'tor',
      title: 'Tor Configuration',
      description: 'Tor network connection settings',
      icon: '🔒',
      config: { tor: config.tor },
    },
    {
      id: 'api',
      title: 'API Configuration',
      description: 'API gateway and service ports',
      icon: '🌐',
      config: { api: config.api },
    },
    {
      id: 'database',
      title: 'Database Configuration',
      description: 'Database connection and settings',
      icon: '🗄️',
      config: { database: config.database },
    },
    {
      id: 'security',
      title: 'Security Configuration',
      description: 'Authentication and encryption settings',
      icon: '🛡️',
      config: { security: config.security },
    },
    {
      id: 'system',
      title: 'System Configuration',
      description: 'Logging, backup, and maintenance settings',
      icon: '⚙️',
      config: { system: config.system },
    },
    {
      id: 'nodes',
      title: 'Node Configuration',
      description: 'Node management and scaling settings',
      icon: '🖥️',
      config: { nodes: config.nodes },
    },
    {
      id: 'sessions',
      title: 'Session Configuration',
      description: 'Session management and anchoring settings',
      icon: '📊',
      config: { sessions: config.sessions },
    },
  ];

  useEffect(() => {
    // Mock loading configuration and backups
    setTimeout(() => {
      setBackups([
        {
          id: 'backup_001',
          name: 'System Backup 2024-01-15',
          created_at: new Date(Date.now() - 86400000).toISOString(),
          size: 1073741824,
          type: 'full',
          status: 'completed',
        },
        {
          id: 'backup_002',
          name: 'Incremental Backup 2024-01-16',
          created_at: new Date(Date.now() - 43200000).toISOString(),
          size: 134217728,
          type: 'incremental',
          status: 'completed',
        },
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  const handleConfigChange = (section: string, key: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section as keyof SystemConfig],
        [key]: value,
      },
    }));
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      // Implement config save logic
      await new Promise(resolve => setTimeout(resolve, 2000)); // Mock delay
      
      showToast({
        type: 'success',
        title: 'Configuration Saved',
        message: 'System configuration has been updated successfully',
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Save Failed',
        message: error instanceof Error ? error.message : 'Failed to save configuration',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleResetConfig = () => {
    setConfirmMessage('Are you sure you want to reset all configuration to defaults? This action cannot be undone.');
    setPendingAction(() => () => {
      // Reset to default config
      showToast({
        type: 'success',
        title: 'Configuration Reset',
        message: 'Configuration has been reset to defaults',
      });
    });
    setShowConfirmModal(true);
  };

  const handleCreateBackup = () => {
    setShowBackupModal(true);
  };

  const handleRestoreBackup = (backup: BackupInfo) => {
    setConfirmMessage(`Are you sure you want to restore from backup "${backup.name}"? This will overwrite the current configuration.`);
    setPendingAction(() => () => {
      // Implement restore logic
      showToast({
        type: 'success',
        title: 'Backup Restored',
        message: `Configuration has been restored from ${backup.name}`,
      });
    });
    setShowConfirmModal(true);
  };

  const handleDeleteBackup = (backup: BackupInfo) => {
    setConfirmMessage(`Are you sure you want to delete backup "${backup.name}"? This action cannot be undone.`);
    setPendingAction(() => () => {
      // Implement delete logic
      setBackups(prev => prev.filter(b => b.id !== backup.id));
      showToast({
        type: 'success',
        title: 'Backup Deleted',
        message: `Backup ${backup.name} has been deleted`,
      });
    });
    setShowConfirmModal(true);
  };

  const confirmAction = () => {
    pendingAction();
    setShowConfirmModal(false);
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const renderConfigSection = (section: ConfigSection) => {
    const sectionConfig = config[section.id as keyof SystemConfig] as any;
    
    return (
      <CardLayout
        key={section.id}
        title={section.title}
        subtitle={section.description}
        className="bg-white border border-gray-200"
        actions={
          <button
            onClick={() => setEditingSection(editingSection === section.id ? null : section.id)}
            className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
          >
            {editingSection === section.id ? 'Cancel' : 'Edit'}
          </button>
        }
      >
        <div className="space-y-4">
          {editingSection === section.id ? (
            <div className="space-y-3">
              {Object.entries(sectionConfig).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-700 capitalize">
                    {key.replace(/_/g, ' ')}
                  </label>
                  <div className="flex-1 max-w-xs ml-4">
                    {typeof value === 'boolean' ? (
                      <input
                        type="checkbox"
                        checked={value as boolean}
                        onChange={(e) => handleConfigChange(section.id, key, e.target.checked)}
                        className="rounded border-gray-300"
                      />
                    ) : typeof value === 'number' ? (
                      <input
                        type="number"
                        value={value as number}
                        onChange={(e) => handleConfigChange(section.id, key, Number(e.target.value))}
                        className="w-full px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : Array.isArray(value) ? (
                      <input
                        type="text"
                        value={(value as string[]).join(', ')}
                        onChange={(e) => handleConfigChange(section.id, key, e.target.value.split(',').map(s => s.trim()))}
                        className="w-full px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Comma-separated values"
                      />
                    ) : key.includes('secret') || key.includes('key') ? (
                      <input
                        type="password"
                        value="***HIDDEN***"
                        disabled
                        className="w-full px-3 py-1 border border-gray-300 rounded text-sm bg-gray-50"
                      />
                    ) : (
                      <input
                        type="text"
                        value={value as string}
                        onChange={(e) => handleConfigChange(section.id, key, e.target.value)}
                        className="w-full px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {Object.entries(sectionConfig).slice(0, 5).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                  <span className="font-mono text-gray-900">
                    {typeof value === 'boolean' ? (value ? 'Yes' : 'No') :
                     Array.isArray(value) ? `${(value as any[]).length} items` :
                     key.includes('secret') || key.includes('key') ? '***HIDDEN***' :
                     String(value)}
                  </span>
                </div>
              ))}
              {Object.keys(sectionConfig).length > 5 && (
                <div className="text-xs text-gray-500">
                  +{Object.keys(sectionConfig).length - 5} more settings
                </div>
              )}
            </div>
          )}
        </div>
      </CardLayout>
    );
  };

  if (loading) {
    return (
      <DashboardLayout
        title="System Configuration"
        torStatus={torStatus}
        headerActions={
          <div className="flex items-center space-x-4">
            <TorIndicator status={torStatus} size="small" />
          </div>
        }
      >
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading configuration...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="System Configuration"
      torStatus={torStatus}
      headerActions={
        <div className="flex items-center space-x-4">
          <button
            onClick={handleSaveConfig}
            disabled={saving}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save Config'}
          </button>
          <button
            onClick={handleResetConfig}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
          >
            Reset to Defaults
          </button>
          <TorIndicator status={torStatus} size="small" />
        </div>
      }
    >
      <div className="space-y-6">
        {/* Configuration Sections */}
        <GridLayout columns={2} gap="lg">
          {configSections.map(renderConfigSection)}
        </GridLayout>

        {/* Backup & Restore */}
        <CardLayout
          title="Backup & Restore"
          subtitle="System backup management"
          className="bg-white border border-gray-200"
          actions={
            <button
              onClick={handleCreateBackup}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Create Backup
            </button>
          }
        >
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {backups.map((backup) => (
                <div key={backup.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-gray-900">{backup.name}</h4>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      backup.status === 'completed' ? 'bg-green-100 text-green-800' :
                      backup.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {backup.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <div>Type: {backup.type}</div>
                    <div>Size: {formatBytes(backup.size)}</div>
                    <div>Created: {formatDate(backup.created_at)}</div>
                  </div>
                  <div className="flex space-x-2 mt-3">
                    <button
                      onClick={() => handleRestoreBackup(backup)}
                      className="flex-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition-colors"
                    >
                      Restore
                    </button>
                    <button
                      onClick={() => handleDeleteBackup(backup)}
                      className="flex-1 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {backups.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-2">💾</div>
                <p>No backups available</p>
                <p className="text-sm">Create your first backup to get started</p>
              </div>
            )}
          </div>
        </CardLayout>

        {/* System Status */}
        <CardLayout
          title="System Status"
          subtitle="Current system state and health"
          className="bg-white border border-gray-200"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${config.system.maintenance_mode ? 'bg-yellow-500' : 'bg-green-500'}`}></div>
              <span className="text-sm font-medium">Maintenance Mode: {config.system.maintenance_mode ? 'Enabled' : 'Disabled'}</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${config.system.backup_enabled ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm font-medium">Auto Backup: {config.system.backup_enabled ? 'Enabled' : 'Disabled'}</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${torStatus.is_connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm font-medium">Tor Connection: {torStatus.is_connected ? 'Connected' : 'Disconnected'}</span>
            </div>
          </div>
        </CardLayout>
      </div>

      {/* Create Backup Modal */}
      <FormModal
        isOpen={showBackupModal}
        onClose={() => setShowBackupModal(false)}
        onSubmit={(data) => {
          // Implement backup creation
          const newBackup: BackupInfo = {
            id: `backup_${Date.now()}`,
            name: data.name,
            created_at: new Date().toISOString(),
            size: Math.floor(Math.random() * 1000000000),
            type: data.type,
            status: 'completed',
          };
          setBackups(prev => [newBackup, ...prev]);
          setShowBackupModal(false);
          showToast({
            type: 'success',
            title: 'Backup Created',
            message: `Backup "${data.name}" has been created successfully`,
          });
        }}
        title="Create System Backup"
        submitText="Create Backup"
        cancelText="Cancel"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Backup Name</label>
            <input
              type="text"
              defaultValue={`System Backup ${new Date().toLocaleDateString()}`}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Backup Type</label>
            <select
              defaultValue="full"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="full">Full Backup</option>
              <option value="incremental">Incremental Backup</option>
            </select>
          </div>
        </div>
      </FormModal>

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={confirmAction}
        title="Confirm Action"
        message={confirmMessage}
        confirmText="Confirm"
        cancelText="Cancel"
        type="warning"
      />
    </DashboardLayout>
  );
};

export default ConfigPage;
