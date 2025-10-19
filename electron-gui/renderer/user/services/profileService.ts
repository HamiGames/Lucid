import { LucidAPIClient } from '../../../shared/api-client';

export interface UserProfile {
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

export interface ProfileUpdateRequest {
  username?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  avatar?: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface UserSettings {
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

export interface UserActivity {
  id: string;
  type: 'login' | 'logout' | 'session_created' | 'session_completed' | 'payment_made' | 'settings_changed';
  description: string;
  timestamp: string;
  ip_address?: string;
  user_agent?: string;
  metadata?: Record<string, any>;
}

export interface UserStatistics {
  total_sessions: number;
  active_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  anchored_sessions: number;
  total_data_processed: number;
  total_payments_made: number;
  total_payments_received: number;
  account_age_days: number;
  last_activity: string;
  average_session_duration: number;
  most_active_day: string;
  preferred_chunk_size: number;
}

class ProfileService {
  private apiClient: LucidAPIClient;

  constructor() {
    this.apiClient = new LucidAPIClient('/api/user');
  }

  // Get user profile
  async getProfile(): Promise<UserProfile> {
    try {
      const response = await this.apiClient.get('/profile');
      return response.profile;
    } catch (error) {
      console.error('Failed to get profile:', error);
      throw error;
    }
  }

  // Update user profile
  async updateProfile(updates: ProfileUpdateRequest): Promise<UserProfile> {
    try {
      const response = await this.apiClient.put('/profile', updates);
      return response.profile;
    } catch (error) {
      console.error('Failed to update profile:', error);
      throw error;
    }
  }

  // Change password
  async changePassword(request: PasswordChangeRequest): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post('/profile/password', request);
      return response;
    } catch (error) {
      console.error('Failed to change password:', error);
      throw error;
    }
  }

  // Upload avatar
  async uploadAvatar(file: File): Promise<{
    success: boolean;
    avatar_url: string;
    message: string;
  }> {
    try {
      const formData = new FormData();
      formData.append('avatar', file);

      const response = await this.apiClient.post('/profile/avatar', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response;
    } catch (error) {
      console.error('Failed to upload avatar:', error);
      throw error;
    }
  }

  // Delete avatar
  async deleteAvatar(): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.delete('/profile/avatar');
      return response;
    } catch (error) {
      console.error('Failed to delete avatar:', error);
      throw error;
    }
  }

  // Get user settings
  async getSettings(): Promise<UserSettings> {
    try {
      const response = await this.apiClient.get('/profile/settings');
      return response.settings;
    } catch (error) {
      console.error('Failed to get settings:', error);
      throw error;
    }
  }

  // Update user settings
  async updateSettings(settings: Partial<UserSettings>): Promise<{
    success: boolean;
    message: string;
    settings: UserSettings;
  }> {
    try {
      const response = await this.apiClient.put('/profile/settings', settings);
      return response;
    } catch (error) {
      console.error('Failed to update settings:', error);
      throw error;
    }
  }

  // Reset settings to defaults
  async resetSettings(): Promise<{
    success: boolean;
    message: string;
    settings: UserSettings;
  }> {
    try {
      const response = await this.apiClient.post('/profile/settings/reset');
      return response;
    } catch (error) {
      console.error('Failed to reset settings:', error);
      throw error;
    }
  }

  // Get user activity log
  async getActivityLog(limit: number = 50, offset: number = 0): Promise<{
    activities: UserActivity[];
    total_count: number;
    has_more: boolean;
  }> {
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString()
      });

      const response = await this.apiClient.get(`/profile/activity?${params}`);
      return response;
    } catch (error) {
      console.error('Failed to get activity log:', error);
      throw error;
    }
  }

  // Get user statistics
  async getStatistics(): Promise<UserStatistics> {
    try {
      const response = await this.apiClient.get('/profile/statistics');
      return response.statistics;
    } catch (error) {
      console.error('Failed to get statistics:', error);
      throw error;
    }
  }

  // Enable two-factor authentication
  async enableTwoFactor(): Promise<{
    success: boolean;
    qr_code: string;
    secret_key: string;
    backup_codes: string[];
  }> {
    try {
      const response = await this.apiClient.post('/profile/2fa/enable');
      return response;
    } catch (error) {
      console.error('Failed to enable 2FA:', error);
      throw error;
    }
  }

  // Verify two-factor authentication setup
  async verifyTwoFactorSetup(code: string): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post('/profile/2fa/verify', { code });
      return response;
    } catch (error) {
      console.error('Failed to verify 2FA setup:', error);
      throw error;
    }
  }

  // Disable two-factor authentication
  async disableTwoFactor(password: string): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post('/profile/2fa/disable', { password });
      return response;
    } catch (error) {
      console.error('Failed to disable 2FA:', error);
      throw error;
    }
  }

  // Get backup codes
  async getBackupCodes(): Promise<{
    backup_codes: string[];
    remaining_codes: number;
  }> {
    try {
      const response = await this.apiClient.get('/profile/2fa/backup-codes');
      return response;
    } catch (error) {
      console.error('Failed to get backup codes:', error);
      throw error;
    }
  }

  // Regenerate backup codes
  async regenerateBackupCodes(): Promise<{
    success: boolean;
    backup_codes: string[];
    message: string;
  }> {
    try {
      const response = await this.apiClient.post('/profile/2fa/regenerate-codes');
      return response;
    } catch (error) {
      console.error('Failed to regenerate backup codes:', error);
      throw error;
    }
  }

  // Export user data
  async exportUserData(): Promise<Blob> {
    try {
      const response = await this.apiClient.get('/profile/export', {
        responseType: 'blob'
      });
      return response;
    } catch (error) {
      console.error('Failed to export user data:', error);
      throw error;
    }
  }

  // Delete user account
  async deleteAccount(password: string, confirmation: string): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post('/profile/delete', {
        password,
        confirmation
      });
      return response;
    } catch (error) {
      console.error('Failed to delete account:', error);
      throw error;
    }
  }

  // Get account security status
  async getSecurityStatus(): Promise<{
    password_strength: 'weak' | 'medium' | 'strong';
    two_factor_enabled: boolean;
    hardware_wallet_connected: boolean;
    last_password_change: string;
    login_attempts: number;
    security_score: number;
    recommendations: string[];
  }> {
    try {
      const response = await this.apiClient.get('/profile/security');
      return response.security;
    } catch (error) {
      console.error('Failed to get security status:', error);
      throw error;
    }
  }

  // Update login sessions
  async getActiveSessions(): Promise<Array<{
    id: string;
    device_info: string;
    ip_address: string;
    location?: string;
    created_at: string;
    last_activity: string;
    current: boolean;
  }>> {
    try {
      const response = await this.apiClient.get('/profile/sessions');
      return response.sessions;
    } catch (error) {
      console.error('Failed to get active sessions:', error);
      throw error;
    }
  }

  // Terminate session
  async terminateSession(sessionId: string): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.delete(`/profile/sessions/${sessionId}`);
      return response;
    } catch (error) {
      console.error('Failed to terminate session:', error);
      throw error;
    }
  }

  // Terminate all other sessions
  async terminateAllOtherSessions(): Promise<{
    success: boolean;
    terminated_count: number;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post('/profile/sessions/terminate-all');
      return response;
    } catch (error) {
      console.error('Failed to terminate all other sessions:', error);
      throw error;
    }
  }

  // Validate email
  async validateEmail(email: string): Promise<{
    valid: boolean;
    available: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post('/profile/validate-email', { email });
      return response;
    } catch (error) {
      console.error('Failed to validate email:', error);
      throw error;
    }
  }

  // Validate username
  async validateUsername(username: string): Promise<{
    valid: boolean;
    available: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post('/profile/validate-username', { username });
      return response;
    } catch (error) {
      console.error('Failed to validate username:', error);
      throw error;
    }
  }
}

export const profileService = new ProfileService();
