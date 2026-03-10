// tests/e2e/setup.ts - E2E test setup file
// Based on the electron-multi-gui-development.plan.md specifications

import { beforeAll, afterAll, beforeEach, afterEach } from '@jest/globals';

// Mock Electron and Playwright for E2E tests
jest.mock('electron', () => ({
  app: {
    whenReady: jest.fn(() => Promise.resolve()),
    on: jest.fn(),
    quit: jest.fn(),
    getName: jest.fn(() => 'Lucid Electron GUI'),
    getVersion: jest.fn(() => '1.0.0'),
    isReady: jest.fn(() => true)
  },
  BrowserWindow: jest.fn().mockImplementation(() => ({
    loadFile: jest.fn(),
    loadURL: jest.fn(),
    webContents: {
      send: jest.fn(),
      on: jest.fn(),
      session: {
        cookies: {
          set: jest.fn(),
          remove: jest.fn(),
          get: jest.fn()
        }
      }
    },
    on: jest.fn(),
    show: jest.fn(),
    hide: jest.fn(),
    close: jest.fn(),
    destroy: jest.fn(),
    isVisible: jest.fn(() => true),
    isFocused: jest.fn(() => false),
    focus: jest.fn(),
    minimize: jest.fn(),
    maximize: jest.fn(),
    restore: jest.fn()
  })),
  ipcMain: {
    handle: jest.fn(),
    on: jest.fn(),
    removeHandler: jest.fn(),
    removeAllListeners: jest.fn()
  },
  ipcRenderer: {
    invoke: jest.fn(),
    on: jest.fn(),
    removeListener: jest.fn(),
    removeAllListeners: jest.fn()
  }
}));

// Mock Playwright
jest.mock('playwright', () => ({
  chromium: {
    launch: jest.fn(() => Promise.resolve({
      newPage: jest.fn(() => Promise.resolve({
        goto: jest.fn(),
        click: jest.fn(),
        fill: jest.fn(),
        waitForSelector: jest.fn(),
        evaluate: jest.fn(),
        screenshot: jest.fn(),
        close: jest.fn()
      })),
      close: jest.fn()
    }))
  }
}));

// Global test setup
beforeAll(async () => {
  console.log('Setting up E2E test environment...');
  
  // Setup test database if needed
  // await setupTestDatabase();
  
  // Setup test services
  // await setupTestServices();
  
  console.log('E2E test environment setup complete');
});

afterAll(async () => {
  console.log('Cleaning up E2E test environment...');
  
  // Cleanup test database
  // await cleanupTestDatabase();
  
  // Cleanup test services
  // await cleanupTestServices();
  
  console.log('E2E test environment cleanup complete');
});

beforeEach(() => {
  // Reset mocks before each test
  jest.clearAllMocks();
  
  // Setup default mock implementations
  const { ipcRenderer } = require('electron');
  ipcRenderer.invoke.mockImplementation((channel: string) => {
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
          user: { id: '1', email: 'test@test.com', role: 'admin' },
          expiresAt: new Date(Date.now() + 3600000).toISOString()
        });
      case 'docker-get-service-status':
        return Promise.resolve({
          services: [
            {
              name: 'api-gateway',
              status: 'running',
              containerId: 'container-1',
              image: 'lucid/api-gateway:latest',
              ports: ['3000:3000'],
              health: 'healthy',
              uptime: 3600
            }
          ]
        });
      default:
        return Promise.resolve({});
    }
  });
});

afterEach(() => {
  // Cleanup after each test
  jest.restoreAllMocks();
});

// Helper functions for E2E tests
export const E2ETestHelpers = {
  // Wait for element to be visible
  waitForElement: async (selector: string, timeout = 5000) => {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      const element = document.querySelector(selector);
      if (element && element.offsetParent !== null) {
        return element;
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error(`Element ${selector} not found within ${timeout}ms`);
  },

  // Simulate user interaction
  simulateUserInteraction: async (action: string, target: string, data?: any) => {
    const element = await E2ETestHelpers.waitForElement(target);
    
    switch (action) {
      case 'click':
        element.click();
        break;
      case 'type':
        element.value = data;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        break;
      case 'select':
        element.value = data;
        element.dispatchEvent(new Event('change', { bubbles: true }));
        break;
      default:
        throw new Error(`Unknown action: ${action}`);
    }
  },

  // Take screenshot for debugging
  takeScreenshot: async (name: string) => {
    const { chromium } = require('playwright');
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    // Navigate to the app
    await page.goto('http://localhost:3000');
    
    // Take screenshot
    await page.screenshot({ path: `tests/e2e/screenshots/${name}.png` });
    
    await browser.close();
  },

  // Mock API responses
  mockAPIResponse: (endpoint: string, response: any) => {
    const { ipcRenderer } = require('electron');
    ipcRenderer.invoke.mockImplementation((channel: string, data: any) => {
      if (channel === 'api-request' && data.url.includes(endpoint)) {
        return Promise.resolve({
          success: true,
          data: response,
          status: 200,
          headers: {}
        });
      }
      return Promise.resolve({});
    });
  },

  // Mock Tor status
  mockTorStatus: (connected: boolean, progress = 100) => {
    const { ipcRenderer } = require('electron');
    ipcRenderer.invoke.mockImplementation((channel: string) => {
      if (channel === 'tor-get-status') {
        return Promise.resolve({
          connected,
          bootstrapProgress: progress,
          circuits: connected ? [{ id: '1', status: 'built', path: [], age: 0 }] : [],
          proxyPort: 9050,
          error: connected ? null : 'Connection failed'
        });
      }
      return Promise.resolve({});
    });
  },

  // Mock Docker service status
  mockDockerStatus: (services: any[]) => {
    const { ipcRenderer } = require('electron');
    ipcRenderer.invoke.mockImplementation((channel: string) => {
      if (channel === 'docker-get-service-status') {
        return Promise.resolve({
          services: services.map(service => ({
            name: service.name,
            status: service.status || 'running',
            containerId: service.containerId || 'container-1',
            image: service.image || 'lucid/service:latest',
            ports: service.ports || ['3000:3000'],
            health: service.health || 'healthy',
            uptime: service.uptime || 3600
          }))
        });
      }
      return Promise.resolve({});
    });
  },

  // Mock authentication
  mockAuthentication: (valid: boolean, user?: any) => {
    const { ipcRenderer } = require('electron');
    ipcRenderer.invoke.mockImplementation((channel: string) => {
      if (channel === 'auth-verify-token') {
        return Promise.resolve({
          valid,
          user: valid ? (user || { id: '1', email: 'test@test.com', role: 'admin' }) : null,
          expiresAt: valid ? new Date(Date.now() + 3600000).toISOString() : null
        });
      }
      return Promise.resolve({});
    });
  }
};

// Export helper functions
export const { waitForElement, simulateUserInteraction, takeScreenshot, mockAPIResponse, mockTorStatus, mockDockerStatus, mockAuthentication } = E2ETestHelpers;
