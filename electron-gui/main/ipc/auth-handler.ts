// main/ipc/auth-handler.ts - Authentication IPC handlers
// Based on the electron-multi-gui-development.plan.md specifications

import { ipcMain, BrowserWindow } from 'electron';
import { WindowManager } from '../window-manager';
import { 
  RENDERER_TO_MAIN_CHANNELS, 
  MAIN_TO_RENDERER_CHANNELS,
  AuthLoginRequest,
  AuthLoginResponse,
  AuthLogoutRequest,
  AuthLogoutResponse,
  AuthVerifyTokenRequest,
  AuthVerifyTokenResponse,
  AuthStatusMessage,
  AuthTokenExpiredMessage
} from '../../shared/ipc-channels';

export function setupAuthHandlers(windowManager: WindowManager): void {
  console.log('Setting up authentication IPC handlers...');

  // Admin login handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.AUTH_LOGIN, async (event, request: AuthLoginRequest) => {
    try {
      const { email, signature } = request;
      
      // Validate input
      if (!email || !signature) {
        return {
          success: false,
          error: 'Email and signature are required'
        } as AuthLoginResponse;
      }

      // Create admin window reference for this request
      const adminWindow = windowManager.getWindow('admin');
      if (!adminWindow) {
        return {
          success: false,
          error: 'Admin window not available'
        } as AuthLoginResponse;
      }

      // Make API call to authentication service
      const response = await makeAuthRequest('POST', '/admin/login', {
        email,
        signature,
        timestamp: Date.now(),
        source: 'electron-gui'
      });

      if (response.success && response.data) {
        const { token, admin, expires_at } = response.data;
        
        // Store authentication data
        adminWindow.webContents.session.cookies.set({
          url: 'http://localhost',
          name: 'lucid_admin_token',
          value: token,
          expirationDate: Math.floor(new Date(expires_at).getTime() / 1000),
          httpOnly: true,
          secure: false
        });

        // Broadcast authentication status to all windows
        broadcastAuthStatus(windowManager, {
          authenticated: true,
          user: {
            id: admin.admin_id,
            email: admin.username,
            role: admin.role
          },
          token,
          expiresAt: expires_at
        });

        return {
          success: true,
          token,
          user: {
            id: admin.admin_id,
            email: admin.username,
            role: admin.role
          }
        } as AuthLoginResponse;
      } else {
        return {
          success: false,
          error: response.error || 'Authentication failed'
        } as AuthLoginResponse;
      }
    } catch (error) {
      console.error('Authentication login error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown authentication error'
      } as AuthLoginResponse;
    }
  });

  // Admin logout handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.AUTH_LOGOUT, async (event, request: AuthLogoutRequest) => {
    try {
      const { token } = request;
      
      // Make API call to logout endpoint
      const response = await makeAuthRequest('POST', '/admin/logout', {
        token,
        timestamp: Date.now()
      });

      // Clear authentication cookies
      const adminWindow = windowManager.getWindow('admin');
      if (adminWindow) {
        await adminWindow.webContents.session.cookies.remove('http://localhost', 'lucid_admin_token');
      }

      // Broadcast authentication status change
      broadcastAuthStatus(windowManager, {
        authenticated: false
      });

      return {
        success: true
      } as AuthLogoutResponse;
    } catch (error) {
      console.error('Authentication logout error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown logout error'
      } as AuthLogoutResponse;
    }
  });

  // Token verification handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.AUTH_VERIFY_TOKEN, async (event, request: AuthVerifyTokenRequest) => {
    try {
      const { token } = request;
      
      if (!token) {
        return {
          valid: false,
          error: 'Token is required'
        } as AuthVerifyTokenResponse;
      }

      // Make API call to verify token
      const response = await makeAuthRequest('POST', '/admin/verify-token', {
        token,
        timestamp: Date.now()
      });

      if (response.success && response.data) {
        const { valid, admin, expires_at } = response.data;
        
        return {
          valid,
          user: admin ? {
            id: admin.admin_id,
            email: admin.username,
            role: admin.role
          } : undefined,
          expiresAt: expires_at
        } as AuthVerifyTokenResponse;
      } else {
        return {
          valid: false,
          error: response.error || 'Token verification failed'
        } as AuthVerifyTokenResponse;
      }
    } catch (error) {
      console.error('Token verification error:', error);
      return {
        valid: false,
        error: error instanceof Error ? error.message : 'Unknown verification error'
      } as AuthVerifyTokenResponse;
    }
  });

  // Token refresh handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.AUTH_REFRESH_TOKEN, async (event, request: { token: string }) => {
    try {
      const { token } = request;
      
      if (!token) {
        throw new Error('Token is required');
      }

      // Make API call to refresh token
      const response = await makeAuthRequest('POST', '/admin/refresh-token', {
        token,
        timestamp: Date.now()
      });

      if (response.success && response.data) {
        const { token: newToken, admin, expires_at } = response.data;
        
        // Update authentication cookies
        const adminWindow = windowManager.getWindow('admin');
        if (adminWindow) {
          adminWindow.webContents.session.cookies.set({
            url: 'http://localhost',
            name: 'lucid_admin_token',
            value: newToken,
            expirationDate: Math.floor(new Date(expires_at).getTime() / 1000),
            httpOnly: true,
            secure: false
          });
        }

        // Broadcast updated authentication status
        broadcastAuthStatus(windowManager, {
          authenticated: true,
          user: {
            id: admin.admin_id,
            email: admin.username,
            role: admin.role
          },
          token: newToken,
          expiresAt: expires_at
        });

        return {
          success: true,
          token: newToken,
          user: {
            id: admin.admin_id,
            email: admin.username,
            role: admin.role
          },
          expiresAt: expires_at
        };
      } else {
        throw new Error(response.error || 'Token refresh failed');
      }
    } catch (error) {
      console.error('Token refresh error:', error);
      
      // Broadcast authentication failure
      broadcastAuthStatus(windowManager, {
        authenticated: false
      });

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown refresh error'
      };
    }
  });

  console.log('Authentication IPC handlers setup complete');
}

// Helper function to make authenticated API requests
async function makeAuthRequest(method: string, endpoint: string, data: any): Promise<any> {
  try {
    // Get Tor proxy configuration
    const torConfig = await getTorProxyConfig();
    
    const requestOptions = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Lucid-Electron-GUI/1.0.0'
      },
      body: method !== 'GET' ? JSON.stringify(data) : undefined
    };

    // Add proxy configuration if Tor is available
    if (torConfig) {
      requestOptions.proxy = torConfig;
    }

    const response = await fetch(`http://localhost:3000${endpoint}`, requestOptions);
    const result = await response.json();

    return {
      success: response.ok,
      data: result,
      error: response.ok ? undefined : result.error || `HTTP ${response.status}`
    };
  } catch (error) {
    console.error('API request error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown API error'
    };
  }
}

// Helper function to get Tor proxy configuration
async function getTorProxyConfig(): Promise<any> {
  try {
    // This would integrate with the TorManager to get current proxy settings
    // For now, return a default SOCKS5 proxy configuration
    return {
      protocol: 'socks5',
      host: '127.0.0.1',
      port: 9050
    };
  } catch (error) {
    console.error('Failed to get Tor proxy config:', error);
    return null;
  }
}

// Helper function to broadcast authentication status changes
function broadcastAuthStatus(windowManager: WindowManager, status: AuthStatusMessage): void {
  windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.AUTH_STATUS_CHANGED, status);
}

// Helper function to broadcast token expiration
function broadcastTokenExpired(windowManager: WindowManager, message: AuthTokenExpiredMessage): void {
  windowManager.broadcastToAllWindows(MAIN_TO_RENDERER_CHANNELS.AUTH_TOKEN_EXPIRED, message);
}

// Export helper functions for use by other modules
export { broadcastAuthStatus, broadcastTokenExpired };
