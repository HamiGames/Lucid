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

interface UserProfile {
  id: string;
  email: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  avatar?: string;
  tron_address: string;
  role: string;
  status: string;
  created_at: string;
  last_login: string;
  session_count: number;
  total_sessions: number;
  total_data_processed: number;
  hardware_wallet?: {
    type: 'ledger' | 'trezor' | 'keepkey';
    device_id: string;
    public_key: string;
    is_connected: boolean;
  };
  preferences: {
    theme: string;
    language: string;
    timezone: string;
    notifications_enabled: boolean;
  };
}

interface ProfileFormData {
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  current_password: string;
  new_password: string;
  confirm_password: string;
}

interface ProfilePageProps {
  user: User | null;
  onRouteChange: (routeId: string) => void;
  onNotification: (notification: any) => void;
  apiCall: (endpoint: string, method: string, data?: any) => Promise<any>;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({
  user,
  onRouteChange,
  onNotification,
  apiCall
}) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'stats'>('profile');
  const [formData, setFormData] = useState<ProfileFormData>({
    username: '',
    first_name: '',
    last_name: '',
    email: '',
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Load user profile
  const loadProfile = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiCall('/user/profile', 'GET');
      
      if (response.success) {
        setProfile(response.profile);
        setFormData(prev => ({
          ...prev,
          username: response.profile.username || '',
          first_name: response.profile.first_name || '',
          last_name: response.profile.last_name || '',
          email: response.profile.email || ''
        }));
      } else {
        throw new Error(response.message || 'Failed to load profile');
      }
    } catch (err) {
      console.error('Failed to load profile:', err);
      setError(err instanceof Error ? err.message : 'Failed to load profile');
      onNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to load profile'
      });
    } finally {
      setLoading(false);
    }
  }, [apiCall, onNotification]);

  // Validate form data
  const validateForm = useCallback((): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.username.trim()) {
      errors.username = 'Username is required';
    } else if (formData.username.length < 3) {
      errors.username = 'Username must be at least 3 characters';
    } else if (formData.username.length > 30) {
      errors.username = 'Username must be less than 30 characters';
    }

    if (!formData.email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address';
    }

    if (formData.new_password) {
      if (formData.new_password.length < 8) {
        errors.new_password = 'Password must be at least 8 characters';
      }
      if (formData.new_password !== formData.confirm_password) {
        errors.confirm_password = 'Passwords do not match';
      }
      if (!formData.current_password) {
        errors.current_password = 'Current password is required to change password';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [formData]);

  // Handle form input changes
  const handleInputChange = useCallback((field: keyof ProfileFormData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  }, [validationErrors]);

  // Save profile changes
  const handleSaveProfile = useCallback(async () => {
    if (!validateForm()) {
      return;
    }

    try {
      setSaving(true);

      const updateData: any = {
        username: formData.username,
        first_name: formData.first_name,
        last_name: formData.last_name,
        email: formData.email
      };

      if (formData.new_password) {
        updateData.current_password = formData.current_password;
        updateData.new_password = formData.new_password;
      }

      const response = await apiCall('/user/profile', 'PUT', updateData);
      
      if (response.success) {
        onNotification({
          type: 'success',
          title: 'Profile Updated',
          message: 'Your profile has been updated successfully'
        });
        loadProfile();
        setFormData(prev => ({
          ...prev,
          current_password: '',
          new_password: '',
          confirm_password: ''
        }));
      } else {
        throw new Error(response.message || 'Failed to update profile');
      }
    } catch (err) {
      console.error('Failed to update profile:', err);
      onNotification({
        type: 'error',
        title: 'Error',
        message: err instanceof Error ? err.message : 'Failed to update profile'
      });
    } finally {
      setSaving(false);
    }
  }, [formData, validateForm, apiCall, onNotification, loadProfile]);

  // Handle avatar upload
  const handleAvatarUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) { // 5MB limit
      onNotification({
        type: 'error',
        title: 'File Too Large',
        message: 'Avatar image must be less than 5MB'
      });
      return;
    }

    if (!file.type.startsWith('image/')) {
      onNotification({
        type: 'error',
        title: 'Invalid File Type',
        message: 'Please select an image file'
      });
      return;
    }

    try {
      const formData = new FormData();
      formData.append('avatar', file);

      const response = await apiCall('/user/avatar', 'POST', formData);
      
      if (response.success) {
        onNotification({
          type: 'success',
          title: 'Avatar Updated',
          message: 'Your avatar has been updated successfully'
        });
        loadProfile();
      } else {
        throw new Error(response.message || 'Failed to update avatar');
      }
    } catch (err) {
      console.error('Failed to update avatar:', err);
      onNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to update avatar'
      });
    }
  }, [apiCall, onNotification, loadProfile]);

  // Load profile on mount
  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  if (loading) {
    return (
      <div className="user-content">
        <div className="user-page-header">
          <h1 className="user-page-title">Profile</h1>
          <p className="user-page-subtitle">Manage your account information</p>
        </div>
        <div className="user-loading">
          <div className="user-loading-spinner"></div>
          Loading profile...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="user-content">
        <div className="user-page-header">
          <h1 className="user-page-title">Profile</h1>
          <p className="user-page-subtitle">Manage your account information</p>
        </div>
        <div className="user-card">
          <div className="user-card-body">
            <div className="user-empty-state">
              <div className="user-empty-state-title">Error Loading Profile</div>
              <p className="user-empty-state-description">{error}</p>
              <button className="user-btn user-btn-primary" onClick={loadProfile}>
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'profile', label: 'Profile', icon: '👤' },
    { id: 'security', label: 'Security', icon: '🔒' },
    { id: 'stats', label: 'Statistics', icon: '📊' }
  ] as const;

  return (
    <div className="user-content">
      <div className="user-page-header">
        <h1 className="user-page-title">Profile</h1>
        <p className="user-page-subtitle">Manage your account information</p>
      </div>

      {/* Tab Navigation */}
      <div className="user-card">
        <div className="user-card-body">
          <div className="user-nav" style={{ marginBottom: '1rem' }}>
            {tabs.map(tab => (
              <button
                key={tab.id}
                className={`user-nav-item ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span style={{ marginRight: '0.5rem' }}>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && profile && (
        <div className="user-card">
          <div className="user-card-header">
            <h3 className="user-card-title">Profile Information</h3>
            <p className="user-card-subtitle">Update your personal information</p>
          </div>
          <div className="user-card-body">
            <form onSubmit={(e) => { e.preventDefault(); handleSaveProfile(); }}>
              <div style={{ display: 'grid', gap: '1.5rem' }}>
                {/* Avatar Section */}
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                  <div style={{ 
                    width: '120px', 
                    height: '120px', 
                    borderRadius: '50%', 
                    backgroundColor: 'var(--user-bg-tertiary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 1rem',
                    fontSize: '3rem',
                    color: 'var(--user-text-secondary)',
                    backgroundImage: profile.avatar ? `url(${profile.avatar})` : 'none',
                    backgroundSize: 'cover',
                    backgroundPosition: 'center'
                  }}>
                    {!profile.avatar && '👤'}
                  </div>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleAvatarUpload}
                    style={{ display: 'none' }}
                    id="avatar-upload"
                  />
                  <label htmlFor="avatar-upload" className="user-btn user-btn-secondary">
                    Change Avatar
                  </label>
                </div>

                {/* Basic Information */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="user-form-group">
                    <label className="user-form-label" htmlFor="first-name">First Name</label>
                    <input
                      type="text"
                      id="first-name"
                      className="user-form-input"
                      value={formData.first_name}
                      onChange={(e) => handleInputChange('first_name', e.target.value)}
                      placeholder="Enter your first name"
                    />
                  </div>
                  <div className="user-form-group">
                    <label className="user-form-label" htmlFor="last-name">Last Name</label>
                    <input
                      type="text"
                      id="last-name"
                      className="user-form-input"
                      value={formData.last_name}
                      onChange={(e) => handleInputChange('last_name', e.target.value)}
                      placeholder="Enter your last name"
                    />
                  </div>
                </div>

                <div className="user-form-group">
                  <label className="user-form-label" htmlFor="username">Username *</label>
                  <input
                    type="text"
                    id="username"
                    className="user-form-input"
                    value={formData.username}
                    onChange={(e) => handleInputChange('username', e.target.value)}
                    placeholder="Enter your username"
                    required
                  />
                  {validationErrors.username && (
                    <div className="user-error-message" style={{ color: 'var(--user-error)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                      {validationErrors.username}
                    </div>
                  )}
                </div>

                <div className="user-form-group">
                  <label className="user-form-label" htmlFor="email">Email *</label>
                  <input
                    type="email"
                    id="email"
                    className="user-form-input"
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    placeholder="Enter your email address"
                    required
                  />
                  {validationErrors.email && (
                    <div className="user-error-message" style={{ color: 'var(--user-error)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                      {validationErrors.email}
                    </div>
                  )}
                </div>

                {/* Account Information (Read-only) */}
                <div style={{ padding: '1rem', backgroundColor: 'var(--user-bg-secondary)', borderRadius: 'var(--user-radius-md)' }}>
                  <h4 style={{ marginBottom: '1rem', color: 'var(--user-text-primary)' }}>Account Information</h4>
                  <div style={{ display: 'grid', gap: '0.5rem', fontSize: '0.875rem' }}>
                    <div><strong>User ID:</strong> {profile.id}</div>
                    <div><strong>TRON Address:</strong> 
                      <div style={{ fontFamily: 'monospace', wordBreak: 'break-all', marginTop: '0.25rem' }}>
                        {profile.tron_address}
                      </div>
                    </div>
                    <div><strong>Role:</strong> {profile.role}</div>
                    <div><strong>Status:</strong> 
                      <span className={`user-status user-status-${profile.status === 'active' ? 'active' : 'inactive'}`} style={{ marginLeft: '0.5rem' }}>
                        <span className="user-status-dot"></span>
                        {profile.status}
                      </span>
                    </div>
                    <div><strong>Member since:</strong> {new Date(profile.created_at).toLocaleDateString()}</div>
                    <div><strong>Last login:</strong> {new Date(profile.last_login).toLocaleString()}</div>
                  </div>
                </div>
              </div>
            </form>
          </div>
          <div className="user-card-footer">
            <button
              className="user-btn user-btn-primary"
              onClick={handleSaveProfile}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      )}

      {/* Security Tab */}
      {activeTab === 'security' && profile && (
        <div className="user-card">
          <div className="user-card-header">
            <h3 className="user-card-title">Security Settings</h3>
            <p className="user-card-subtitle">Manage your password and security preferences</p>
          </div>
          <div className="user-card-body">
            <form onSubmit={(e) => { e.preventDefault(); handleSaveProfile(); }}>
              <div style={{ display: 'grid', gap: '1.5rem' }}>
                {/* Password Change Section */}
                <div>
                  <h4 style={{ marginBottom: '1rem', color: 'var(--user-text-primary)' }}>Change Password</h4>
                  <div style={{ display: 'grid', gap: '1rem' }}>
                    <div className="user-form-group">
                      <label className="user-form-label" htmlFor="current-password">Current Password</label>
                      <input
                        type="password"
                        id="current-password"
                        className="user-form-input"
                        value={formData.current_password}
                        onChange={(e) => handleInputChange('current_password', e.target.value)}
                        placeholder="Enter your current password"
                      />
                      {validationErrors.current_password && (
                        <div className="user-error-message" style={{ color: 'var(--user-error)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                          {validationErrors.current_password}
                        </div>
                      )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                      <div className="user-form-group">
                        <label className="user-form-label" htmlFor="new-password">New Password</label>
                        <input
                          type="password"
                          id="new-password"
                          className="user-form-input"
                          value={formData.new_password}
                          onChange={(e) => handleInputChange('new_password', e.target.value)}
                          placeholder="Enter new password"
                        />
                        {validationErrors.new_password && (
                          <div className="user-error-message" style={{ color: 'var(--user-error)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                            {validationErrors.new_password}
                          </div>
                        )}
                      </div>
                      <div className="user-form-group">
                        <label className="user-form-label" htmlFor="confirm-password">Confirm Password</label>
                        <input
                          type="password"
                          id="confirm-password"
                          className="user-form-input"
                          value={formData.confirm_password}
                          onChange={(e) => handleInputChange('confirm_password', e.target.value)}
                          placeholder="Confirm new password"
                        />
                        {validationErrors.confirm_password && (
                          <div className="user-error-message" style={{ color: 'var(--user-error)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                            {validationErrors.confirm_password}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Hardware Wallet Section */}
                {profile.hardware_wallet && (
                  <div>
                    <h4 style={{ marginBottom: '1rem', color: 'var(--user-text-primary)' }}>Hardware Wallet</h4>
                    <div style={{ 
                      padding: '1rem', 
                      backgroundColor: 'var(--user-bg-secondary)', 
                      borderRadius: 'var(--user-radius-md)' 
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                          <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                            {profile.hardware_wallet.type.charAt(0).toUpperCase() + profile.hardware_wallet.type.slice(1)} Wallet
                          </div>
                          <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
                            {profile.hardware_wallet.is_connected ? 'Connected' : 'Not connected'}
                          </div>
                        </div>
                        <span className={`user-status user-status-${profile.hardware_wallet.is_connected ? 'active' : 'inactive'}`}>
                          <span className="user-status-dot"></span>
                          {profile.hardware_wallet.is_connected ? 'Connected' : 'Disconnected'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </form>
          </div>
          <div className="user-card-footer">
            <button
              className="user-btn user-btn-primary"
              onClick={handleSaveProfile}
              disabled={saving || (!formData.new_password && !formData.current_password)}
            >
              {saving ? 'Saving...' : 'Update Password'}
            </button>
          </div>
        </div>
      )}

      {/* Statistics Tab */}
      {activeTab === 'stats' && profile && (
        <div className="user-card">
          <div className="user-card-header">
            <h3 className="user-card-title">Account Statistics</h3>
            <p className="user-card-subtitle">Your usage and activity statistics</p>
          </div>
          <div className="user-card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
              <div style={{ textAlign: 'center', padding: '1.5rem', backgroundColor: 'var(--user-bg-secondary)', borderRadius: 'var(--user-radius-md)' }}>
                <div style={{ fontSize: '2rem', fontWeight: '700', color: 'var(--user-primary)', marginBottom: '0.5rem' }}>
                  {profile.total_sessions}
                </div>
                <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
                  Total Sessions
                </div>
              </div>

              <div style={{ textAlign: 'center', padding: '1.5rem', backgroundColor: 'var(--user-bg-secondary)', borderRadius: 'var(--user-radius-md)' }}>
                <div style={{ fontSize: '2rem', fontWeight: '700', color: 'var(--user-success)', marginBottom: '0.5rem' }}>
                  {Math.round(profile.total_data_processed / 1024 / 1024)} MB
                </div>
                <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
                  Data Processed
                </div>
              </div>

              <div style={{ textAlign: 'center', padding: '1.5rem', backgroundColor: 'var(--user-bg-secondary)', borderRadius: 'var(--user-radius-md)' }}>
                <div style={{ fontSize: '2rem', fontWeight: '700', color: 'var(--user-warning)', marginBottom: '0.5rem' }}>
                  {Math.round((new Date().getTime() - new Date(profile.created_at).getTime()) / (1000 * 60 * 60 * 24))}
                </div>
                <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
                  Days Active
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
