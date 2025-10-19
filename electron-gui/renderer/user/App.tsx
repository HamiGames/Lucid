import React, { useState, useEffect, useCallback } from 'react';
import { Layout, TorIndicator } from '../common/components/Layout';
import { useTorStatus } from '../common/hooks/useTorStatus';
import { useApi } from '../common/hooks/useApi';
import { UserHeader } from './components/UserHeader';
import { SessionsPage } from './pages/SessionsPage';
import { CreateSessionPage } from './pages/CreateSessionPage';
import { HistoryPage } from './pages/HistoryPage';
import { WalletPage } from './pages/WalletPage';
import { SettingsPage } from './pages/SettingsPage';
import { ProfilePage } from './pages/ProfilePage';

// User route definitions
interface UserRoute {
  id: string;
  path: string;
  component: React.ComponentType<any>;
  title: string;
  requiresAuth: boolean;
  icon?: string;
}

const USER_ROUTES: UserRoute[] = [
  {
    id: 'sessions',
    path: '/sessions',
    component: SessionsPage,
    title: 'My Sessions',
    requiresAuth: true,
    icon: 'activity'
  },
  {
    id: 'create-session',
    path: '/create-session',
    component: CreateSessionPage,
    title: 'Create Session',
    requiresAuth: true,
    icon: 'plus'
  },
  {
    id: 'history',
    path: '/history',
    component: HistoryPage,
    title: 'History',
    requiresAuth: true,
    icon: 'clock'
  },
  {
    id: 'wallet',
    path: '/wallet',
    component: WalletPage,
    title: 'Wallet',
    requiresAuth: true,
    icon: 'wallet'
  },
  {
    id: 'settings',
    path: '/settings',
    component: SettingsPage,
    title: 'Settings',
    requiresAuth: true,
    icon: 'settings'
  },
  {
    id: 'profile',
    path: '/profile',
    component: ProfilePage,
    title: 'Profile',
    requiresAuth: true,
    icon: 'user'
  }
];

interface User {
  id: string;
  email: string;
  tron_address: string;
  role: string;
  status: string;
  created_at: string;
  last_login: string;
  session_count: number;
  hardware_wallet?: {
    type: 'ledger' | 'trezor' | 'keepkey';
    device_id: string;
    public_key: string;
    is_connected: boolean;
  };
}

interface UserAppState {
  currentRoute: string;
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  error: string | null;
  notifications: Array<{
    id: string;
    type: 'info' | 'success' | 'warning' | 'error';
    title: string;
    message: string;
    timestamp: string;
  }>;
}

const UserApp: React.FC = () => {
  const [state, setState] = useState<UserAppState>({
    currentRoute: 'sessions',
    isAuthenticated: false,
    user: null,
    isLoading: true,
    error: null,
    notifications: []
  });

  const { torStatus, isConnected } = useTorStatus();
  const { apiCall } = useApi();

  // Initialize user application
  const initializeUser = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      // Check authentication status
      const authResult = await verifyAuthentication();
      if (authResult.authenticated) {
        setState(prev => ({
          ...prev,
          isAuthenticated: true,
          user: authResult.user,
          isLoading: false
        }));
      } else {
        setState(prev => ({
          ...prev,
          isAuthenticated: false,
          user: null,
          isLoading: false
        }));
      }
    } catch (error) {
      console.error('Failed to initialize user app:', error);
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to initialize'
      }));
    }
  }, []);

  // Verify user authentication
  const verifyAuthentication = async (): Promise<{ authenticated: boolean; user?: User }> => {
    try {
      const response = await apiCall('/auth/verify', 'GET');
      
      if (response.success && response.user) {
        return {
          authenticated: true,
          user: response.user
        };
      }
      
      return { authenticated: false };
    } catch (error) {
      console.error('Authentication verification failed:', error);
      return { authenticated: false };
    }
  };

  // Handle route changes
  const handleRouteChange = useCallback((routeId: string) => {
    const route = USER_ROUTES.find(r => r.id === routeId);
    if (route && (!route.requiresAuth || state.isAuthenticated)) {
      setState(prev => ({ ...prev, currentRoute: routeId }));
    }
  }, [state.isAuthenticated]);

  // Handle Tor indicator click
  const handleTorIndicatorClick = useCallback(() => {
    if (!isConnected) {
      addNotification({
        type: 'warning',
        title: 'Tor Connection',
        message: 'Connecting to Tor network...'
      });
    } else {
      addNotification({
        type: 'info',
        title: 'Tor Connection',
        message: `Connected via Tor (${torStatus?.circuits || 0} circuits)`
      });
    }
  }, [isConnected, torStatus]);

  // Add notification
  const addNotification = useCallback((notification: Omit<UserAppState['notifications'][0], 'id' | 'timestamp'>) => {
    const newNotification = {
      ...notification,
      id: Date.now().toString(),
      timestamp: new Date().toISOString()
    };
    
    setState(prev => ({
      ...prev,
      notifications: [...prev.notifications, newNotification]
    }));

    // Auto-remove notification after 5 seconds
    setTimeout(() => {
      setState(prev => ({
        ...prev,
        notifications: prev.notifications.filter(n => n.id !== newNotification.id)
      }));
    }, 5000);
  }, []);

  // Handle logout
  const handleLogout = useCallback(async () => {
    try {
      await apiCall('/auth/logout', 'POST');
      setState(prev => ({
        ...prev,
        isAuthenticated: false,
        user: null,
        currentRoute: 'sessions'
      }));
      addNotification({
        type: 'info',
        title: 'Logged Out',
        message: 'You have been successfully logged out'
      });
    } catch (error) {
      console.error('Logout failed:', error);
      addNotification({
        type: 'error',
        title: 'Logout Failed',
        message: 'Failed to logout properly'
      });
    }
  }, [apiCall, addNotification]);

  // Initialize on mount
  useEffect(() => {
    initializeUser();
  }, [initializeUser]);

  // Get current route component
  const getCurrentRouteComponent = () => {
    const route = USER_ROUTES.find(r => r.id === state.currentRoute);
    if (route) {
      const Component = route.component;
      return <Component 
        user={state.user}
        onRouteChange={handleRouteChange}
        onNotification={addNotification}
        apiCall={apiCall}
      />;
    }
    return <SessionsPage 
      user={state.user}
      onRouteChange={handleRouteChange}
      onNotification={addNotification}
      apiCall={apiCall}
    />;
  };

  // Loading state
  if (state.isLoading) {
    return (
      <div className="user-app-loading">
        <div className="loading-spinner"></div>
        <p>Loading User Interface...</p>
      </div>
    );
  }

  // Error state
  if (state.error) {
    return (
      <div className="user-app-error">
        <h2>Error</h2>
        <p>{state.error}</p>
        <button onClick={initializeUser}>Retry</button>
      </div>
    );
  }

  // Not authenticated state
  if (!state.isAuthenticated) {
    return (
      <div className="user-app-auth-required">
        <h2>Authentication Required</h2>
        <p>Please log in to access the User Interface.</p>
        <button onClick={initializeUser}>Retry Login</button>
      </div>
    );
  }

  return (
    <Layout
      title="Lucid User Interface"
      torStatus={torStatus}
      showTorIndicator={true}
      onTorIndicatorClick={handleTorIndicatorClick}
      headerContent={
        <UserHeader
          user={state.user}
          currentRoute={state.currentRoute}
          routes={USER_ROUTES}
          onRouteChange={handleRouteChange}
          onLogout={handleLogout}
          notifications={state.notifications}
          onNotificationDismiss={(id) => {
            setState(prev => ({
              ...prev,
              notifications: prev.notifications.filter(n => n.id !== id)
            }));
          }}
        />
      }
      className="user-app"
    >
      <div className="user-main-content">
        {getCurrentRouteComponent()}
      </div>
    </Layout>
  );
};

export { App };
