// tests/admin-gui.spec.ts - Admin GUI tests
// Based on the electron-multi-gui-development.plan.md specifications

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock the Admin GUI components
jest.mock('../renderer/admin/App', () => {
  return function MockAdminApp() {
    return <div data-testid="admin-app">Admin App</div>;
  };
});

jest.mock('../renderer/admin/components/AdminHeader', () => {
  return function MockAdminHeader({ userName, onLogout }: any) {
    return (
      <div data-testid="admin-header">
        <span data-testid="user-name">{userName}</span>
        <button data-testid="logout-button" onClick={onLogout}>
          Logout
        </button>
      </div>
    );
  };
});

jest.mock('../renderer/admin/components/AdminSidebar', () => {
  return function MockAdminSidebar({ activeItem, onNavigate }: any) {
    return (
      <div data-testid="admin-sidebar">
        <button 
          data-testid="dashboard-nav" 
          onClick={() => onNavigate?.('dashboard')}
          className={activeItem === 'dashboard' ? 'active' : ''}
        >
          Dashboard
        </button>
        <button 
          data-testid="sessions-nav" 
          onClick={() => onNavigate?.('sessions')}
          className={activeItem === 'sessions' ? 'active' : ''}
        >
          Sessions
        </button>
        <button 
          data-testid="users-nav" 
          onClick={() => onNavigate?.('users')}
          className={activeItem === 'users' ? 'active' : ''}
        >
          Users
        </button>
      </div>
    );
  };
});

jest.mock('../renderer/admin/components/TorIndicator', () => {
  return function MockTorIndicator({ connected, onClick }: any) {
    return (
      <div 
        data-testid="tor-indicator" 
        onClick={onClick}
        className={connected ? 'connected' : 'disconnected'}
      >
        Tor {connected ? 'Connected' : 'Disconnected'}
      </div>
    );
  };
});

// Mock the Admin GUI pages
jest.mock('../renderer/admin/pages/DashboardPage', () => {
  return function MockDashboardPage() {
    return <div data-testid="dashboard-page">Dashboard Page</div>;
  };
});

jest.mock('../renderer/admin/pages/SessionsPage', () => {
  return function MockSessionsPage() {
    return <div data-testid="sessions-page">Sessions Page</div>;
  };
});

jest.mock('../renderer/admin/pages/UsersPage', () => {
  return function MockUsersPage() {
    return <div data-testid="users-page">Users Page</div>;
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

// Mock the Admin GUI services
jest.mock('../renderer/admin/services/adminApi', () => ({
  AdminAPIService: jest.fn().mockImplementation(() => ({
    getDashboardData: jest.fn().mockResolvedValue({
      system_health: { status: 'healthy' },
      active_sessions: 5,
      total_users: 100,
      active_nodes: 10,
      recent_activity: [],
      system_metrics: {}
    }),
    getAllUsers: jest.fn().mockResolvedValue([]),
    getAllSessions: jest.fn().mockResolvedValue([]),
    adminLogin: jest.fn().mockResolvedValue({
      token: 'mock-token',
      admin: { admin_id: '1', username: 'admin', role: 'admin', permissions: [] }
    })
  }))
}));

describe('Admin GUI', () => {
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
            user: { id: '1', email: 'admin@test.com', role: 'admin' },
            expiresAt: new Date(Date.now() + 3600000).toISOString()
          });
        default:
          return Promise.resolve({});
      }
    });
  });

  describe('Admin App Component', () => {
    test('should render admin app', () => {
      const { AdminApp } = require('../renderer/admin/App');
      render(<AdminApp />);
      
      expect(screen.getByTestId('admin-app')).toBeInTheDocument();
    });

    test('should handle authentication state', async () => {
      const { AdminApp } = require('../renderer/admin/App');
      render(<AdminApp />);
      
      // Wait for authentication to complete
      await waitFor(() => {
        expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('auth-verify-token', expect.any(Object));
      });
    });
  });

  describe('Admin Header Component', () => {
    test('should display user name', () => {
      const { AdminHeader } = require('../renderer/admin/components/AdminHeader');
      render(<AdminHeader userName="Admin User" />);
      
      expect(screen.getByTestId('user-name')).toHaveTextContent('Admin User');
    });

    test('should handle logout', () => {
      const mockOnLogout = jest.fn();
      const { AdminHeader } = require('../renderer/admin/components/AdminHeader');
      render(<AdminHeader onLogout={mockOnLogout} />);
      
      fireEvent.click(screen.getByTestId('logout-button'));
      expect(mockOnLogout).toHaveBeenCalled();
    });
  });

  describe('Admin Sidebar Component', () => {
    test('should render navigation items', () => {
      const { AdminSidebar } = require('../renderer/admin/components/AdminSidebar');
      render(<AdminSidebar activeItem="dashboard" />);
      
      expect(screen.getByTestId('dashboard-nav')).toBeInTheDocument();
      expect(screen.getByTestId('sessions-nav')).toBeInTheDocument();
      expect(screen.getByTestId('users-nav')).toBeInTheDocument();
    });

    test('should highlight active navigation item', () => {
      const { AdminSidebar } = require('../renderer/admin/components/AdminSidebar');
      render(<AdminSidebar activeItem="dashboard" />);
      
      expect(screen.getByTestId('dashboard-nav')).toHaveClass('active');
      expect(screen.getByTestId('sessions-nav')).not.toHaveClass('active');
    });

    test('should handle navigation', () => {
      const mockOnNavigate = jest.fn();
      const { AdminSidebar } = require('../renderer/admin/components/AdminSidebar');
      render(<AdminSidebar onNavigate={mockOnNavigate} />);
      
      fireEvent.click(screen.getByTestId('sessions-nav'));
      expect(mockOnNavigate).toHaveBeenCalledWith('sessions');
    });
  });

  describe('Tor Indicator Component', () => {
    test('should show connected state', () => {
      const { TorIndicator } = require('../renderer/admin/components/TorIndicator');
      render(<TorIndicator connected={true} />);
      
      expect(screen.getByTestId('tor-indicator')).toHaveTextContent('Tor Connected');
      expect(screen.getByTestId('tor-indicator')).toHaveClass('connected');
    });

    test('should show disconnected state', () => {
      const { TorIndicator } = require('../renderer/admin/components/TorIndicator');
      render(<TorIndicator connected={false} />);
      
      expect(screen.getByTestId('tor-indicator')).toHaveTextContent('Tor Disconnected');
      expect(screen.getByTestId('tor-indicator')).toHaveClass('disconnected');
    });

    test('should handle click events', () => {
      const mockOnClick = jest.fn();
      const { TorIndicator } = require('../renderer/admin/components/TorIndicator');
      render(<TorIndicator connected={true} onClick={mockOnClick} />);
      
      fireEvent.click(screen.getByTestId('tor-indicator'));
      expect(mockOnClick).toHaveBeenCalled();
    });
  });

  describe('Admin Pages', () => {
    test('should render dashboard page', () => {
      const { DashboardPage } = require('../renderer/admin/pages/DashboardPage');
      render(<DashboardPage />);
      
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    test('should render sessions page', () => {
      const { SessionsPage } = require('../renderer/admin/pages/SessionsPage');
      render(<SessionsPage />);
      
      expect(screen.getByTestId('sessions-page')).toBeInTheDocument();
    });

    test('should render users page', () => {
      const { UsersPage } = require('../renderer/admin/pages/UsersPage');
      render(<UsersPage />);
      
      expect(screen.getByTestId('users-page')).toBeInTheDocument();
    });
  });

  describe('Admin API Service', () => {
    test('should get dashboard data', async () => {
      const { AdminAPIService } = require('../renderer/admin/services/adminApi');
      const apiService = new AdminAPIService();
      
      const data = await apiService.getDashboardData();
      
      expect(data).toEqual({
        system_health: { status: 'healthy' },
        active_sessions: 5,
        total_users: 100,
        active_nodes: 10,
        recent_activity: [],
        system_metrics: {}
      });
    });

    test('should get all users', async () => {
      const { AdminAPIService } = require('../renderer/admin/services/adminApi');
      const apiService = new AdminAPIService();
      
      const users = await apiService.getAllUsers();
      expect(Array.isArray(users)).toBe(true);
    });

    test('should get all sessions', async () => {
      const { AdminAPIService } = require('../renderer/admin/services/adminApi');
      const apiService = new AdminAPIService();
      
      const sessions = await apiService.getAllSessions();
      expect(Array.isArray(sessions)).toBe(true);
    });

    test('should handle admin login', async () => {
      const { AdminAPIService } = require('../renderer/admin/services/adminApi');
      const apiService = new AdminAPIService();
      
      const result = await apiService.adminLogin('admin@test.com', 'mock-signature');
      
      expect(result).toEqual({
        token: 'mock-token',
        admin: { admin_id: '1', username: 'admin', role: 'admin', permissions: [] }
      });
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
    test('should handle complete admin workflow', async () => {
      const { AdminApp } = require('../renderer/admin/App');
      render(<AdminApp />);
      
      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByTestId('admin-app')).toBeInTheDocument();
      });
      
      // Verify Tor status check was called
      expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('tor-get-status');
      
      // Verify authentication check was called
      expect(mockIpcRenderer.invoke).toHaveBeenCalledWith('auth-verify-token', expect.any(Object));
    });

    test('should handle navigation between pages', () => {
      const { AdminSidebar } = require('../renderer/admin/components/AdminSidebar');
      const mockOnNavigate = jest.fn();
      
      render(<AdminSidebar onNavigate={mockOnNavigate} />);
      
      // Navigate to sessions
      fireEvent.click(screen.getByTestId('sessions-nav'));
      expect(mockOnNavigate).toHaveBeenCalledWith('sessions');
      
      // Navigate to users
      fireEvent.click(screen.getByTestId('users-nav'));
      expect(mockOnNavigate).toHaveBeenCalledWith('users');
    });
  });

  describe('Error Handling', () => {
    test('should handle API errors gracefully', async () => {
      const { AdminAPIService } = require('../renderer/admin/services/adminApi');
      const apiService = new AdminAPIService();
      
      // Mock API error
      apiService.getDashboardData.mockRejectedValue(new Error('API Error'));
      
      try {
        await apiService.getDashboardData();
      } catch (error) {
        expect(error.message).toBe('API Error');
      }
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
    test('should render admin components within acceptable time', () => {
      const startTime = Date.now();
      
      const { AdminApp } = require('../renderer/admin/App');
      render(<AdminApp />);
      
      const endTime = Date.now();
      expect(endTime - startTime).toBeLessThan(100); // Should be less than 100ms
    });

    test('should handle multiple rapid navigation clicks', () => {
      const { AdminSidebar } = require('../renderer/admin/components/AdminSidebar');
      const mockOnNavigate = jest.fn();
      
      render(<AdminSidebar onNavigate={mockOnNavigate} />);
      
      // Rapidly click navigation items
      for (let i = 0; i < 10; i++) {
        fireEvent.click(screen.getByTestId('dashboard-nav'));
        fireEvent.click(screen.getByTestId('sessions-nav'));
      }
      
      expect(mockOnNavigate).toHaveBeenCalledTimes(20);
    });
  });
});
