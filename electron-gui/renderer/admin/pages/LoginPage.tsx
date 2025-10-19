// electron-gui/renderer/admin/pages/LoginPage.tsx
// Admin Login Page - Admin authentication, TOTP verification, session management

import React, { useState, useEffect } from 'react';
import { CenteredLayout } from '../../common/components/Layout';
import { Modal, FormModal } from '../../common/components/Modal';
import { TorIndicator } from '../../common/components/TorIndicator';
import { useToast } from '../../common/components/Toast';
import { useApi } from '../../common/hooks/useApi';
import { useTorStatus } from '../../common/hooks/useTorStatus';
import { useLogin, useVerifyToken } from '../../common/hooks/useApi';
import { TorStatus } from '../../../shared/tor-types';

interface LoginFormData {
  email: string;
  password: string;
  totp_code?: string;
  remember_me: boolean;
}

interface AuthState {
  isAuthenticated: boolean;
  user: {
    id: string;
    email: string;
    role: string;
    name?: string;
    avatar?: string;
    last_login?: string;
  } | null;
  token: string | null;
  expires_at: string | null;
  requires_totp: boolean;
  login_attempts: number;
  locked_until: string | null;
}

interface SecurityInfo {
  last_login_ip: string;
  last_login_location: string;
  login_count: number;
  failed_attempts: number;
  account_created: string;
  password_changed: string;
  two_factor_enabled: boolean;
}

const LoginPage: React.FC = () => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    token: null,
    expires_at: null,
    requires_totp: false,
    login_attempts: 0,
    locked_until: null,
  });

  const [loginData, setLoginData] = useState<LoginFormData>({
    email: '',
    password: '',
    totp_code: '',
    remember_me: false,
  });

  const [loading, setLoading] = useState(false);
  const [showTotpModal, setShowTotpModal] = useState(false);
  const [showSecurityModal, setShowSecurityModal] = useState(false);
  const [securityInfo, setSecurityInfo] = useState<SecurityInfo | null>(null);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [showSetupTotp, setShowSetupTotp] = useState(false);

  const torStatus = useTorStatus();
  const { showToast } = useToast();

  // API hooks
  const { execute: login, loading: loginLoading } = useLogin();
  const { execute: verifyToken, loading: verifyLoading } = useVerifyToken();

  // Check for existing authentication on component mount
  useEffect(() => {
    const checkExistingAuth = async () => {
      const storedToken = localStorage.getItem('admin_token');
      if (storedToken) {
        try {
          const result = await verifyToken(storedToken);
          if (result.valid && result.user) {
            setAuthState({
              isAuthenticated: true,
              user: result.user,
              token: storedToken,
              expires_at: result.expiresAt,
              requires_totp: false,
              login_attempts: 0,
              locked_until: null,
            });
          } else {
            localStorage.removeItem('admin_token');
          }
        } catch (error) {
          localStorage.removeItem('admin_token');
        }
      }
    };

    checkExistingAuth();
  }, [verifyToken]);

  // Handle login form submission
  const handleLogin = async (data: LoginFormData) => {
    setLoading(true);
    try {
      const result = await login(data.email, data.password);
      
      if (result.requires_totp) {
        setAuthState(prev => ({
          ...prev,
          requires_totp: true,
          login_attempts: prev.login_attempts + 1,
        }));
        setShowTotpModal(true);
      } else if (result.token && result.user) {
        // Store token and update state
        localStorage.setItem('admin_token', result.token);
        setAuthState({
          isAuthenticated: true,
          user: result.user,
          token: result.token,
          expires_at: result.expiresAt,
          requires_totp: false,
          login_attempts: 0,
          locked_until: null,
        });
        
        showToast({
          type: 'success',
          title: 'Login Successful',
          message: `Welcome back, ${result.user.email}`,
        });
      }
    } catch (error) {
      setAuthState(prev => ({
        ...prev,
        login_attempts: prev.login_attempts + 1,
      }));
      
      showToast({
        type: 'error',
        title: 'Login Failed',
        message: error instanceof Error ? error.message : 'Invalid credentials',
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle TOTP verification
  const handleTotpVerification = async (totpCode: string) => {
    setLoading(true);
    try {
      const result = await login(loginData.email, loginData.password, totpCode);
      
      if (result.token && result.user) {
        localStorage.setItem('admin_token', result.token);
        setAuthState({
          isAuthenticated: true,
          user: result.user,
          token: result.token,
          expires_at: result.expiresAt,
          requires_totp: false,
          login_attempts: 0,
          locked_until: null,
        });
        
        setShowTotpModal(false);
        showToast({
          type: 'success',
          title: 'Authentication Successful',
          message: 'Two-factor authentication completed',
        });
      }
    } catch (error) {
      showToast({
        type: 'error',
        title: 'TOTP Verification Failed',
        message: error instanceof Error ? error.message : 'Invalid TOTP code',
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle logout
  const handleLogout = async () => {
    try {
      // Clear stored token
      localStorage.removeItem('admin_token');
      
      setAuthState({
        isAuthenticated: false,
        user: null,
        token: null,
        expires_at: null,
        requires_totp: false,
        login_attempts: 0,
        locked_until: null,
      });
      
      showToast({
        type: 'info',
        title: 'Logged Out',
        message: 'You have been successfully logged out',
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Logout Failed',
        message: error instanceof Error ? error.message : 'Failed to logout',
      });
    }
  };

  // Handle forgot password
  const handleForgotPassword = async (email: string) => {
    try {
      // Implement forgot password logic
      showToast({
        type: 'success',
        title: 'Password Reset Sent',
        message: 'Password reset instructions have been sent to your email',
      });
      setShowForgotPassword(false);
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Password Reset Failed',
        message: error instanceof Error ? error.message : 'Failed to send password reset',
      });
    }
  };

  // Load security information
  const loadSecurityInfo = async () => {
    try {
      // Mock security info
      setSecurityInfo({
        last_login_ip: '192.168.1.100',
        last_login_location: 'New York, NY',
        login_count: 42,
        failed_attempts: 3,
        account_created: '2024-01-01T00:00:00Z',
        password_changed: '2024-01-15T00:00:00Z',
        two_factor_enabled: true,
      });
      setShowSecurityModal(true);
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Failed to Load Security Info',
        message: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  // Check if account is locked
  const isAccountLocked = authState.locked_until && new Date(authState.locked_until) > new Date();
  const remainingAttempts = Math.max(0, 5 - authState.login_attempts);

  // If authenticated, show admin interface
  if (authState.isAuthenticated && authState.user) {
    return (
      <CenteredLayout
        title="Admin Panel"
        subtitle={`Welcome, ${authState.user.email}`}
        torStatus={torStatus}
      >
        <div className="max-w-md w-full space-y-6">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-center">
              <div className="mx-auto h-16 w-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <span className="text-2xl">👤</span>
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                {authState.user.name || authState.user.email}
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                Role: {authState.user.role}
              </p>
              <div className="flex items-center justify-center space-x-2 mb-6">
                <TorIndicator status={torStatus} size="small" />
                <span className="text-sm text-gray-600">
                  {torStatus.is_connected ? 'Secure Connection' : 'Connection Issues'}
                </span>
              </div>
            </div>
            
            <div className="space-y-3">
              <button
                onClick={() => window.location.href = '/admin/dashboard'}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
              >
                Go to Dashboard
              </button>
              
              <button
                onClick={loadSecurityInfo}
                className="w-full bg-gray-600 text-white py-2 px-4 rounded-md hover:bg-gray-700 transition-colors"
              >
                Security Information
              </button>
              
              <button
                onClick={handleLogout}
                className="w-full bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </CenteredLayout>
    );
  }

  // Show login form
  return (
    <CenteredLayout
      title="Admin Login"
      subtitle="Secure access to Lucid administration"
      torStatus={torStatus}
    >
      <div className="max-w-md w-full space-y-6">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <div className="text-center mb-6">
            <div className="mx-auto h-16 w-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
              <span className="text-2xl">🔐</span>
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Admin Access</h2>
            <p className="text-sm text-gray-600 mt-2">
              Enter your credentials to access the admin panel
            </p>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleLogin(loginData);
            }}
            className="space-y-4"
          >
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={loginData.email}
                onChange={(e) => setLoginData(prev => ({ ...prev, email: e.target.value }))}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="admin@example.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                value={loginData.password}
                onChange={(e) => setLoginData(prev => ({ ...prev, password: e.target.value }))}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter your password"
              />
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="remember_me"
                checked={loginData.remember_me}
                onChange={(e) => setLoginData(prev => ({ ...prev, remember_me: e.target.checked }))}
                className="rounded border-gray-300"
              />
              <label htmlFor="remember_me" className="ml-2 text-sm text-gray-700">
                Remember me
              </label>
            </div>

            {isAccountLocked && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <span className="text-red-400">⚠️</span>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">
                      Account Temporarily Locked
                    </h3>
                    <div className="mt-1 text-sm text-red-700">
                      Too many failed login attempts. Please try again later.
                    </div>
                  </div>
                </div>
              </div>
            )}

            {remainingAttempts > 0 && remainingAttempts < 5 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
                <div className="text-sm text-yellow-700">
                  {remainingAttempts} login attempts remaining
                </div>
              </div>
            )}

            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setShowForgotPassword(true)}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Forgot password?
              </button>
              
              <button
                type="submit"
                disabled={loading || isAccountLocked}
                className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </div>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <div className="flex items-center justify-center space-x-2">
              <TorIndicator status={torStatus} size="small" />
              <span className="text-sm text-gray-600">
                {torStatus.is_connected ? 'Secure Connection Active' : 'Establishing Secure Connection...'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* TOTP Verification Modal */}
      <FormModal
        isOpen={showTotpModal}
        onClose={() => setShowTotpModal(false)}
        onSubmit={(data) => handleTotpVerification(data.totp_code)}
        title="Two-Factor Authentication"
        submitText="Verify"
        cancelText="Cancel"
      >
        <div className="space-y-4">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
              <span className="text-xl">🔑</span>
            </div>
            <p className="text-sm text-gray-600">
              Enter the 6-digit code from your authenticator app
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              TOTP Code
            </label>
            <input
              type="text"
              value={loginData.totp_code || ''}
              onChange={(e) => setLoginData(prev => ({ ...prev, totp_code: e.target.value }))}
              required
              maxLength={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-center text-lg tracking-widest"
              placeholder="000000"
            />
          </div>
        </div>
      </FormModal>

      {/* Security Information Modal */}
      <Modal
        isOpen={showSecurityModal}
        onClose={() => setShowSecurityModal(false)}
        title="Security Information"
        size="md"
      >
        {securityInfo && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Last Login IP</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{securityInfo.last_login_ip}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Location</label>
                <p className="mt-1 text-sm text-gray-900">{securityInfo.last_login_location}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Login Count</label>
                <p className="mt-1 text-sm text-gray-900">{securityInfo.login_count}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Failed Attempts</label>
                <p className="mt-1 text-sm text-gray-900">{securityInfo.failed_attempts}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Account Created</label>
                <p className="mt-1 text-sm text-gray-900">{new Date(securityInfo.account_created).toLocaleDateString()}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Password Changed</label>
                <p className="mt-1 text-sm text-gray-900">{new Date(securityInfo.password_changed).toLocaleDateString()}</p>
              </div>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
              <span className="text-sm font-medium text-gray-700">Two-Factor Authentication</span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                securityInfo.two_factor_enabled ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
                {securityInfo.two_factor_enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </div>
        )}
      </Modal>

      {/* Forgot Password Modal */}
      <FormModal
        isOpen={showForgotPassword}
        onClose={() => setShowForgotPassword(false)}
        onSubmit={(data) => handleForgotPassword(data.email)}
        title="Forgot Password"
        submitText="Send Reset Link"
        cancelText="Cancel"
      >
        <div className="space-y-4">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
              <span className="text-xl">📧</span>
            </div>
            <p className="text-sm text-gray-600">
              Enter your email address and we'll send you a password reset link
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email Address
            </label>
            <input
              type="email"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="admin@example.com"
            />
          </div>
        </div>
      </FormModal>
    </CenteredLayout>
  );
};

export default LoginPage;
