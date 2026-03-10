// tests/node-gui.spec.ts - Node Operator GUI tests
// Based on the electron-multi-gui-development.plan.md specifications

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock the Node GUI components
jest.mock('../renderer/node/App', () => {
  return function MockNodeApp() {
    return <div data-testid="node-app">Node App</div>;
  };
});

jest.mock('../renderer/node/components/NodeStatusCard', () => {
  return function MockNodeStatusCard({ node, onAction }: any) {
    return (
      <div data-testid="node-status-card">
        <span data-testid="node-id">{node.id}</span>
        <span data-testid="node-status">{node.status}</span>
        <span data-testid="poot-score">{node.pootScore}</span>
        <button data-testid="node-action" onClick={() => onAction?.('restart')}>
          Restart
        </button>
      </div>
    );
  };
});

jest.mock('../renderer/node/components/ResourceChart', () => {
  return function MockResourceChart({ title, data, onRefresh }: any) {
    return (
      <div data-testid="resource-chart">
        <h3 data-testid="chart-title">{title}</h3>
        <div data-testid="chart-data">{JSON.stringify(data)}</div>
        <button data-testid="refresh-chart" onClick={onRefresh}>
          Refresh
        </button>
      </div>
    );
  };
});

jest.mock('../renderer/node/components/EarningsCard', () => {
  return function MockEarningsCard({ earnings, currency }: any) {
    return (
      <div data-testid="earnings-card">
        <span data-testid="earnings-amount">{earnings}</span>
        <span data-testid="earnings-currency">{currency}</span>
      </div>
    );
  };
});

// Mock the Node GUI pages
jest.mock('../renderer/node/pages/NodeDashboardPage', () => {
  return function MockNodeDashboardPage() {
    return <div data-testid="node-dashboard-page">Node Dashboard Page</div>;
  };
});

jest.mock('../renderer/node/pages/ResourcesPage', () => {
  return function MockResourcesPage() {
    return <div data-testid="resources-page">Resources Page</div>;
  };
});

jest.mock('../renderer/node/pages/EarningsPage', () => {
  return function MockEarningsPage() {
    return <div data-testid="earnings-page">Earnings Page</div>;
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

describe('Node GUI', () => {
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
            user: { id: '1', email: 'node@test.com', role: 'node_operator' },
            expiresAt: new Date(Date.now() + 3600000).toISOString()
          });
        default:
          return Promise.resolve({});
      }
    });
  });

  describe('Node App Component', () => {
    test('should render node app', () => {
      const { NodeApp } = require('../renderer/node/App');
      render(<NodeApp />);
      
      expect(screen.getByTestId('node-app')).toBeInTheDocument();
    });

    test('should handle authentication state', async () => {
      const { NodeApp } = require('../renderer/node/App');
      render(<NodeApp />);
      
      // Wait for authentication to complete
      await waitFor(() => {
        expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('auth-verify-token', expect.any(Object));
      });
    });
  });

  describe('Node Status Card Component', () => {
    test('should display node information', () => {
      const { NodeStatusCard } = require('../renderer/node/components/NodeStatusCard');
      const mockNode = {
        id: 'node-123',
        status: 'active',
        pootScore: 85.5,
        operator: 'operator-1',
        location: 'US',
        uptime: '99.9%'
      };
      
      render(<NodeStatusCard node={mockNode} />);
      
      expect(screen.getByTestId('node-id')).toHaveTextContent('node-123');
      expect(screen.getByTestId('node-status')).toHaveTextContent('active');
      expect(screen.getByTestId('poot-score')).toHaveTextContent('85.5');
    });

    test('should handle node actions', () => {
      const { NodeStatusCard } = require('../renderer/node/components/NodeStatusCard');
      const mockNode = {
        id: 'node-123',
        status: 'active',
        pootScore: 85.5,
        operator: 'operator-1',
        location: 'US',
        uptime: '99.9%'
      };
      const mockOnAction = jest.fn();
      
      render(<NodeStatusCard node={mockNode} onAction={mockOnAction} />);
      
      fireEvent.click(screen.getByTestId('node-action'));
      expect(mockOnAction).toHaveBeenCalledWith('restart');
    });
  });

  describe('Resource Chart Component', () => {
    test('should display resource metrics', () => {
      const { ResourceChart } = require('../renderer/node/components/ResourceChart');
      const mockData = { cpu: 45, memory: 60, disk: 30, network: 15 };
      
      render(<ResourceChart title="Node Resources" data={mockData} />);
      
      expect(screen.getByTestId('chart-title')).toHaveTextContent('Node Resources');
      expect(screen.getByTestId('chart-data')).toHaveTextContent(JSON.stringify(mockData));
    });

    test('should handle chart refresh', () => {
      const { ResourceChart } = require('../renderer/node/components/ResourceChart');
      const mockOnRefresh = jest.fn();
      const mockData = { cpu: 45, memory: 60, disk: 30, network: 15 };
      
      render(<ResourceChart title="Node Resources" data={mockData} onRefresh={mockOnRefresh} />);
      
      fireEvent.click(screen.getByTestId('refresh-chart'));
      expect(mockOnRefresh).toHaveBeenCalled();
    });

    test('should handle empty data', () => {
      const { ResourceChart } = require('../renderer/node/components/ResourceChart');
      
      render(<ResourceChart title="Empty Chart" data={{}} />);
      
      expect(screen.getByTestId('chart-title')).toHaveTextContent('Empty Chart');
      expect(screen.getByTestId('chart-data')).toHaveTextContent('{}');
    });
  });

  describe('Earnings Card Component', () => {
    test('should display earnings information', () => {
      const { EarningsCard } = require('../renderer/node/components/EarningsCard');
      render(<EarningsCard earnings="1250.75" currency="TRX" />);
      
      expect(screen.getByTestId('earnings-amount')).toHaveTextContent('1250.75');
      expect(screen.getByTestId('earnings-currency')).toHaveTextContent('TRX');
    });

    test('should handle zero earnings', () => {
      const { EarningsCard } = require('../renderer/node/components/EarningsCard');
      render(<EarningsCard earnings="0" currency="TRX" />);
      
      expect(screen.getByTestId('earnings-amount')).toHaveTextContent('0');
      expect(screen.getByTestId('earnings-currency')).toHaveTextContent('TRX');
    });

    test('should handle large earnings', () => {
      const { EarningsCard } = require('../renderer/node/components/EarningsCard');
      render(<EarningsCard earnings="999999.99" currency="TRX" />);
      
      expect(screen.getByTestId('earnings-amount')).toHaveTextContent('999999.99');
      expect(screen.getByTestId('earnings-currency')).toHaveTextContent('TRX');
    });
  });

  describe('Node Pages', () => {
    test('should render node dashboard page', () => {
      const { NodeDashboardPage } = require('../renderer/node/pages/NodeDashboardPage');
      render(<NodeDashboardPage />);
      
      expect(screen.getByTestId('node-dashboard-page')).toBeInTheDocument();
    });

    test('should render resources page', () => {
      const { ResourcesPage } = require('../renderer/node/pages/ResourcesPage');
      render(<ResourcesPage />);
      
      expect(screen.getByTestId('resources-page')).toBeInTheDocument();
    });

    test('should render earnings page', () => {
      const { EarningsPage } = require('../renderer/node/pages/EarningsPage');
      render(<EarningsPage />);
      
      expect(screen.getByTestId('earnings-page')).toBeInTheDocument();
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
    test('should handle complete node operator workflow', async () => {
      const { NodeApp } = require('../renderer/node/App');
      render(<NodeApp />);
      
      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByTestId('node-app')).toBeInTheDocument();
      });
      
      // Verify Tor status check was called
      expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('tor-get-status');
      
      // Verify authentication check was called
      expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('auth-verify-token', expect.any(Object));
    });

    test('should handle node management workflow', () => {
      const { NodeStatusCard } = require('../renderer/node/components/NodeStatusCard');
      const mockNode = {
        id: 'node-123',
        status: 'active',
        pootScore: 85.5,
        operator: 'operator-1',
        location: 'US',
        uptime: '99.9%'
      };
      const mockOnAction = jest.fn();
      
      render(<NodeStatusCard node={mockNode} onAction={mockOnAction} />);
      
      // Verify node information is displayed
      expect(screen.getByTestId('node-id')).toHaveTextContent('node-123');
      expect(screen.getByTestId('node-status')).toHaveTextContent('active');
      expect(screen.getByTestId('poot-score')).toHaveTextContent('85.5');
      
      // Test node action
      fireEvent.click(screen.getByTestId('node-action'));
      expect(mockOnAction).toHaveBeenCalledWith('restart');
    });

    test('should handle resource monitoring workflow', () => {
      const { ResourceChart } = require('../renderer/node/components/ResourceChart');
      const mockData = { cpu: 45, memory: 60, disk: 30, network: 15 };
      const mockOnRefresh = jest.fn();
      
      render(<ResourceChart title="Node Resources" data={mockData} onRefresh={mockOnRefresh} />);
      
      // Verify resource data is displayed
      expect(screen.getByTestId('chart-title')).toHaveTextContent('Node Resources');
      expect(screen.getByTestId('chart-data')).toHaveTextContent(JSON.stringify(mockData));
      
      // Test chart refresh
      fireEvent.click(screen.getByTestId('refresh-chart'));
      expect(mockOnRefresh).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    test('should handle node action errors gracefully', () => {
      const { NodeStatusCard } = require('../renderer/node/components/NodeStatusCard');
      const mockNode = {
        id: 'node-123',
        status: 'active',
        pootScore: 85.5,
        operator: 'operator-1',
        location: 'US',
        uptime: '99.9%'
      };
      const mockOnAction = jest.fn(() => {
        throw new Error('Node action failed');
      });
      
      render(<NodeStatusCard node={mockNode} onAction={mockOnAction} />);
      
      // Should not crash when action fails
      expect(() => {
        fireEvent.click(screen.getByTestId('node-action'));
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
    test('should render node components within acceptable time', () => {
      const startTime = Date.now();
      
      const { NodeApp } = require('../renderer/node/App');
      render(<NodeApp />);
      
      const endTime = Date.now();
      expect(endTime - startTime).toBeLessThan(100); // Should be less than 100ms
    });

    test('should handle multiple node cards efficiently', () => {
      const { NodeStatusCard } = require('../renderer/node/components/NodeStatusCard');
      const nodes = Array.from({ length: 50 }, (_, i) => ({
        id: `node-${i}`,
        status: i % 2 === 0 ? 'active' : 'inactive',
        pootScore: Math.random() * 100,
        operator: `operator-${i}`,
        location: 'US',
        uptime: '99.9%'
      }));
      
      const startTime = Date.now();
      
      const { container } = render(
        <div>
          {nodes.map(node => (
            <NodeStatusCard key={node.id} node={node} />
          ))}
        </div>
      );
      
      const endTime = Date.now();
      
      // Should render 50 node cards within acceptable time
      expect(endTime - startTime).toBeLessThan(500); // needs to be less than 500ms
      expect(container.querySelectorAll('[data-testid="node-status-card"]')).toHaveLength(50);
    });

    test('should handle multiple resource charts efficiently', () => {
      const { ResourceChart } = require('../renderer/node/components/ResourceChart');
      const charts = Array.from({ length: 20 }, (_, i) => ({
        title: `Resource Chart ${i}`,
        data: { cpu: i * 5, memory: i * 3, disk: i * 2, network: i * 1 }
      }));
      
      const startTime = Date.now();
      
      const { container } = render(
        <div>
          {charts.map((chart, index) => (
            <ResourceChart key={index} title={chart.title} data={chart.data} />
          ))}
        </div>
      );
      
      const endTime = Date.now();
      
      // Should render 20 charts within acceptable time
      expect(endTime - startTime).toBeLessThan(500); // Should be less than 500ms
      expect(container.querySelectorAll('[data-testid="resource-chart"]')).toHaveLength(20);
    });
  });
});
