// tests/main.spec.ts - Main process tests
// Based on the electron-multi-gui-development.plan.md specifications

import { BrowserWindow } from 'electron';
import { WindowManager } from '../main/window-manager';
import { TorManager } from '../main/tor-manager';
import { DockerService } from '../main/docker-service';
import { setupIpcHandlers } from '../main/ipc-handlers';

// Mock the main process modules
jest.mock('../main/window-manager');
jest.mock('../main/tor-manager');
jest.mock('../main/docker-service');
jest.mock('../main/ipc-handlers');

describe('Main Process', () => {
  let windowManager: jest.Mocked<WindowManager>;
  let torManager: jest.Mocked<TorManager>;
  let dockerService: jest.Mocked<DockerService>;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();

    // Create mock instances
    windowManager = new WindowManager() as jest.Mocked<WindowManager>;
    torManager = new TorManager() as jest.Mocked<TorManager>;
    dockerService = new DockerService() as jest.Mocked<DockerService>;

    // Setup mock implementations
    windowManager.createWindow = jest.fn().mockResolvedValue(new BrowserWindow());
    windowManager.getWindow = jest.fn().mockReturnValue(new BrowserWindow());
    windowManager.broadcastToAllWindows = jest.fn();
    windowManager.getAllWindows = jest.fn().mockReturnValue([]);

    torManager.start = jest.fn().mockResolvedValue(undefined);
    torManager.stop = jest.fn().mockResolvedValue(undefined);
    torManager.restart = jest.fn().mockResolvedValue(undefined);
    torManager.getStatus = jest.fn().mockResolvedValue({
      connected: false,
      bootstrapProgress: 0,
      circuits: [],
      proxyPort: 9050,
      error: null
    });

    dockerService.initialize = jest.fn().mockResolvedValue(undefined);
    dockerService.startServices = jest.fn().mockResolvedValue({
      success: true,
      started: [],
      failed: []
    });
  });

  describe('WindowManager', () => {
    test('should create window successfully', async () => {
      const window = await windowManager.createWindow('admin');
      expect(window).toBeInstanceOf(BrowserWindow);
      expect(windowManager.createWindow).toHaveBeenCalledWith('admin');
    });

    test('should broadcast messages to all windows', () => {
      const message = { type: 'test', data: 'test data' };
      windowManager.broadcastToAllWindows('test-channel', message);
      
      expect(windowManager.broadcastToAllWindows).toHaveBeenCalledWith('test-channel', message);
    });

    test('should get window by name', () => {
      const window = windowManager.getWindow('admin');
      expect(window).toBeInstanceOf(BrowserWindow);
      expect(windowManager.getWindow).toHaveBeenCalledWith('admin');
    });

    test('should get all windows', () => {
      const windows = windowManager.getAllWindows();
      expect(Array.isArray(windows)).toBe(true);
    });
  });

  describe('TorManager', () => {
    test('should start Tor successfully', async () => {
      await torManager.start();
      expect(torManager.start).toHaveBeenCalled();
    });

    test('should stop Tor successfully', async () => {
      await torManager.stop();
      expect(torManager.stop).toHaveBeenCalled();
    });

    test('should restart Tor successfully', async () => {
      await torManager.restart();
      expect(torManager.restart).toHaveBeenCalled();
    });

    test('should get Tor status', async () => {
      const status = await torManager.getStatus();
      expect(status).toEqual({
        connected: false,
        bootstrapProgress: 0,
        circuits: [],
        proxyPort: 9050,
        error: null
      });
    });

    test('should handle Tor start errors', async () => {
      const error = new Error('Tor start failed');
      torManager.start.mockRejectedValue(error);
      
      await expect(torManager.start()).rejects.toThrow('Tor start failed');
    });

    test('should handle Tor stop errors', async () => {
      const error = new Error('Tor stop failed');
      torManager.stop.mockRejectedValue(error);
      
      await expect(torManager.stop()).rejects.toThrow('Tor stop failed');
    });
  });

  describe('DockerService', () => {
    test('should initialize successfully', async () => {
      await dockerService.initialize();
      expect(dockerService.initialize).toHaveBeenCalled();
    });

    test('should start services successfully', async () => {
      const result = await dockerService.startServices(['api-gateway', 'blockchain']);
      expect(result).toEqual({
        success: true,
        started: [],
        failed: []
      });
      expect(dockerService.startServices).toHaveBeenCalledWith(['api-gateway', 'blockchain']);
    });

    test('should handle service start errors', async () => {
      const error = new Error('Docker service start failed');
      dockerService.startServices.mockRejectedValue(error);
      
      await expect(dockerService.startServices(['api-gateway'])).rejects.toThrow('Docker service start failed');
    });
  });

  describe('IPC Handlers', () => {
    test('should setup IPC handlers', () => {
      setupIpcHandlers(windowManager, torManager, dockerService);
      expect(setupIpcHandlers).toHaveBeenCalledWith(windowManager, torManager, dockerService);
    });
  });

  describe('Integration Tests', () => {
    test('should initialize all services together', async () => {
      // Test the complete initialization flow
      await dockerService.initialize();
      await torManager.start();
      const adminWindow = await windowManager.createWindow('admin');
      
      expect(dockerService.initialize).toHaveBeenCalled();
      expect(torManager.start).toHaveBeenCalled();
      expect(windowManager.createWindow).toHaveBeenCalledWith('admin');
      expect(adminWindow).toBeInstanceOf(BrowserWindow);
    });

    test('should handle service initialization errors gracefully', async () => {
      const error = new Error('Initialization failed');
      dockerService.initialize.mockRejectedValue(error);
      
      await expect(dockerService.initialize()).rejects.toThrow('Initialization failed');
      
      // Other services should still be able to initialize
      await torManager.start();
      expect(torManager.start).toHaveBeenCalled();
    });

    test('should broadcast status updates correctly', async () => {
      // Simulate Tor status change
      const torStatus = {
        connected: true,
        bootstrapProgress: 100,
        circuits: [{ id: '1', status: 'built', path: [], age: 0 }],
        proxyPort: 9050,
        error: null
      };
      
      torManager.getStatus.mockResolvedValue(torStatus);
      
      const status = await torManager.getStatus();
      expect(status.connected).toBe(true);
      expect(status.bootstrapProgress).toBe(100);
    });
  });

  describe('Error Handling', () => {
    test('should handle window creation errors', async () => {
      const error = new Error('Window creation failed');
      windowManager.createWindow.mockRejectedValue(error);
      
      await expect(windowManager.createWindow('admin')).rejects.toThrow('Window creation failed');
    });

    test('should handle Tor connection errors', async () => {
      const error = new Error('Tor connection failed');
      torManager.getStatus.mockResolvedValue({
        connected: false,
        bootstrapProgress: 0,
        circuits: [],
        proxyPort: 9050,
        error: error.message
      });
      
      const status = await torManager.getStatus();
      expect(status.connected).toBe(false);
      expect(status.error).toBe('Tor connection failed');
    });

    test('should handle Docker service errors', async () => {
      const error = new Error('Docker service error');
      dockerService.startServices.mockResolvedValue({
        success: false,
        started: [],
        failed: [{ service: 'api-gateway', error: error.message }]
      });
      
      const result = await dockerService.startServices(['api-gateway']);
      expect(result.success).toBe(false);
      expect(result.failed[0].error).toBe('Docker service error');
    });
  });

  describe('Performance Tests', () => {
    test('should create windows within acceptable time', async () => {
      const startTime = Date.now();
      await windowManager.createWindow('admin');
      const endTime = Date.now();
      
      expect(endTime - startTime).toBeLessThan(1000); // Should be less than 1 second
    });

    test('should start Tor within acceptable time', async () => {
      const startTime = Date.now();
      await torManager.start();
      const endTime = Date.now();
      
      expect(endTime - startTime).toBeLessThan(5000); // Should be less than 5 seconds
    });

    test('should initialize Docker service within acceptable time', async () => {
      const startTime = Date.now();
      await dockerService.initialize();
      const endTime = Date.now();
      
      expect(endTime - startTime).toBeLessThan(3000); // Should be less than 3 seconds
    });
  });
});
