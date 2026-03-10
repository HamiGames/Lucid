import React, { useState, useEffect, useCallback } from 'react';

interface User {
  id: string;
  email: string;
  tron_address: string;
  role: string;
  status: string;
  created_at: string;
  last_login: string;
  session_count: number;
}

interface UserSettings {
  // General Settings
  theme: 'light' | 'dark' | 'auto';
  language: string;
  timezone: string;
  date_format: string;
  time_format: '12h' | '24h';
  
  // Notification Settings
  notifications_enabled: boolean;
  email_notifications: boolean;
  push_notifications: boolean;
  session_completion_notifications: boolean;
  payment_notifications: boolean;
  security_notifications: boolean;
  
  // Session Settings
  default_encryption: boolean;
  default_auto_anchor: boolean;
  default_chunk_size: number;
  default_priority: 'low' | 'normal' | 'high';
  session_timeout_minutes: number;
  
  // Security Settings
  two_factor_enabled: boolean;
  hardware_wallet_required: boolean;
  auto_logout_minutes: number;
  require_password_for_sessions: boolean;
  
  // Privacy Settings
  data_retention_days: number;
  analytics_enabled: boolean;
  crash_reporting_enabled: boolean;
  
  // Advanced Settings
  debug_mode: boolean;
  log_level: 'error' | 'warn' | 'info' | 'debug';
  api_timeout_seconds: number;
  max_concurrent_sessions: number;
}

interface SettingsPageProps {
  user: User | null;
  onRouteChange: (routeId: string) => void;
  onNotification: (notification: any) => void;
  apiCall: (endpoint: string, method: string, data?: any) => Promise<any>;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  user,
  onRouteChange,
  onNotification,
  apiCall
}) => {
  const [settings, setSettings] = useState<UserSettings>({
    // Default values
    theme: 'auto',
    language: 'en',
    timezone: 'UTC',
    date_format: 'MM/DD/YYYY',
    time_format: '12h',
    notifications_enabled: true,
    email_notifications: true,
    push_notifications: true,
    session_completion_notifications: true,
    payment_notifications: true,
    security_notifications: true,
    default_encryption: true,
    default_auto_anchor: false,
    default_chunk_size: 1024,
    default_priority: 'normal',
    session_timeout_minutes: 60,
    two_factor_enabled: false,
    hardware_wallet_required: false,
    auto_logout_minutes: 480,
    require_password_for_sessions: false,
    data_retention_days: 30,
    analytics_enabled: true,
    crash_reporting_enabled: true,
    debug_mode: false,
    log_level: 'info',
    api_timeout_seconds: 30,
    max_concurrent_sessions: 5
  });
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'general' | 'notifications' | 'sessions' | 'security' | 'privacy' | 'advanced'>('general');

  // Load user settings
  const loadSettings = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiCall('/user/settings', 'GET');
      
      if (response.success) {
        setSettings(prev => ({
          ...prev,
          ...response.settings
        }));
      } else {
        throw new Error(response.message || 'Failed to load settings');
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
      setError(err instanceof Error ? err.message : 'Failed to load settings');
      onNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to load settings'
      });
    } finally {
      setLoading(false);
    }
  }, [apiCall, onNotification]);

  // Save user settings
  const saveSettings = useCallback(async (updatedSettings: Partial<UserSettings>) => {
    try {
      setSaving(true);

      const response = await apiCall('/user/settings', 'PUT', updatedSettings);
      
      if (response.success) {
        setSettings(prev => ({
          ...prev,
          ...updatedSettings
        }));
        onNotification({
          type: 'success',
          title: 'Settings Saved',
          message: 'Your settings have been saved successfully'
        });
      } else {
        throw new Error(response.message || 'Failed to save settings');
      }
    } catch (err) {
      console.error('Failed to save settings:', err);
      onNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to save settings'
      });
    } finally {
      setSaving(false);
    }
  }, [apiCall, onNotification]);

  // Handle setting change
  const handleSettingChange = useCallback((key: keyof UserSettings, value: any) => {
    const updatedSettings = { [key]: value };
    setSettings(prev => ({
      ...prev,
      ...updatedSettings
    }));
    saveSettings(updatedSettings);
  }, [saveSettings]);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  if (loading) {
    return (
      <div className="user-content">
        <div className="user-page-header">
          <h1 className="user-page-title">Settings</h1>
          <p className="user-page-subtitle">Configure your application preferences</p>
        </div>
        <div className="user-loading">
          <div className="user-loading-spinner"></div>
          Loading settings...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="user-content">
        <div className="user-page-header">
          <h1 className="user-page-title">Settings</h1>
          <p className="user-page-subtitle">Configure your application preferences</p>
        </div>
        <div className="user-card">
          <div className="user-card-body">
            <div className="user-empty-state">
              <div className="user-empty-state-title">Error Loading Settings</div>
              <p className="user-empty-state-description">{error}</p>
              <button className="user-btn user-btn-primary" onClick={loadSettings}>
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const sections = [
    { id: 'general', label: 'General', icon: '⚙️' },
    { id: 'notifications', label: 'Notifications', icon: '🔔' },
    { id: 'sessions', label: 'Sessions', icon: '📁' },
    { id: 'security', label: 'Security', icon: '🔒' },
    { id: 'privacy', label: 'Privacy', icon: '🛡️' },
    { id: 'advanced', label: 'Advanced', icon: '🔧' }
  ] as const;

  return (
    <div className="user-content">
      <div className="user-page-header">
        <h1 className="user-page-title">Settings</h1>
        <p className="user-page-subtitle">Configure your application preferences</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr', gap: '2rem' }}>
        {/* Settings Navigation */}
        <div className="user-card">
          <div className="user-card-body">
            <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {sections.map(section => (
                <button
                  key={section.id}
                  className={`user-nav-item ${activeSection === section.id ? 'active' : ''}`}
                  onClick={() => setActiveSection(section.id)}
                  style={{ justifyContent: 'flex-start' }}
                >
                  <span style={{ marginRight: '0.5rem' }}>{section.icon}</span>
                  {section.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Settings Content */}
        <div className="user-card">
          <div className="user-card-body">
            {/* General Settings */}
            {activeSection === 'general' && (
              <div>
                <h3 style={{ marginBottom: '1.5rem', color: 'var(--user-text-primary)' }}>
                  General Settings
                </h3>
                <div style={{ display: 'grid', gap: '1.5rem' }}>
                  <div className="user-form-group">
                    <label className="user-form-label">Theme</label>
                    <select
                      className="user-form-input user-form-select"
                      value={settings.theme}
                      onChange={(e) => handleSettingChange('theme', e.target.value)}
                    >
                      <option value="light">Light</option>
                      <option value="dark">Dark</option>
                      <option value="auto">Auto (System)</option>
                    </select>
                  </div>

                  <div className="user-form-group">
                    <label className="user-form-label">Language</label>
                    <select
                      className="user-form-input user-form-select"
                      value={settings.language}
                      onChange={(e) => handleSettingChange('language', e.target.value)}
                    >
                      <option value="en">English</option>
                      <option value="es">Español</option>
                      <option value="fr">Français</option>
                      <option value="de">Deutsch</option>
                      <option value="zh">中文</option>
                    </select>
                  </div>

                  <div className="user-form-group">
                    <label className="user-form-label">Timezone</label>
                    <select
                      className="user-form-input user-form-select"
                      value={settings.timezone}
                      onChange={(e) => handleSettingChange('timezone', e.target.value)}
                    >
                      <option value="UTC">UTC</option>
                      <option value="America/New_York">Eastern Time</option>
                      <option value="America/Chicago">Central Time</option>
                      <option value="America/Denver">Mountain Time</option>
                      <option value="America/Los_Angeles">Pacific Time</option>
                      <option value="Europe/London">London</option>
                      <option value="Europe/Paris">Paris</option>
                      <option value="Asia/Tokyo">Tokyo</option>
                    </select>
                  </div>

                  <div className="user-form-group">
                    <label className="user-form-label">Date Format</label>
                    <select
                      className="user-form-input user-form-select"
                      value={settings.date_format}
                      onChange={(e) => handleSettingChange('date_format', e.target.value)}
                    >
                      <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                      <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                      <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                    </select>
                  </div>

                  <div className="user-form-group">
                    <label className="user-form-label">Time Format</label>
                    <select
                      className="user-form-input user-form-select"
                      value={settings.time_format}
                      onChange={(e) => handleSettingChange('time_format', e.target.value)}
                    >
                      <option value="12h">12 Hour (AM/PM)</option>
                      <option value="24h">24 Hour</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Notification Settings */}
            {activeSection === 'notifications' && (
              <div>
                <h3 style={{ marginBottom: '1.5rem', color: 'var(--user-text-primary)' }}>
                  Notification Settings
                </h3>
                <div style={{ display: 'grid', gap: '1rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.notifications_enabled}
                      onChange={(e) => handleSettingChange('notifications_enabled', e.target.checked)}
                    />
                    <span>Enable notifications</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.email_notifications}
                      onChange={(e) => handleSettingChange('email_notifications', e.target.checked)}
                    />
                    <span>Email notifications</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.push_notifications}
                      onChange={(e) => handleSettingChange('push_notifications', e.target.checked)}
                    />
                    <span>Push notifications</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.session_completion_notifications}
                      onChange={(e) => handleSettingChange('session_completion_notifications', e.target.checked)}
                    />
                    <span>Session completion notifications</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.payment_notifications}
                      onChange={(e) => handleSettingChange('payment_notifications', e.target.checked)}
                    />
                    <span>Payment notifications</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.security_notifications}
                      onChange={(e) => handleSettingChange('security_notifications', e.target.checked)}
                    />
                    <span>Security notifications</span>
                  </label>
                </div>
              </div>
            )}

            {/* Session Settings */}
            {activeSection === 'sessions' && (
              <div>
                <h3 style={{ marginBottom: '1.5rem', color: 'var(--user-text-primary)' }}>
                  Session Settings
                </h3>
                <div style={{ display: 'grid', gap: '1.5rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.default_encryption}
                      onChange={(e) => handleSettingChange('default_encryption', e.target.checked)}
                    />
                    <span>Enable encryption by default</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.default_auto_anchor}
                      onChange={(e) => handleSettingChange('default_auto_anchor', e.target.checked)}
                    />
                    <span>Auto-anchor to blockchain by default</span>
                  </label>

                  <div className="user-form-group">
                    <label className="user-form-label">Default Chunk Size (bytes)</label>
                    <select
                      className="user-form-input user-form-select"
                      value={settings.default_chunk_size}
                      onChange={(e) => handleSettingChange('default_chunk_size', parseInt(e.target.value))}
                    >
                      <option value={512}>512 bytes</option>
                      <option value={1024}>1 KB</option>
                      <option value={2048}>2 KB</option>
                      <option value={4096}>4 KB</option>
                      <option value={8192}>8 KB</option>
                    </select>
                  </div>

                  <div className="user-form-group">
                    <label className="user-form-label">Default Priority</label>
                    <select
                      className="user-form-input user-form-select"
                      value={settings.default_priority}
                      onChange={(e) => handleSettingChange('default_priority', e.target.value)}
                    >
                      <option value="low">Low</option>
                      <option value="normal">Normal</option>
                      <option value="high">High</option>
                    </select>
                  </div>

                  <div className="user-form-group">
                    <label className="user-form-label">Session Timeout (minutes)</label>
                    <input
                      type="number"
                      className="user-form-input"
                      value={settings.session_timeout_minutes}
                      onChange={(e) => handleSettingChange('session_timeout_minutes', parseInt(e.target.value))}
                      min="1"
                      max="1440"
                    />
                  </div>

                  <div className="user-form-group">
                    <label className="user-form-label">Max Concurrent Sessions</label>
                    <input
                      type="number"
                      className="user-form-input"
                      value={settings.max_concurrent_sessions}
                      onChange={(e) => handleSettingChange('max_concurrent_sessions', parseInt(e.target.value))}
                      min="1"
                      max="10"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Security Settings */}
            {activeSection === 'security' && (
              <div>
                <h3 style={{ marginBottom: '1.5rem', color: 'var(--user-text-primary)' }}>
                  Security Settings
                </h3>
                <div style={{ display: 'grid', gap: '1rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.two_factor_enabled}
                      onChange={(e) => handleSettingChange('two_factor_enabled', e.target.checked)}
                    />
                    <span>Enable two-factor authentication</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.hardware_wallet_required}
                      onChange={(e) => handleSettingChange('hardware_wallet_required', e.target.checked)}
                    />
                    <span>Require hardware wallet for transactions</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.require_password_for_sessions}
                      onChange={(e) => handleSettingChange('require_password_for_sessions', e.target.checked)}
                    />
                    <span>Require password for session operations</span>
                  </label>

                  <div className="user-form-group">
                    <label className="user-form-label">Auto-logout after (minutes)</label>
                    <input
                      type="number"
                      className="user-form-input"
                      value={settings.auto_logout_minutes}
                      onChange={(e) => handleSettingChange('auto_logout_minutes', parseInt(e.target.value))}
                      min="5"
                      max="1440"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Privacy Settings */}
            {activeSection === 'privacy' && (
              <div>
                <h3 style={{ marginBottom: '1.5rem', color: 'var(--user-text-primary)' }}>
                  Privacy Settings
                </h3>
                <div style={{ display: 'grid', gap: '1.5rem' }}>
                  <div className="user-form-group">
                    <label className="user-form-label">Data Retention (days)</label>
                    <input
                      type="number"
                      className="user-form-input"
                      value={settings.data_retention_days}
                      onChange={(e) => handleSettingChange('data_retention_days', parseInt(e.target.value))}
                      min="1"
                      max="365"
                    />
                  </div>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.analytics_enabled}
                      onChange={(e) => handleSettingChange('analytics_enabled', e.target.checked)}
                    />
                    <span>Enable analytics and usage statistics</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.crash_reporting_enabled}
                      onChange={(e) => handleSettingChange('crash_reporting_enabled', e.target.checked)}
                    />
                    <span>Enable crash reporting</span>
                  </label>
                </div>
              </div>
            )}

            {/* Advanced Settings */}
            {activeSection === 'advanced' && (
              <div>
                <h3 style={{ marginBottom: '1.5rem', color: 'var(--user-text-primary)' }}>
                  Advanced Settings
                </h3>
                <div style={{ display: 'grid', gap: '1.5rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={settings.debug_mode}
                      onChange={(e) => handleSettingChange('debug_mode', e.target.checked)}
                    />
                    <span>Enable debug mode</span>
                  </label>

                  <div className="user-form-group">
                    <label className="user-form-label">Log Level</label>
                    <select
                      className="user-form-input user-form-select"
                      value={settings.log_level}
                      onChange={(e) => handleSettingChange('log_level', e.target.value)}
                    >
                      <option value="error">Error</option>
                      <option value="warn">Warning</option>
                      <option value="info">Info</option>
                      <option value="debug">Debug</option>
                    </select>
                  </div>

                  <div className="user-form-group">
                    <label className="user-form-label">API Timeout (seconds)</label>
                    <input
                      type="number"
                      className="user-form-input"
                      value={settings.api_timeout_seconds}
                      onChange={(e) => handleSettingChange('api_timeout_seconds', parseInt(e.target.value))}
                      min="5"
                      max="300"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Save Status */}
      {saving && (
        <div style={{ position: 'fixed', bottom: '2rem', right: '2rem', backgroundColor: 'var(--user-bg-primary)', padding: '1rem', borderRadius: 'var(--user-radius-md)', boxShadow: 'var(--user-shadow-lg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div className="user-loading-spinner" style={{ width: '1rem', height: '1rem' }}></div>
            Saving settings...
          </div>
        </div>
      )}
    </div>
  );
};
