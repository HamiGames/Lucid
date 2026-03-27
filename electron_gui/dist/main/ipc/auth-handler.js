"use strict";
// main/ipc/auth-handler.ts - Authentication IPC handlers
// Based on the electron-multi-gui-development.plan.md specifications
Object.defineProperty(exports, "__esModule", { value: true });
exports.broadcastTokenExpired = exports.broadcastAuthStatus = exports.setupAuthHandlers = void 0;
const electron_1 = require("electron");
const ipc_channels_1 = require("../../shared/ipc-channels");
function setupAuthHandlers(windowManager) {
    console.log('Setting up authentication IPC handlers...');
    // Admin login handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.AUTH_LOGIN, async (event, request) => {
        try {
            const { email, signature } = request;
            // Validate input
            if (!email || !signature) {
                return {
                    success: false,
                    error: 'Email and signature are required'
                };
            }
            // Create admin window reference for this request
            const adminWindow = windowManager.getWindow('admin');
            if (!adminWindow) {
                return {
                    success: false,
                    error: 'Admin window not available'
                };
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
                adminWindow.window.webContents.session.cookies.set({
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
                };
            }
            else {
                return {
                    success: false,
                    error: response.error || 'Authentication failed'
                };
            }
        }
        catch (error) {
            console.error('Authentication login error:', error);
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Unknown authentication error'
            };
        }
    });
    // Admin logout handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.AUTH_LOGOUT, async (event, request) => {
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
                await adminWindow.window.webContents.session.cookies.remove('http://localhost', 'lucid_admin_token');
            }
            // Broadcast authentication status change
            broadcastAuthStatus(windowManager, {
                authenticated: false
            });
            return {
                success: true
            };
        }
        catch (error) {
            console.error('Authentication logout error:', error);
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Unknown logout error'
            };
        }
    });
    // Token verification handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.AUTH_VERIFY_TOKEN, async (event, request) => {
        try {
            const { token } = request;
            if (!token) {
                return {
                    success: false,
                    error: 'Token is required'
                };
            }
            // Make API call to verify token
            const response = await makeAuthRequest('POST', '/admin/verify-token', {
                token,
                timestamp: Date.now()
            });
            if (response.success && response.data) {
                const { valid, admin, expires_at } = response.data;
                return {
                    success: !!valid,
                    user: admin ? {
                        id: admin.admin_id,
                        email: admin.username,
                        role: admin.role
                    } : undefined,
                    expiresAt: expires_at
                };
            }
            else {
                return {
                    success: false,
                    error: response.error || 'Token verification failed'
                };
            }
        }
        catch (error) {
            console.error('Token verification error:', error);
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Unknown verification error'
            };
        }
    });
    // Token refresh handler
    electron_1.ipcMain.handle(ipc_channels_1.RENDERER_TO_MAIN_CHANNELS.AUTH_REFRESH_TOKEN, async (event, request) => {
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
                    adminWindow.window.webContents.session.cookies.set({
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
            }
            else {
                throw new Error(response.error || 'Token refresh failed');
            }
        }
        catch (error) {
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
exports.setupAuthHandlers = setupAuthHandlers;
// Helper function to make authenticated API requests
async function makeAuthRequest(method, endpoint, data) {
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
    }
    catch (error) {
        console.error('API request error:', error);
        return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown API error'
        };
    }
}
// Helper function to get Tor proxy configuration
async function getTorProxyConfig() {
    try {
        // This would integrate with the TorManager to get current proxy settings
        // For now, return a default SOCKS5 proxy configuration
        return {
            protocol: 'socks5',
            host: '127.0.0.1',
            port: 9050
        };
    }
    catch (error) {
        console.error('Failed to get Tor proxy config:', error);
        return null;
    }
}
// Helper function to broadcast authentication status changes
function broadcastAuthStatus(windowManager, status) {
    windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.AUTH_STATUS_CHANGED, status);
}
exports.broadcastAuthStatus = broadcastAuthStatus;
// Helper function to broadcast token expiration
function broadcastTokenExpired(windowManager, message) {
    windowManager.broadcastToAllWindows(ipc_channels_1.MAIN_TO_RENDERER_CHANNELS.AUTH_TOKEN_EXPIRED, message);
}
exports.broadcastTokenExpired = broadcastTokenExpired;
