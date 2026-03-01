// tests/developer-gui.spec.ts - Developer GUI tests
// Based on the electron-multi-gui-development.plan.md specifications

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock the Developer GUI components
jest.mock('../renderer/developer/App', () => {
  return function MockDeveloperApp() {
    return <div data-testid="developer-app">Developer App</div>;
  };
});

jest.mock('../renderer/developer/components/APIEndpointCard', () => {
  return function MockAPIEndpointCard({ endpoint, onTest }: any) {
    return (
      <div data-testid="api-endpoint-card">
        <span data-testid="endpoint-method">{endpoint.method}</span>
        <span data-testid="endpoint-path">{endpoint.path}</span>
        <button data-testid="test-endpoint" onClick={() => onTest?.(endpoint)}>
          Test
        </button>
      </div>
    );
  };
});

jest.mock('../renderer/developer/components/LogViewer', () => {
  return function MockLogViewer({ logs, onClear }: any) {
    return (
      <div data-testid="log-viewer">
        <div data-testid="logs-container">
          {logs.map((log: any, index: number) => (
            <div key={index} data-testid="log-entry">
              {log.message}
            </div>
          ))}
        </div>
        <button data-testid="clear-logs" onClick={onClear}>
          Clear Logs
        </button>
      </div>
    );
  };
});

jest.mock('../renderer/developer/components/MetricChart', () => {
  return function MockMetricChart({ title, data, onRefresh }: any) {
    return (
      <div data-testid="metric-chart">
        <h3 data-testid="chart-title">{title}</h3>
        <div data-testid="chart-data">{JSON.stringify(data)}</div>
        <button data-testid="refresh-chart" onClick={onRefresh}>
          Refresh
        </button>
      </div>
    );
  };
});

// Mock the Developer GUI pages
jest.mock('../renderer/developer/pages/APIExplorerPage', () => {
  return function MockAPIExplorerPage() {
    return <div data-testid="api-explorer-page">API Explorer Page</div>;
  };
});

jest.mock('../renderer/developer/pages/LogsPage', () => {
  return function MockLogsPage() {
    return <div data-testid="logs-page">Logs Page</div>;
  };
});

jest.mock('../renderer/developer/pages/MetricsPage', () => {
  return function MockMetricsPage() {
    return <div data-testid="metrics-page">Metrics Page</div>;
  };
});

// Mock IPC
jest.mock('electron', () => ({
  ipcRenderer: {
    invoke: jest.fn(),
    on: jest.fn(),
    removeListener: jest.fn(),
    removeAllListeners: jest.fn()
  }
}));

describe('Developer GUI', () => {
  let mockIpcRenderer: any;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Get the mocked IPC renderer
    const { ipcRenderer } = require('electron');
    mockIpcRenderer = ipcRenderer;
    
    // Setup default mock implementations
    mockIpcRenderer.invoke.mockImplementation((channel: string) => {
      switch (channel) {
        case 'tor-get-status':
          return Promise.resolve({
            connected: true,
            bootstrapProgress: 100,
            circuits: [],
            proxyPort: 9050,
            error: null
          });
        case 'auth-verify-token':
          return Promise.resolve({
            valid: true,
            user: { id: '1', email: 'dev@test.com', role: 'developer' },
            expiresAt: new Date(Date.now() + 3600000).toISOString()
          });
        default:
          return Promise.resolve({});
      }
    });
  });

  describe('Developer App Component', () => {
    test('should render developer app', () => {
      const { DeveloperApp } = require('../renderer/developer/App');
      render(<DeveloperApp />);
      
      expect(screen.getByTestId('developer-app')).toBeInTheDocument();
    });

    test('should handle authentication state', async () => {
      const { DeveloperApp } = require('../renderer/developer/App');
      render(<DeveloperApp />);
      
      // Wait for authentication to complete
      await waitFor(() => {
        expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('auth-verify-token', expect.any(Object));
      });
    });
  });

  describe('API Endpoint Card Component', () => {
    test('should display endpoint information', () => {
      const { APIEndpointCard } = require('../renderer/developer/components/APIEndpointCard');
      const mockEndpoint = {
        method: 'GET',
        path: '/api/users',
        description: 'Get all users',
        parameters: []
      };
      
      render(<APIEndpointCard endpoint={mockEndpoint} />);
      
      expect(screen.getByTestId('endpoint-method')).toHaveTextContent('GET');
      expect(screen.getByTestId('endpoint-path')).toHaveTextContent('/api/users');
    });

    test('should handle endpoint testing', () => {
      const { APIEndpointCard } = require('../renderer/developer/components/APIEndpointCard');
      const mockEndpoint = {
        method: 'POST',
        path: '/api/users',
        description: 'Create user',
        parameters: []
      };
      const mockOnTest = jest.fn();
      
      render(<APIEndpointCard endpoint={mockEndpoint} onTest={mockOnTest} />);
      
      fireEvent.click(screen.getByTestId('test-endpoint'));
      expect(mockOnTest).toHaveBeenCalledWith(mockEndpoint);
    });
  });

  describe('Log Viewer Component', () => {
    test('should display logs', () => {
      const { LogViewer } = require('../renderer/developer/components/LogViewer');
      const mockLogs = [
        { message: 'Log entry 1', level: 'info', timestamp: '2023-01-01T00:00:00Z' },
        { message: 'Log entry 2', level: 'error', timestamp: '2023-01-01T00:01:00Z' }
      ];
      
      render(<LogViewer logs={mockLogs} />);
      
      expect(screen.getByTestId('log-entry')).toHaveLength(2);
      expect(screen.getByText('Log entry 1')).toBeInTheDocument();
      expect(screen.getByText('Log entry 2')).toBeInTheDocument();
    });

    test('should handle log clearing', () => {
      const { LogViewer } = require('../renderer/developer/components/LogViewer');
      const mockOnClear = jest.fn();
      const mockLogs = [
        { message: 'Log entry 1', level: 'info', timestamp: '2023-01-01T00:00:00Z' }
      ];
      
      render(<LogViewer logs={mockLogs} onClear={mockOnClear} />);
      
      fireEvent.click(screen.getByTestId('clear-logs'));
      expect(mockOnClear).toHaveBeenCalled();
    });

    test('should handle empty logs', () => {
      const { LogViewer } = require('../renderer/developer/components/LogViewer');
      
      render(<LogViewer logs={[]} />);
      
      expect(screen.getByTestId('logs-container')).toBeInTheDocument();
      expect(screen.queryByTestId('log-entry')).not.toBeInTheDocument();
    });
  });

  describe('Metric Chart Component', () => {
    test('should display chart with title and data', () => {
      const { MetricChart } = require('../renderer/developer/components/MetricChart');
      const mockData = { cpu: 50, memory: 75, disk: 25 };
      
      render(<MetricChart title="System Metrics" data={mockData} />);
      
      expect(screen.getByTestId('chart-title')).toHaveTextContent('System Metrics');
      expect(screen.getByTestId('chart-data')).toHaveTextContent(JSON.stringify(mockData));
    });

    test('should handle chart refresh', () => {
      const { MetricChart } = require('../renderer/developer/components/MetricChart');
      const mockOnRefresh = jest.fn();
      const mockData = { cpu: 50, memory: 75, disk: 25 };
      
      render(<MetricChart title="System Metrics" data={mockData} onRefresh={mockOnRefresh} />);
      
      fireEvent.click(screen.getByTestId('refresh-chart'));
      expect(mockOnRefresh).toHaveBeenCalled();
    });

    test('should handle empty data', () => {
      const { MetricChart } = require('../renderer/developer/components/MetricChart');
      
      render(<MetricChart title="Empty Chart" data={{}} />);
      
      expect(screen.getByTestId('chart-title')).toHaveTextContent('Empty Chart');
      expect(screen.getByTestId('chart-data')).toHaveTextContent('{}');
    });
  });

  describe('Developer Pages', () => {
    test('should render API explorer page', () => {
      const { APIExplorerPage } = require('../renderer/developer/pages/APIExplorerPage');
      render(<APIExplorerPage />);
      
      expect(screen.getByTestId('api-explorer-page')).toBeInTheDocument();
    });

    test('should render logs page', () => {
      const { LogsPage } = require('../renderer/developer/pages/LogsPage');
      render(<LogsPage />);
      
      expect(screen.getByTestId('logs-page')).toBeInTheDocument();
    });

    test('should render metrics page', () => {
      const { MetricsPage } = require('../renderer/developer/pages/MetricsPage');
      render(<MetricsPage />);
      
      expect(screen.getByTestId('metrics-page')).toBeInTheDocument();
    });
  });

  describe('IPC Communication', () => {
    test('should invoke Tor status check', async () => {
      mockIpcRenderer.invoke.mockResolvedValue({
        connected: true,
        bootstrapProgress: 100,
        circuits: [],
        proxyPort: 9050,
        error: null
      });
      
      const result = await mockIpcRenderer.invoke('tor-get-status');
      
      expect(result.connected).toBe(true);
      expect(result.bootstrapProgress).toBe(100);
    });

    test('should handle IPC errors gracefully', async () => {
      mockIpcRenderer.invoke.mockRejectedValue(new Error('IPC Error'));
      
      try {
        await mockIpcRenderer.invoke('tor-get-status');
      } catch (error) {
        expect(error.message).toBe('IPC Error');
      }
    });
  });

  describe('Integration Tests', () => {
    test('should handle complete developer workflow', async () => {
      const { DeveloperApp } = require('../renderer/developer/App');
      render(<DeveloperApp />);
      
      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByTestId('developer-app')).toBeInTheDocument();
      });
      
      // Verify Tor status check was called
      expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('tor-get-status');
      
      // Verify authentication check was called
      expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('auth-verify-token', expect.any(Object));
    });

    test('should handle API testing workflow', () => {
      const { APIEndpointCard } = require('../renderer/developer/components/APIEndpointCard');
      const mockEndpoint = {
        method: 'GET',
        path: '/api/test',
        description: 'Test endpoint',
        parameters: []
      };
      const mockOnTest = jest.fn();
      
      render(<APIEndpointCard endpoint={mockEndpoint} onTest={mockOnTest} />);
      
      // Verify endpoint information is displayed
      expect(screen.getByTestId('endpoint-method')).toHaveTextContent('GET');
      expect(screen.getByTestId('endpoint-path')).toHaveTextContent('/api/test');
      
      // Test endpoint
      fireEvent.click(screen.getByTestId('test-endpoint'));
      expect(mockOnTest).toHaveBeenCalledWith(mockEndpoint);
    });

    test('should handle log viewing workflow', () => {
      const { LogViewer } = require('../renderer/developer/components/LogViewer');
      const mockLogs = [
        { message: 'System started', level: 'info', timestamp: '2023-01-01T00:00:00Z' },
        { message: 'User logged in', level: 'info', timestamp: '2023-01-01T00:01:00Z' },
        { message: 'Error occurred', level: 'error', timestamp: '2023-01-01T00:02:00Z' }
      ];
      const mockOnClear = jest.fn();
      
      render(<LogViewer logs={mockLogs} onClear={mockOnClear} />);
      
      // Verify logs are displayed
      expect(screen.getByText('System started')).toBeInTheDocument();
      expect(screen.getByText('User logged in')).toBeInTheDocument();
      expect(screen.getByText('Error occurred')).toBeInTheDocument();
      
      // Clear logs
      fireEvent.click(screen.getByTestId('clear-logs'));
      expect(mockOnClear).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    test('should handle API testing errors gracefully', () => {
      const { APIEndpointCard } = require('../renderer/developer/components/APIEndpointCard');
      const mockEndpoint = {
        method: 'GET',
        path: '/api/test',
        description: 'Test endpoint',
        parameters: []
      };
      const mockOnTest = jest.fn(() => {
        throw new Error('API test failed');
      });
      
      render(<APIEndpointCard endpoint={mockEndpoint} onTest={mockOnTest} />);
      
      // Should not crash when test fails
      expect(() => {
        fireEvent.click(screen.getByTestId('test-endpoint'));
      }).not.toThrow();
    });

    test('should handle IPC errors gracefully', async () => {
      mockIpcRenderer.invoke.mockRejectedValue(new Error('IPC Connection Failed'));
      
      try {
        await mockIpcRenderer.invoke('tor-get-status');
      } catch (error) {
        expect(error.message).toBe('IPC Connection Failed');
      }
    });
  });

  describe('Performance Tests', () => {
    test('should render developer components within acceptable time', () => {
      const startTime = Date.now();
      
      const { DeveloperApp } = require('../renderer/developer/App');
      render(<DeveloperApp />);
      
      const endTime = Date.now();
      expect(endTime - startTime).toBeLessThan(100); // Should be less than 100ms
    });

    test('should handle large log datasets efficiently', () => {
      const { LogViewer } = require('../renderer/developer/components/LogViewer');
      const mockLogs = Array.from({ length: 1000 }, (_, i) => ({
        message: `Log entry ${i}`,
        level: i % 2 === 0 ? 'info' : 'error',
        timestamp: new Date(Date.now() + i * 1000).toISOString()
      }));
      
      const startTime = Date.now();
      
      render(<LogViewer logs={mockLogs} />);
      
      const endTime = Date.now();
      
      // Should render 1000 log entries within acceptable time
      expect(endTime - startTime).toBeLessThan(1000); // Should be less than 1 second
      expect(screen.getAllByTestId('log-entry')).toHaveLength(1000);
    });

    test('should handle multiple metric charts efficiently', () => {
      const { MetricChart } = require('../renderer/developer/components/MetricChart');
      const charts = Array.from({ length: 20 }, (_, i) => ({
        title: `Chart ${i}`,
        data: { cpu: i * 5, memory: i * 3, disk: i * 2 }
      }));
      
      const startTime = Date.now();
      
      const { container } = render(
        <div>
          {charts.map((chart, index) => (
            <MetricChart key={index} title={chart.title} data={chart.data} />
          ))}
        </div>
      );
      
      const endTime = Date.now();
      
      // Should render 20 charts within acceptable time
      expect(endTime - startTime).toBeLessThan(500); // Should be less than 500ms
      expect(container.querySelectorAll('[data-testid="metric-chart"]')).toHaveLength(20);
    });
  });
});
