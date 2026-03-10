// appStore.ts - Zustand state management
// Based on the electron-multi-gui-development.plan.md specifications

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { TorStatus } from '../../../shared/tor-types';
import { User, Session, Node } from '../../../shared/types';

// Global application state
interface AppState {
  // Tor connection state
  torStatus: TorStatus;
  torConnected: boolean;
  torConnecting: boolean;
  torError: string | null;

  // User authentication state
  user: User | null;
  authenticated: boolean;
  authToken: string | null;
  authExpiresAt: Date | null;

  // Application state
  theme: 'light' | 'dark' | 'system';
  language: string;
  sidebarCollapsed: boolean;
  currentWindow: 'admin' | 'user' | 'developer' | 'node' | null;

  // UI state
  loading: boolean;
  error: string | null;
  notifications: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message?: string;
    timestamp: Date;
    read: boolean;
  }>;

  // Data state
  sessions: Session[];
  users: User[];
  nodes: Node[];
  lastSync: Date | null;

  // Settings
  settings: {
    autoStartTor: boolean;
    torBootstrapTimeout: number;
    apiTimeout: number;
    refreshInterval: number;
    logLevel: 'debug' | 'info' | 'warn' | 'error';
    notifications: {
      enabled: boolean;
      sound: boolean;
      desktop: boolean;
    };
    privacy: {
      clearDataOnExit: boolean;
      rememberSessions: boolean;
      analytics: boolean;
    };
  };
}

// Actions interface
interface AppActions {
  // Tor actions
  setTorStatus: (status: TorStatus) => void;
  setTorConnected: (connected: boolean) => void;
  setTorConnecting: (connecting: boolean) => void;
  setTorError: (error: string | null) => void;

  // Authentication actions
  setUser: (user: User | null) => void;
  setAuthenticated: (authenticated: boolean) => void;
  setAuthToken: (token: string | null) => void;
  setAuthExpiresAt: (expiresAt: Date | null) => void;
  login: (user: User, token: string, expiresAt: Date) => void;
  logout: () => void;

  // Application actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setLanguage: (language: string) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setCurrentWindow: (window: 'admin' | 'user' | 'developer' | 'node' | null) => void;

  // UI actions
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  addNotification: (notification: Omit<AppState['notifications'][0], 'id' | 'timestamp' | 'read'>) => void;
  removeNotification: (id: string) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;

  // Data actions
  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
  updateSession: (sessionId: string, updates: Partial<Session>) => void;
  removeSession: (sessionId: string) => void;
  setUsers: (users: User[]) => void;
  addUser: (user: User) => void;
  updateUser: (userId: string, updates: Partial<User>) => void;
  removeUser: (userId: string) => void;
  setNodes: (nodes: Node[]) => void;
  addNode: (node: Node) => void;
  updateNode: (nodeId: string, updates: Partial<Node>) => void;
  removeNode: (nodeId: string) => void;
  setLastSync: (date: Date) => void;

  // Settings actions
  updateSettings: (settings: Partial<AppState['settings']>) => void;
  resetSettings: () => void;

  // Utility actions
  reset: () => void;
  clearData: () => void;
}

// Initial state
const initialState: AppState = {
  // Tor connection state
  torStatus: {
    is_connected: false,
    bootstrap_progress: 0,
    circuits: [],
    proxy_port: 9050,
    status: 'disconnected',
  },
  torConnected: false,
  torConnecting: false,
  torError: null,

  // User authentication state
  user: null,
  authenticated: false,
  authToken: null,
  authExpiresAt: null,

  // Application state
  theme: 'system',
  language: 'en',
  sidebarCollapsed: false,
  currentWindow: null,

  // UI state
  loading: false,
  error: null,
  notifications: [],

  // Data state
  sessions: [],
  users: [],
  nodes: [],
  lastSync: null,

  // Settings
  settings: {
    autoStartTor: true,
    torBootstrapTimeout: 60000,
    apiTimeout: 30000,
    refreshInterval: 30000,
    logLevel: 'info',
    notifications: {
      enabled: true,
      sound: true,
      desktop: true,
    },
    privacy: {
      clearDataOnExit: false,
      rememberSessions: true,
      analytics: false,
    },
  },
};

// Create the store
export const useAppStore = create<AppState & AppActions>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        // Tor actions
        setTorStatus: (status) => set({ torStatus: status }),
        setTorConnected: (connected) => set({ torConnected: connected }),
        setTorConnecting: (connecting) => set({ torConnecting: connecting }),
        setTorError: (error) => set({ torError: error }),

        // Authentication actions
        setUser: (user) => set({ user }),
        setAuthenticated: (authenticated) => set({ authenticated }),
        setAuthToken: (token) => set({ authToken: token }),
        setAuthExpiresAt: (expiresAt) => set({ authExpiresAt: expiresAt }),
        login: (user, token, expiresAt) => set({
          user,
          authenticated: true,
          authToken: token,
          authExpiresAt: expiresAt,
        }),
        logout: () => set({
          user: null,
          authenticated: false,
          authToken: null,
          authExpiresAt: null,
        }),

        // Application actions
        setTheme: (theme) => set({ theme }),
        setLanguage: (language) => set({ language }),
        setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
        setCurrentWindow: (window) => set({ currentWindow: window }),

        // UI actions
        setLoading: (loading) => set({ loading }),
        setError: (error) => set({ error }),
        addNotification: (notification) => set((state) => ({
          notifications: [
            ...state.notifications,
            {
              ...notification,
              id: Math.random().toString(36).substring(2, 9),
              timestamp: new Date(),
              read: false,
            },
          ],
        })),
        removeNotification: (id) => set((state) => ({
          notifications: state.notifications.filter(n => n.id !== id),
        })),
        markNotificationRead: (id) => set((state) => ({
          notifications: state.notifications.map(n =>
            n.id === id ? { ...n, read: true } : n
          ),
        })),
        clearNotifications: () => set({ notifications: [] }),

        // Data actions
        setSessions: (sessions) => set({ sessions }),
        addSession: (session) => set((state) => ({
          sessions: [...state.sessions, session],
        })),
        updateSession: (sessionId, updates) => set((state) => ({
          sessions: state.sessions.map(s =>
            s.session_id === sessionId ? { ...s, ...updates } : s
          ),
        })),
        removeSession: (sessionId) => set((state) => ({
          sessions: state.sessions.filter(s => s.session_id !== sessionId),
        })),
        setUsers: (users) => set({ users }),
        addUser: (user) => set((state) => ({
          users: [...state.users, user],
        })),
        updateUser: (userId, updates) => set((state) => ({
          users: state.users.map(u =>
            u.user_id === userId ? { ...u, ...updates } : u
          ),
        })),
        removeUser: (userId) => set((state) => ({
          users: state.users.filter(u => u.user_id !== userId),
        })),
        setNodes: (nodes) => set({ nodes }),
        addNode: (node) => set((state) => ({
          nodes: [...state.nodes, node],
        })),
        updateNode: (nodeId, updates) => set((state) => ({
          nodes: state.nodes.map(n =>
            n.node_id === nodeId ? { ...n, ...updates } : n
          ),
        })),
        removeNode: (nodeId) => set((state) => ({
          nodes: state.nodes.filter(n => n.node_id !== nodeId),
        })),
        setLastSync: (date) => set({ lastSync: date }),

        // Settings actions
        updateSettings: (settings) => set((state) => ({
          settings: { ...state.settings, ...settings },
        })),
        resetSettings: () => set({ settings: initialState.settings }),

        // Utility actions
        reset: () => set(initialState),
        clearData: () => set({
          sessions: [],
          users: [],
          nodes: [],
          lastSync: null,
          notifications: [],
        }),
      }),
      {
        name: 'lucid-app-store',
        partialize: (state) => ({
          theme: state.theme,
          language: state.language,
          sidebarCollapsed: state.sidebarCollapsed,
          settings: state.settings,
          user: state.user,
          authenticated: state.authenticated,
          authToken: state.authToken,
          authExpiresAt: state.authExpiresAt,
        }),
      }
    ),
    {
      name: 'lucid-app-store',
    }
  )
);

// Selectors for common state access
export const useTorStatus = () => useAppStore((state) => state.torStatus);
export const useTorConnected = () => useAppStore((state) => state.torConnected);
export const useTorConnecting = () => useAppStore((state) => state.torConnecting);
export const useTorError = () => useAppStore((state) => state.torError);

export const useUser = () => useAppStore((state) => state.user);
export const useAuthenticated = () => useAppStore((state) => state.authenticated);
export const useAuthToken = () => useAppStore((state) => state.authToken);

export const useTheme = () => useAppStore((state) => state.theme);
export const useLanguage = () => useAppStore((state) => state.language);
export const useSidebarCollapsed = () => useAppStore((state) => state.sidebarCollapsed);
export const useCurrentWindow = () => useAppStore((state) => state.currentWindow);

export const useLoading = () => useAppStore((state) => state.loading);
export const useError = () => useAppStore((state) => state.error);
export const useNotifications = () => useAppStore((state) => state.notifications);

export const useSessions = () => useAppStore((state) => state.sessions);
export const useUsers = () => useAppStore((state) => state.users);
export const useNodes = () => useAppStore((state) => state.nodes);
export const useLastSync = () => useAppStore((state) => state.lastSync);

export const useSettings = () => useAppStore((state) => state.settings);

// Action selectors
export const useTorActions = () => useAppStore((state) => ({
  setTorStatus: state.setTorStatus,
  setTorConnected: state.setTorConnected,
  setTorConnecting: state.setTorConnecting,
  setTorError: state.setTorError,
}));

export const useAuthActions = () => useAppStore((state) => ({
  setUser: state.setUser,
  setAuthenticated: state.setAuthenticated,
  setAuthToken: state.setAuthToken,
  setAuthExpiresAt: state.setAuthExpiresAt,
  login: state.login,
  logout: state.logout,
}));

export const useAppActions = () => useAppStore((state) => ({
  setTheme: state.setTheme,
  setLanguage: state.setLanguage,
  setSidebarCollapsed: state.setSidebarCollapsed,
  setCurrentWindow: state.setCurrentWindow,
}));

export const useUIActions = () => useAppStore((state) => ({
  setLoading: state.setLoading,
  setError: state.setError,
  addNotification: state.addNotification,
  removeNotification: state.removeNotification,
  markNotificationRead: state.markNotificationRead,
  clearNotifications: state.clearNotifications,
}));

export const useDataActions = () => useAppStore((state) => ({
  setSessions: state.setSessions,
  addSession: state.addSession,
  updateSession: state.updateSession,
  removeSession: state.removeSession,
  setUsers: state.setUsers,
  addUser: state.addUser,
  updateUser: state.updateUser,
  removeUser: state.removeUser,
  setNodes: state.setNodes,
  addNode: state.addNode,
  updateNode: state.updateNode,
  removeNode: state.removeNode,
  setLastSync: state.setLastSync,
}));

export const useSettingsActions = () => useAppStore((state) => ({
  updateSettings: state.updateSettings,
  resetSettings: state.resetSettings,
}));

// Computed selectors
export const useUnreadNotifications = () => useAppStore((state) =>
  state.notifications.filter(n => !n.read)
);

export const useUnreadNotificationCount = () => useAppStore((state) =>
  state.notifications.filter(n => !n.read).length
);

export const useActiveSessions = () => useAppStore((state) =>
  state.sessions.filter(s => s.status === 'active')
);

export const useCompletedSessions = () => useAppStore((state) =>
  state.sessions.filter(s => s.status === 'completed')
);

export const useActiveNodes = () => useAppStore((state) =>
  state.nodes.filter(n => n.status === 'active')
);

export const useUserSessions = (userId: string) => useAppStore((state) =>
  state.sessions.filter(s => s.user_id === userId)
);

export const useNodeSessions = (nodeId: string) => useAppStore((state) =>
  state.sessions.filter(s => s.node_id === nodeId)
);

// Theme selector with system preference detection
export const useEffectiveTheme = () => {
  const theme = useTheme();
  
  if (theme === 'system') {
    // In a real implementation, this would detect system preference
    return 'light'; // Default fallback
  }
  
  return theme;
};

// Authentication status selector
export const useAuthStatus = () => {
  const user = useUser();
  const authenticated = useAuthenticated();
  const authToken = useAuthToken();
  const authExpiresAt = useAuthExpiresAt();
  
  const isExpired = authExpiresAt ? new Date() > authExpiresAt : false;
  const isAuthenticated = authenticated && !!user && !!authToken && !isExpired;
  
  return {
    isAuthenticated,
    isExpired,
    user,
    token: authToken,
    expiresAt: authExpiresAt,
  };
};

// Tor connection status selector
export const useTorConnectionStatus = () => {
  const status = useTorStatus();
  const connected = useTorConnected();
  const connecting = useTorConnecting();
  const error = useTorError();
  
  return {
    connected,
    connecting,
    disconnected: !connected && !connecting,
    error,
    status,
    bootstrapProgress: status.bootstrap_progress,
    circuitCount: status.circuits.length,
    proxyPort: status.proxy_port,
  };
};

export default useAppStore;
