// renderer/admin/App.tsx - Admin main component with routing
// Based on the electron-multi-gui-development.plan.md specifications

import React, { useState, useEffect } from 'react';
import { Layout, DashboardLayout } from '../common/components/Layout';
import { AdminSidebar } from '../common/components/Sidebar';
import { TorIndicator } from '../common/components/TorIndicator';
import { useToast } from '../common/components/Toast';
import { useTorStatus } from '../common/hooks/useTorStatus';
import { useApi } from '../common/hooks/useApi';
import { TorStatus } from '../../shared/tor-types';
import { SystemHealth, User } from '../../shared/types';

// Import Admin Pages
import DashboardPage from './pages/DashboardPage';
import SessionsPage from './pages/SessionsPage';
import UsersPage from './pages/UsersPage';
import NodesPage from './pages/NodesPage';
import BlockchainPage from './pages/BlockchainPage';
import AuditPage from './pages/AuditPage';
import ConfigPage from './pages/ConfigPage';
import LoginPage from './pages/LoginPage';

// Admin routing configuration
interface AdminRoute {
  id: string;
  path: string;
  component: React.ComponentType<any>;
  title: string;
  requiresAuth: boolean;
  adminOnly: boolean;
}

const ADMIN_ROUTES: AdminRoute[] = [
  {
    id: 'dashboard',
    path: '/admin/dashboard',
    component: DashboardPage,
    title: 'Dashboard',
    requiresAuth: true,
    adminOnly: true,
  },
  {
    id: 'sessions',
    path: '/admin/sessions',
    component: SessionsPage,
    title: 'Sessions Management',
    requiresAuth: true,
    adminOnly: true,
  },
  {
    id: 'users',
    path: '/admin/users',
    component: UsersPage,
    title: 'Users Management',
    requiresAuth: true,
    adminOnly: true,
  },
  {
    id: 'nodes',
    path: '/admin/nodes',
    component: NodesPage,
    title: 'Nodes Management',
    requiresAuth: true,
    adminOnly: true,
  },
  {
    id: 'blockchain',
    path: '/admin/blockchain',
    component: BlockchainPage,
    title: 'Blockchain Management',
    requiresAuth: true,
    adminOnly: true,
  },
  {
    id: 'audit',
    path: '/admin/audit',
    component: AuditPage,
    title: 'Audit Logs',
    requiresAuth: true,
    adminOnly: true,
  },
  {
    id: 'config',
    path: '/admin/config',
    component: ConfigPage,
    title: 'Configuration',
    requiresAuth: true,
    adminOnly: true,
  },
];

interface AdminAppState {
  currentRoute: string;
  isAuthenticated: boolean;
  user: User | null;
  systemHealth: SystemHealth | null;
  isLoading: boolean;
  error: string | null;
}

const AdminApp: React.FC = () => {
  const [state, setState] = useState<AdminAppState>({
    currentRoute: 'dashboard',
    isAuthenticated: false,
    user: null,
    systemHealth: null,
    isLoading: true,
    error: null,
  });

  const { torStatus, torError } = useTorStatus();
  const { showToast } = useToast();
  const { data: authData, loading: authLoading, error: authError } = useApi(
    () => verifyAuthentication(),
    { immediate: true }
  );

  // Initialize admin application
  useEffect(() => {
    initializeAdmin();
  }, []);

  // Handle authentication changes
  useEffect(() => {
    if (authData) {
      setState(prev => ({
        ...prev,
        isAuthenticated: true,
        user: authData.user,
        isLoading: false,
      }));
    } else if (authError) {
      setState(prev => ({
        ...prev,
        isAuthenticated: false,
        user: null,
        isLoading: false,
        error: authError,
      }));
    }
  }, [authData, authError]);

  // Handle Tor status changes
  useEffect(() => {
    if (torStatus) {
      if (torStatus.status === 'connected') {
        showToast({
          type: 'success',
          title: 'Tor Connected',
          message: 'Secure connection established',
          duration: 3000,
        });
      } else if (torStatus.status === 'disconnected') {
        showToast({
          type: 'warning',
          title: 'Tor Disconnected',
          message: 'Connection lost, attempting to reconnect...',
          duration: 5000,
        });
      }
    }
  }, [torStatus, showToast]);

  const initializeAdmin = async () => {
    try {
      console.log('Initializing Admin GUI...');
      
      // Load initial data
      await Promise.all([
        loadSystemHealth(),
        loadUserProfile(),
      ]);

      setState(prev => ({ ...prev, isLoading: false }));
    } catch (error) {
      console.error('Failed to initialize admin:', error);
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Initialization failed',
      }));
    }
  };

  const loadSystemHealth = async () => {
    try {
      // This would call the API to get system health
      const health: SystemHealth = {
        overall: 'healthy',
        services: [],
        tor_status: torStatus?.status === 'connected' ? 'connected' : 'disconnected',
        docker_status: 'running',
      };
      
      setState(prev => ({ ...prev, systemHealth: health }));
    } catch (error) {
      console.error('Failed to load system health:', error);
    }
  };

  const loadUserProfile = async () => {
    try {
      // This would call the API to get user profile
      // For now, using mock data
    } catch (error) {
      console.error('Failed to load user profile:', error);
    }
  };

  const verifyAuthentication = async (): Promise<{ user: User }> => {
    try {
      // This would verify the authentication token
      // For now, returning mock data
      return {
        user: {
          user_id: 'admin-1',
          email: 'admin@lucid.com',
          tron_address: 'TAdmin123...',
          role: 'admin',
          created_at: new Date().toISOString(),
        },
      };
    } catch (error) {
      throw new Error('Authentication verification failed');
    }
  };

  const handleRouteChange = (routeId: string) => {
    setState(prev => ({ ...prev, currentRoute: routeId }));
  };

  const handleTorIndicatorClick = () => {
    showToast({
      type: 'info',
      title: 'Tor Status',
      message: `Status: ${torStatus?.status || 'unknown'}, Progress: ${Math.round((torStatus?.bootstrap_progress || 0) * 100)}%`,
      duration: 5000,
    });
  };

  const handleLogout = async () => {
    try {
      // This would call the logout API
      setState(prev => ({
        ...prev,
        isAuthenticated: false,
        user: null,
        currentRoute: 'login',
      }));
      
      showToast({
        type: 'success',
        title: 'Logged Out',
        message: 'You have been successfully logged out',
      });
    } catch (error) {
      console.error('Logout failed:', error);
      showToast({
        type: 'error',
        title: 'Logout Failed',
        message: 'Failed to logout, please try again',
      });
    }
  };

  // Render login page if not authenticated
  if (!state.isAuthenticated && !state.isLoading) {
    return (
      <LoginPage
        onLoginSuccess={(user) => {
          setState(prev => ({
            ...prev,
            isAuthenticated: true,
            user,
            currentRoute: 'dashboard',
          }));
        }}
      />
    );
  }

  // Show loading state
  if (state.isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Loading Admin Interface
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Initializing secure connection...
          </p>
        </div>
      </div>
    );
  }

  // Show error state
  if (state.error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="bg-red-100 dark:bg-red-900 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-red-900 dark:text-red-100 mb-2">
              Initialization Error
            </h2>
            <p className="text-red-700 dark:text-red-300 mb-4">
              {state.error}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Get current route component
  const currentRoute = ADMIN_ROUTES.find(route => route.id === state.currentRoute);
  const CurrentComponent = currentRoute?.component || DashboardPage;

  // Render main admin interface
  return (
    <DashboardLayout
      title="Lucid Admin"
      torStatus={torStatus}
      showTorIndicator={true}
      onTorIndicatorClick={handleTorIndicatorClick}
      headerActions={
        <div className="flex items-center space-x-4">
          {state.user && (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Welcome, {state.user.email}
              </span>
              <button
                onClick={handleLogout}
                className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 transition-colors"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      }
    >
      <div className="flex h-full">
        {/* Sidebar */}
        <AdminSidebar
          activeItem={state.currentRoute}
          onItemClick={(item) => handleRouteChange(item.id)}
          className="w-64 flex-shrink-0"
        />

        {/* Main content */}
        <div className="flex-1 overflow-auto">
          <div className="p-6">
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {currentRoute?.title || 'Dashboard'}
              </h1>
              {state.systemHealth && (
                <div className="mt-2 flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    state.systemHealth.overall === 'healthy'
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : state.systemHealth.overall === 'degraded'
                      ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                      : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                  }`}>
                    System: {state.systemHealth.overall}
                  </span>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    state.systemHealth.tor_status === 'connected'
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                  }`}>
                    Tor: {state.systemHealth.tor_status}
                  </span>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    state.systemHealth.docker_status === 'running'
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                  }`}>
                    Docker: {state.systemHealth.docker_status}
                  </span>
                </div>
              )}
            </div>

            {/* Route component */}
            <CurrentComponent
              user={state.user}
              systemHealth={state.systemHealth}
              torStatus={torStatus}
            />
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default AdminApp;
