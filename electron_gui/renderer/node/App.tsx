import React, { useState, useEffect } from 'react';
import { Layout } from '../common/components/Layout';
import { TorIndicator } from '../common/components/TorIndicator';
import { Toast } from '../common/components/Toast';
import { useApi } from '../common/hooks/useApi';
import { useTorStatus } from '../common/hooks/useTorStatus';

// Node GUI Pages
import NodeDashboardPage from './pages/NodeDashboardPage';
import ResourcesPage from './pages/ResourcesPage';
import EarningsPage from './pages/EarningsPage';
import PoolPage from './pages/PoolPage';
import ConfigurationPage from './pages/ConfigurationPage';
import MaintenancePage from './pages/MaintenancePage';

// Types
interface NodeUser {
  node_id: string;
  operator_id: string;
  pool_id?: string;
  status: 'active' | 'inactive' | 'maintenance' | 'suspended';
  hardware_info: {
    cpu_cores: number;
    memory_gb: number;
    disk_gb: number;
    network_speed_mbps: number;
  };
  location: {
    country: string;
    region: string;
    timezone: string;
  };
  poot_score: number;
  total_earnings: number;
  uptime_percentage: number;
  created_at: string;
  last_activity: string;
}

interface NodeRoute {
  id: string;
  path: string;
  component: React.ComponentType<any>;
  title: string;
  requiresAuth: boolean;
}

interface NodeAppState {
  currentRoute: string;
  isAuthenticated: boolean;
  nodeUser: NodeUser | null;
  systemHealth: any;
  isLoading: boolean;
  error: string | null;
  notifications: Array<{
    id: string;
    type: 'info' | 'warning' | 'error' | 'success';
    message: string;
    timestamp: Date;
  }>;
}

const NodeApp: React.FC = () => {
  const { apiClient } = useApi();
  const { torStatus } = useTorStatus();

  // Define routes for Node GUI
  const routes: NodeRoute[] = [
    {
      id: 'dashboard',
      path: '/dashboard',
      component: NodeDashboardPage,
      title: 'Node Dashboard',
      requiresAuth: true,
    },
    {
      id: 'resources',
      path: '/resources',
      component: ResourcesPage,
      title: 'Resource Monitoring',
      requiresAuth: true,
    },
    {
      id: 'earnings',
      path: '/earnings',
      component: EarningsPage,
      title: 'Earnings & Payouts',
      requiresAuth: true,
    },
    {
      id: 'pool',
      path: '/pool',
      component: PoolPage,
      title: 'Pool Management',
      requiresAuth: true,
    },
    {
      id: 'configuration',
      path: '/configuration',
      component: ConfigurationPage,
      title: 'Configuration',
      requiresAuth: true,
    },
    {
      id: 'maintenance',
      path: '/maintenance',
      component: MaintenancePage,
      title: 'Maintenance',
      requiresAuth: true,
    },
  ];

  const [state, setState] = useState<NodeAppState>({
    currentRoute: 'dashboard',
    isAuthenticated: false,
    nodeUser: null,
    systemHealth: null,
    isLoading: true,
    error: null,
    notifications: [],
  });

  // Initialize Node GUI
  useEffect(() => {
    initializeNode();
  }, []);

  // Monitor Tor connection
  useEffect(() => {
    if (torStatus.connected && state.isAuthenticated) {
      addNotification('success', 'Secure connection established via Tor');
    } else if (!torStatus.connected && state.isAuthenticated) {
      addNotification('warning', 'Tor connection lost - reconnecting...');
    }
  }, [torStatus.connected, state.isAuthenticated]);

  const initializeNode = async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      // Check for existing authentication
      const authResult = await checkExistingAuth();
      if (authResult.authenticated) {
        setState(prev => ({
          ...prev,
          isAuthenticated: true,
          nodeUser: authResult.nodeUser,
          currentRoute: 'dashboard',
        }));

        // Load initial data
        await loadSystemHealth();
        await loadNodeProfile();
      } else {
        // Redirect to authentication or show welcome
        setState(prev => ({
          ...prev,
          isAuthenticated: false,
          currentRoute: 'dashboard',
        }));
      }
    } catch (error) {
      console.error('Failed to initialize node:', error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to initialize node',
      }));
      addNotification('error', 'Failed to initialize node application');
    } finally {
      setState(prev => ({ ...prev, isLoading: false }));
    }
  };

  const checkExistingAuth = async (): Promise<{ authenticated: boolean; nodeUser?: NodeUser }> => {
    try {
      const token = localStorage.getItem('lucid_node_token');
      if (!token) {
        return { authenticated: false };
      }

      const response = await apiClient.get('/node/auth/verify', {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.data.valid) {
        return {
          authenticated: true,
          nodeUser: response.data.node_user,
        };
      } else {
        localStorage.removeItem('lucid_node_token');
        return { authenticated: false };
      }
    } catch (error) {
      console.error('Auth verification failed:', error);
      localStorage.removeItem('lucid_node_token');
      return { authenticated: false };
    }
  };

  const loadSystemHealth = async () => {
    try {
      const response = await apiClient.get('/node/system/health');
      setState(prev => ({ ...prev, systemHealth: response.data }));
    } catch (error) {
      console.error('Failed to load system health:', error);
      addNotification('warning', 'Failed to load system health data');
    }
  };

  const loadNodeProfile = async () => {
    try {
      const response = await apiClient.get('/node/profile');
      setState(prev => ({ ...prev, nodeUser: response.data }));
    } catch (error) {
      console.error('Failed to load node profile:', error);
      addNotification('warning', 'Failed to load node profile');
    }
  };

  const handleRouteChange = (routeId: string) => {
    setState(prev => ({ ...prev, currentRoute: routeId }));
  };

  const handleTorIndicatorClick = () => {
    if (torStatus.connected) {
      addNotification('info', 'Tor connection is active and secure');
    } else {
      addNotification('warning', 'Tor connection is not available');
    }
  };

  const handleLogout = async () => {
    try {
      await apiClient.post('/node/auth/logout');
      localStorage.removeItem('lucid_node_token');
      setState(prev => ({
        ...prev,
        isAuthenticated: false,
        nodeUser: null,
        currentRoute: 'dashboard',
      }));
      addNotification('info', 'Successfully logged out');
    } catch (error) {
      console.error('Logout failed:', error);
      addNotification('error', 'Logout failed');
    }
  };

  const addNotification = (type: 'info' | 'warning' | 'error' | 'success', message: string) => {
    const notification = {
      id: Date.now().toString(),
      type,
      message,
      timestamp: new Date(),
    };

    setState(prev => ({
      ...prev,
      notifications: [...prev.notifications, notification],
    }));

    // Auto-remove notification after 5 seconds
    setTimeout(() => {
      setState(prev => ({
        ...prev,
        notifications: prev.notifications.filter(n => n.id !== notification.id),
      }));
    }, 5000);
  };

  const removeNotification = (id: string) => {
    setState(prev => ({
      ...prev,
      notifications: prev.notifications.filter(n => n.id !== id),
    }));
  };

  const getCurrentRoute = () => {
    return routes.find(route => route.id === state.currentRoute) || routes[0];
  };

  const getNavigationItems = () => {
    return routes.map(route => ({
      id: route.id,
      label: route.title,
      path: route.path,
      icon: getRouteIcon(route.id),
    }));
  };

  const getRouteIcon = (routeId: string): string => {
    const icons: Record<string, string> = {
      dashboard: 'dashboard',
      resources: 'monitor',
      earnings: 'dollar-sign',
      pool: 'users',
      configuration: 'settings',
      maintenance: 'wrench',
    };
    return icons[routeId] || 'circle';
  };

  const renderCurrentPage = () => {
    const currentRoute = getCurrentRoute();
    const PageComponent = currentRoute.component;

    return (
      <PageComponent
        nodeUser={state.nodeUser}
        systemHealth={state.systemHealth}
        onRouteChange={handleRouteChange}
        onNotification={addNotification}
      />
    );
  };

  if (state.isLoading) {
    return (
      <div className="node-app-loading">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Initializing Node Operator GUI...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="node-app">
      <Layout
        title="Lucid Node Operator"
        navigationItems={getNavigationItems()}
        currentRoute={state.currentRoute}
        onRouteChange={handleRouteChange}
        headerActions={
          <div className="header-actions">
            <TorIndicator
              status={torStatus}
              onClick={handleTorIndicatorClick}
              showLabel={true}
            />
            {state.nodeUser && (
              <div className="node-info">
                <span className="node-id">Node: {state.nodeUser.node_id.substring(0, 8)}...</span>
                <button
                  className="logout-btn"
                  onClick={handleLogout}
                  title="Logout"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        }
      >
        {renderCurrentPage()}
      </Layout>

      {/* Toast Notifications */}
      {state.notifications.map(notification => (
        <Toast
          key={notification.id}
          type={notification.type}
          message={notification.message}
          onClose={() => removeNotification(notification.id)}
          duration={5000}
        />
      ))}

      {/* Error Display */}
      {state.error && (
        <div className="error-overlay">
          <div className="error-content">
            <h3>Application Error</h3>
            <p>{state.error}</p>
            <button
              onClick={() => setState(prev => ({ ...prev, error: null }))}
              className="error-close-btn"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NodeApp;
