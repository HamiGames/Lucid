import React, { useState, useEffect } from 'react';
import { Layout } from '../common/components/Layout';
import { TorIndicator } from '../common/components/TorIndicator';
import { useTorStatus } from '../common/hooks/useTorStatus';
import { useApi } from '../common/hooks/useApi';
import { APIExplorerPage } from './pages/APIExplorerPage';
import { LogsPage } from './pages/LogsPage';
import { MetricsPage } from './pages/MetricsPage';
import { DocumentationPage } from './pages/DocumentationPage';
import { TestingPage } from './pages/TestingPage';
import { DebugPage } from './pages/DebugPage';

interface DeveloperRoute {
  id: string;
  path: string;
  component: React.ComponentType<any>;
  title: string;
  icon: string;
  description: string;
}

const DEVELOPER_ROUTES: DeveloperRoute[] = [
  {
    id: 'api-explorer',
    path: '/api-explorer',
    component: APIExplorerPage,
    title: 'API Explorer',
    icon: '🔍',
    description: 'Explore and test API endpoints'
  },
  {
    id: 'logs',
    path: '/logs',
    component: LogsPage,
    title: 'System Logs',
    icon: '📋',
    description: 'View real-time system logs'
  },
  {
    id: 'metrics',
    path: '/metrics',
    component: MetricsPage,
    title: 'Metrics',
    icon: '📊',
    description: 'Monitor system performance metrics'
  },
  {
    id: 'documentation',
    path: '/documentation',
    component: DocumentationPage,
    title: 'Documentation',
    icon: '📚',
    description: 'API documentation and guides'
  },
  {
    id: 'testing',
    path: '/testing',
    component: TestingPage,
    title: 'API Testing',
    icon: '🧪',
    description: 'Test API endpoints and workflows'
  },
  {
    id: 'debug',
    path: '/debug',
    component: DebugPage,
    title: 'Debug Tools',
    icon: '🔧',
    description: 'Debugging utilities and tools'
  }
];

interface DeveloperAppState {
  currentRoute: string;
  isLoading: boolean;
  error: string | null;
  systemInfo: {
    version: string;
    build: string;
    environment: string;
  } | null;
}

const DeveloperApp: React.FC = () => {
  const [state, setState] = useState<DeveloperAppState>({
    currentRoute: 'api-explorer',
    isLoading: true,
    error: null,
    systemInfo: null
  });

  const { torStatus } = useTorStatus();
  const { apiClient } = useApi();

  useEffect(() => {
    initializeDeveloper();
  }, []);

  const initializeDeveloper = async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      // Load system information
      const systemInfo = await loadSystemInfo();
      
      setState(prev => ({
        ...prev,
        isLoading: false,
        systemInfo
      }));
    } catch (error) {
      console.error('Failed to initialize developer app:', error);
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to initialize developer app'
      }));
    }
  };

  const loadSystemInfo = async () => {
    try {
      // Get system information from main process
      const response = await window.electronAPI.getSystemInfo();
      return {
        version: response.version || '1.0.0',
        build: response.build || 'development',
        environment: response.environment || 'development'
      };
    } catch (error) {
      console.warn('Failed to load system info:', error);
      return {
        version: '1.0.0',
        build: 'development',
        environment: 'development'
      };
    }
  };

  const handleRouteChange = (routeId: string) => {
    setState(prev => ({ ...prev, currentRoute: routeId }));
  };

  const handleTorIndicatorClick = () => {
    // Show Tor connection details
    console.log('Tor status:', torStatus);
  };

  const renderCurrentPage = () => {
    const route = DEVELOPER_ROUTES.find(r => r.id === state.currentRoute);
    if (!route) {
      return <div className="developer-error">Route not found</div>;
    }

    const PageComponent = route.component;
    return <PageComponent />;
  };

  if (state.isLoading) {
    return (
      <div className="developer-loading">
        <div className="loading-spinner"></div>
        <p>Initializing Developer Tools...</p>
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="developer-error">
        <h2>Failed to Initialize</h2>
        <p>{state.error}</p>
        <button onClick={initializeDeveloper}>Retry</button>
      </div>
    );
  }

  return (
    <Layout
      title="Developer Tools"
      subtitle="API Development & Debugging"
      torStatus={torStatus}
      onTorIndicatorClick={handleTorIndicatorClick}
      sidebarItems={DEVELOPER_ROUTES.map(route => ({
        id: route.id,
        title: route.title,
        icon: route.icon,
        description: route.description,
        active: state.currentRoute === route.id
      }))}
      onNavigate={handleRouteChange}
      systemInfo={state.systemInfo}
    >
      {renderCurrentPage()}
    </Layout>
  );
};

export { DeveloperApp as App };
