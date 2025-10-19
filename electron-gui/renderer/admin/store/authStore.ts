// authStore.ts - Admin authentication state management
// Based on the electron-multi-gui-development.plan.md specifications

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { User } from '../../../shared/types';

// Admin authentication state interface
interface AuthState {
  // Authentication status
  isAuthenticated: boolean;
  isAdmin: boolean;
  isSuperAdmin: boolean;
  
  // User information
  adminUser: User | null;
  authToken: string | null;
  refreshToken: string | null;
  authExpiresAt: Date | null;
  refreshExpiresAt: Date | null;
  
  // Session information
  sessionId: string | null;
  loginTime: Date | null;
  lastActivity: Date | null;
  sessionTimeout: number; // in milliseconds
  
  // TOTP information
  totpRequired: boolean;
  totpVerified: boolean;
  totpSecret: string | null;
  
  // Authentication attempts
  loginAttempts: number;
  maxLoginAttempts: number;
  lockedUntil: Date | null;
  
  // Hardware wallet status
  hardwareWalletConnected: boolean;
  hardwareWalletType: 'ledger' | 'trezor' | 'keepkey' | null;
  
  // Authentication state
  isLoggingIn: boolean;
  isLoggingOut: boolean;
  loginError: string | null;
  logoutError: string | null;
}

// Auth actions interface
interface AuthActions {
  // Authentication actions
  setAuthenticated: (authenticated: boolean) => void;
  setAdminUser: (user: User | null) => void;
  setAuthToken: (token: string | null) => void;
  setRefreshToken: (token: string | null) => void;
  setAuthExpiresAt: (expiresAt: Date | null) => void;
  setRefreshExpiresAt: (expiresAt: Date | null) => void;
  
  // Session actions
  setSessionId: (sessionId: string | null) => void;
  setLoginTime: (loginTime: Date | null) => void;
  updateLastActivity: () => void;
  setSessionTimeout: (timeout: number) => void;
  
  // TOTP actions
  setTotpRequired: (required: boolean) => void;
  setTotpVerified: (verified: boolean) => void;
  setTotpSecret: (secret: string | null) => void;
  
  // Login attempt actions
  incrementLoginAttempts: () => void;
  resetLoginAttempts: () => void;
  setLockedUntil: (lockedUntil: Date | null) => void;
  
  // Hardware wallet actions
  setHardwareWalletConnected: (connected: boolean) => void;
  setHardwareWalletType: (type: 'ledger' | 'trezor' | 'keepkey' | null) => void;
  
  // Loading states
  setLoggingIn: (loggingIn: boolean) => void;
  setLoggingOut: (loggingOut: boolean) => void;
  setLoginError: (error: string | null) => void;
  setLogoutError: (error: string | null) => void;
  
  // Combined actions
  login: (user: User, authToken: string, refreshToken: string, expiresAt: Date, refreshExpiresAt: Date) => void;
  logout: () => void;
  refreshAuth: (authToken: string, refreshToken: string, expiresAt: Date, refreshExpiresAt: Date) => void;
  lockAccount: (duration: number) => void;
  unlockAccount: () => void;
  
  // Utility actions
  reset: () => void;
  clearErrors: () => void;
}

// Initial state
const initialState: AuthState = {
  // Authentication status
  isAuthenticated: false,
  isAdmin: false,
  isSuperAdmin: false,
  
  // User information
  adminUser: null,
  authToken: null,
  refreshToken: null,
  authExpiresAt: null,
  refreshExpiresAt: null,
  
  // Session information
  sessionId: null,
  loginTime: null,
  lastActivity: null,
  sessionTimeout: 30 * 60 * 1000, // 30 minutes
  
  // TOTP information
  totpRequired: false,
  totpVerified: false,
  totpSecret: null,
  
  // Authentication attempts
  loginAttempts: 0,
  maxLoginAttempts: 5,
  lockedUntil: null,
  
  // Hardware wallet status
  hardwareWalletConnected: false,
  hardwareWalletType: null,
  
  // Authentication state
  isLoggingIn: false,
  isLoggingOut: false,
  loginError: null,
  logoutError: null,
};

// Create the auth store
export const useAuthStore = create<AuthState & AuthActions>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        // Authentication actions
        setAuthenticated: (authenticated) => set({ isAuthenticated: authenticated }),
        setAdminUser: (user) => set({ 
          adminUser: user,
          isAdmin: user?.role === 'admin' || user?.role === 'super_admin',
          isSuperAdmin: user?.role === 'super_admin',
        }),
        setAuthToken: (token) => set({ authToken: token }),
        setRefreshToken: (token) => set({ refreshToken: token }),
        setAuthExpiresAt: (expiresAt) => set({ authExpiresAt: expiresAt }),
        setRefreshExpiresAt: (expiresAt) => set({ refreshExpiresAt: expiresAt }),
        
        // Session actions
        setSessionId: (sessionId) => set({ sessionId }),
        setLoginTime: (loginTime) => set({ loginTime }),
        updateLastActivity: () => set({ lastActivity: new Date() }),
        setSessionTimeout: (timeout) => set({ sessionTimeout: timeout }),
        
        // TOTP actions
        setTotpRequired: (required) => set({ totpRequired: required }),
        setTotpVerified: (verified) => set({ totpVerified: verified }),
        setTotpSecret: (secret) => set({ totpSecret: secret }),
        
        // Login attempt actions
        incrementLoginAttempts: () => set((state) => ({ 
          loginAttempts: state.loginAttempts + 1 
        })),
        resetLoginAttempts: () => set({ loginAttempts: 0 }),
        setLockedUntil: (lockedUntil) => set({ lockedUntil }),
        
        // Hardware wallet actions
        setHardwareWalletConnected: (connected) => set({ hardwareWalletConnected: connected }),
        setHardwareWalletType: (type) => set({ hardwareWalletType: type }),
        
        // Loading states
        setLoggingIn: (loggingIn) => set({ isLoggingIn: loggingIn }),
        setLoggingOut: (loggingOut) => set({ isLoggingOut: loggingOut }),
        setLoginError: (error) => set({ loginError: error }),
        setLogoutError: (error) => set({ logoutError: error }),
        
        // Combined actions
        login: (user, authToken, refreshToken, expiresAt, refreshExpiresAt) => set({
          isAuthenticated: true,
          adminUser: user,
          isAdmin: user.role === 'admin' || user.role === 'super_admin',
          isSuperAdmin: user.role === 'super_admin',
          authToken,
          refreshToken,
          authExpiresAt: expiresAt,
          refreshExpiresAt: refreshExpiresAt,
          sessionId: Math.random().toString(36).substring(2, 15),
          loginTime: new Date(),
          lastActivity: new Date(),
          totpRequired: user.role === 'super_admin', // Super admin requires TOTP
          totpVerified: false,
          loginAttempts: 0,
          lockedUntil: null,
          isLoggingIn: false,
          loginError: null,
        }),
        
        logout: () => set({
          isAuthenticated: false,
          adminUser: null,
          isAdmin: false,
          isSuperAdmin: false,
          authToken: null,
          refreshToken: null,
          authExpiresAt: null,
          refreshExpiresAt: null,
          sessionId: null,
          loginTime: null,
          lastActivity: null,
          totpRequired: false,
          totpVerified: false,
          totpSecret: null,
          hardwareWalletConnected: false,
          hardwareWalletType: null,
          isLoggingOut: false,
          logoutError: null,
        }),
        
        refreshAuth: (authToken, refreshToken, expiresAt, refreshExpiresAt) => set({
          authToken,
          refreshToken,
          authExpiresAt: expiresAt,
          refreshExpiresAt: refreshExpiresAt,
          lastActivity: new Date(),
        }),
        
        lockAccount: (duration) => set({
          lockedUntil: new Date(Date.now() + duration),
          loginAttempts: get().maxLoginAttempts,
        }),
        
        unlockAccount: () => set({
          lockedUntil: null,
          loginAttempts: 0,
        }),
        
        // Utility actions
        reset: () => set(initialState),
        clearErrors: () => set({
          loginError: null,
          logoutError: null,
        }),
      }),
      {
        name: 'lucid-admin-auth-store',
        partialize: (state) => ({
          isAuthenticated: state.isAuthenticated,
          adminUser: state.adminUser,
          authToken: state.authToken,
          refreshToken: state.refreshToken,
          authExpiresAt: state.authExpiresAt,
          refreshExpiresAt: state.refreshExpiresAt,
          sessionId: state.sessionId,
          loginTime: state.loginTime,
          totpRequired: state.totpRequired,
          totpSecret: state.totpSecret,
          hardwareWalletConnected: state.hardwareWalletConnected,
          hardwareWalletType: state.hardwareWalletType,
          sessionTimeout: state.sessionTimeout,
        }),
      }
    ),
    {
      name: 'lucid-admin-auth-store',
    }
  )
);

// Selectors for auth state access
export const useAuthStatus = () => useAuthStore((state) => ({
  isAuthenticated: state.isAuthenticated,
  isAdmin: state.isAdmin,
  isSuperAdmin: state.isSuperAdmin,
  isLocked: state.lockedUntil ? new Date() < state.lockedUntil : false,
  isExpired: state.authExpiresAt ? new Date() > state.authExpiresAt : false,
  sessionExpired: state.lastActivity && state.sessionTimeout 
    ? (Date.now() - state.lastActivity.getTime()) > state.sessionTimeout 
    : false,
}));

export const useAdminUser = () => useAuthStore((state) => state.adminUser);
export const useAuthToken = () => useAuthStore((state) => state.authToken);
export const useRefreshToken = () => useAuthStore((state) => state.refreshToken);

export const useSessionInfo = () => useAuthStore((state) => ({
  sessionId: state.sessionId,
  loginTime: state.loginTime,
  lastActivity: state.lastActivity,
  sessionTimeout: state.sessionTimeout,
  timeUntilTimeout: state.lastActivity && state.sessionTimeout 
    ? Math.max(0, state.sessionTimeout - (Date.now() - state.lastActivity.getTime()))
    : 0,
}));

export const useTotpStatus = () => useAuthStore((state) => ({
  totpRequired: state.totpRequired,
  totpVerified: state.totpVerified,
  totpSecret: state.totpSecret,
}));

export const useLoginAttempts = () => useAuthStore((state) => ({
  attempts: state.loginAttempts,
  maxAttempts: state.maxLoginAttempts,
  remaining: state.maxLoginAttempts - state.loginAttempts,
  isLocked: state.lockedUntil ? new Date() < state.lockedUntil : false,
  lockedUntil: state.lockedUntil,
}));

export const useHardwareWallet = () => useAuthStore((state) => ({
  connected: state.hardwareWalletConnected,
  type: state.hardwareWalletType,
}));

export const useAuthLoading = () => useAuthStore((state) => ({
  isLoggingIn: state.isLoggingIn,
  isLoggingOut: state.isLoggingOut,
}));

export const useAuthErrors = () => useAuthStore((state) => ({
  loginError: state.loginError,
  logoutError: state.logoutError,
}));

// Action selectors
export const useAuthActions = () => useAuthStore((state) => ({
  setAuthenticated: state.setAuthenticated,
  setAdminUser: state.setAdminUser,
  setAuthToken: state.setAuthToken,
  setRefreshToken: state.setRefreshToken,
  setAuthExpiresAt: state.setAuthExpiresAt,
  setRefreshExpiresAt: state.setRefreshExpiresAt,
  login: state.login,
  logout: state.logout,
  refreshAuth: state.refreshAuth,
  reset: state.reset,
  clearErrors: state.clearErrors,
}));

export const useSessionActions = () => useAuthStore((state) => ({
  setSessionId: state.setSessionId,
  setLoginTime: state.setLoginTime,
  updateLastActivity: state.updateLastActivity,
  setSessionTimeout: state.setSessionTimeout,
}));

export const useTotpActions = () => useAuthStore((state) => ({
  setTotpRequired: state.setTotpRequired,
  setTotpVerified: state.setTotpVerified,
  setTotpSecret: state.setTotpSecret,
}));

export const useLoginAttemptActions = () => useAuthStore((state) => ({
  incrementLoginAttempts: state.incrementLoginAttempts,
  resetLoginAttempts: state.resetLoginAttempts,
  setLockedUntil: state.setLockedUntil,
  lockAccount: state.lockAccount,
  unlockAccount: state.unlockAccount,
}));

export const useHardwareWalletActions = () => useAuthStore((state) => ({
  setHardwareWalletConnected: state.setHardwareWalletConnected,
  setHardwareWalletType: state.setHardwareWalletType,
}));

export const useAuthLoadingActions = () => useAuthStore((state) => ({
  setLoggingIn: state.setLoggingIn,
  setLoggingOut: state.setLoggingOut,
  setLoginError: state.setLoginError,
  setLogoutError: state.setLogoutError,
}));

// Computed selectors
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useIsAdmin = () => useAuthStore((state) => state.isAdmin);
export const useIsSuperAdmin = () => useAuthStore((state) => state.isSuperAdmin);

export const useCanAccessAdmin = () => {
  const authStatus = useAuthStatus();
  return authStatus.isAuthenticated && authStatus.isAdmin && !authStatus.isLocked && !authStatus.isExpired;
};

export const useCanAccessSuperAdmin = () => {
  const authStatus = useAuthStatus();
  return authStatus.isAuthenticated && authStatus.isSuperAdmin && !authStatus.isLocked && !authStatus.isExpired;
};

export const useSessionTimeRemaining = () => {
  const sessionInfo = useSessionInfo();
  return sessionInfo.timeUntilTimeout;
};

export const useIsSessionExpired = () => {
  const sessionInfo = useSessionInfo();
  return sessionInfo.timeUntilTimeout <= 0;
};

export default useAuthStore;
