/**
 * LUCID Electron Preload Script - Secure Context Bridge
 * Provides safe IPC communication between renderer and main processes
 * SPEC-1B Implementation with security hardening
 */

import { contextBridge, ipcRenderer } from 'electron';
import type {
  IPCMessage,
  IPCResponse,
} from '../shared/ipc-channels';
import { isValidChannel, IPCChannels } from '../shared/ipc-channels';

/**
 * Secure API object exposed to renderer process
 * All communication goes through validated IPC channels
 */
const api = {
  /**
   * Send message to main process with validation
   */
  send: (channel: string, ...args: any[]): void => {
    if (!isValidChannel(channel)) {
      console.error(`Invalid IPC channel: ${channel}`);
      return;
    }
    ipcRenderer.send(channel, ...args);
  },

  /**
   * Send message and wait for response
   */
  invoke: async (channel: string, ...args: any[]): Promise<any> => {
    if (!isValidChannel(channel)) {
      throw new Error(`Invalid IPC channel: ${channel}`);
    }
    try {
      return await ipcRenderer.invoke(channel, ...args);
    } catch (error) {
      console.error(`IPC invoke error on channel ${channel}:`, error);
      throw error;
    }
  },

  /**
   * Listen for messages from main process
   */
  on: (channel: string, listener: (event: any, ...args: any[]) => void): void => {
    if (!isValidChannel(channel)) {
      console.error(`Invalid IPC channel: ${channel}`);
      return;
    }

    // Create wrapper to prevent message flooding
    const validListener = (event: any, ...args: any[]) => {
      listener(event, ...args);
    };

    ipcRenderer.on(channel, validListener);
  },

  /**
   * Listen for one message from main process
   */
  once: (channel: string, listener: (event: any, ...args: any[]) => void): void => {
    if (!isValidChannel(channel)) {
      console.error(`Invalid IPC channel: ${channel}`);
      return;
    }
    ipcRenderer.once(channel, listener);
  },

  /**
   * Remove listener for channel
   */
  off: (channel: string, listener: (event: any, ...args: any[]) => void): void => {
    if (!isValidChannel(channel)) {
      console.error(`Invalid IPC channel: ${channel}`);
      return;
    }
    ipcRenderer.off(channel, listener);
  },

  /**
   * TOR management methods
   */
  tor: {
    start: (): Promise<any> => ipcRenderer.invoke(IPCChannels.TOR_START),
    stop: (): Promise<any> => ipcRenderer.invoke(IPCChannels.TOR_STOP),
    restart: (): Promise<any> => ipcRenderer.invoke(IPCChannels.TOR_RESTART),
    getStatus: (): Promise<any> => ipcRenderer.invoke(IPCChannels.TOR_GET_STATUS),
    getMetrics: (): Promise<any> => ipcRenderer.invoke(IPCChannels.TOR_GET_METRICS),
    testConnection: (url: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.TOR_TEST_CONNECTION, { url }),
    healthCheck: (): Promise<any> => ipcRenderer.invoke(IPCChannels.TOR_HEALTH_CHECK),
    onStatusUpdate: (listener: (status: any) => void): void => {
      ipcRenderer.on(IPCChannels.TOR_STATUS_UPDATE, (event, status) => listener(status));
    },
  },

  /**
   * Docker management methods
   */
  docker: {
    getStatus: (): Promise<any> => ipcRenderer.invoke(IPCChannels.DOCKER_GET_STATUS),
    connectSSH: (config: any): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.DOCKER_CONNECT_SSH, config),
    disconnect: (): Promise<any> => ipcRenderer.invoke(IPCChannels.DOCKER_DISCONNECT),
    getContainers: (): Promise<any> => ipcRenderer.invoke(IPCChannels.DOCKER_GET_CONTAINERS),
    getContainer: (id: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.DOCKER_GET_CONTAINER, id),
    startContainer: (id: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.DOCKER_START_CONTAINER, id),
    stopContainer: (id: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.DOCKER_STOP_CONTAINER, id),
    restartContainer: (id: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.DOCKER_RESTART_CONTAINER, id),
    removeContainer: (id: string, force?: boolean): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.DOCKER_REMOVE_CONTAINER, { id, force }),
    getLogs: (id: string, lines?: number): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.DOCKER_GET_LOGS, { id, lines }),
    getStats: (id: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.DOCKER_GET_STATS, id),
    getAllStats: (): Promise<any> => ipcRenderer.invoke(IPCChannels.DOCKER_GET_ALL_STATS),
    pullImage: (imageName: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.DOCKER_PULL_IMAGE, imageName),
    getImages: (): Promise<any> => ipcRenderer.invoke(IPCChannels.DOCKER_GET_IMAGES),
    onContainerUpdate: (listener: (data: any) => void): void => {
      ipcRenderer.on(IPCChannels.DOCKER_CONTAINER_UPDATE, (event, data) => listener(data));
    },
  },

  /**
   * API proxy methods
   */
  api: {
    request: (request: any): Promise<any> => ipcRenderer.invoke(IPCChannels.API_REQUEST, request),
    get: (url: string, config?: any): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.API_GET, { url, config }),
    post: (url: string, data?: any, config?: any): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.API_POST, { url, data, config }),
    put: (url: string, data?: any, config?: any): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.API_PUT, { url, data, config }),
    delete: (url: string, config?: any): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.API_DELETE, { url, config }),
  },

  /**
   * Authentication methods
   */
  auth: {
    login: (email: string, signature: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.AUTH_LOGIN, { email, signature }),
    logout: (): Promise<any> => ipcRenderer.invoke(IPCChannels.AUTH_LOGOUT),
    verifyToken: (token: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.AUTH_VERIFY_TOKEN, { token }),
    refreshToken: (): Promise<any> => ipcRenderer.invoke(IPCChannels.AUTH_REFRESH_TOKEN),
    onStatusChange: (listener: (status: any) => void): void => {
      ipcRenderer.on(IPCChannels.AUTH_STATUS_CHANGED, (event, status) => listener(status));
    },
    onTokenExpired: (listener: () => void): void => {
      ipcRenderer.on(IPCChannels.AUTH_TOKEN_EXPIRED, () => listener());
    },
  },

  /**
   * Configuration methods
   */
  config: {
    get: (key?: string): Promise<any> => ipcRenderer.invoke(IPCChannels.CONFIG_GET, key),
    set: (key: string, value: any): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.CONFIG_SET, { key, value }),
    reset: (key?: string): Promise<any> => ipcRenderer.invoke(IPCChannels.CONFIG_RESET, key),
    export: (): Promise<any> => ipcRenderer.invoke(IPCChannels.CONFIG_EXPORT),
    import: (data: any): Promise<any> => ipcRenderer.invoke(IPCChannels.CONFIG_IMPORT, data),
    onUpdate: (listener: (update: any) => void): void => {
      ipcRenderer.on(IPCChannels.CONFIG_UPDATED, (event, update) => listener(update));
    },
  },

  /**
   * System methods
   */
  system: {
    getInfo: (): Promise<any> => ipcRenderer.invoke(IPCChannels.SYSTEM_GET_INFO),
    getResources: (): Promise<any> => ipcRenderer.invoke(IPCChannels.SYSTEM_GET_RESOURCES),
    getNetworkInfo: (): Promise<any> => ipcRenderer.invoke(IPCChannels.SYSTEM_GET_NETWORK_INFO),
    showNotification: (title: string, body: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.SYSTEM_SHOW_NOTIFICATION, { title, body }),
    openExternal: (url: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.SYSTEM_OPEN_EXTERNAL, url),
  },

  /**
   * Logging methods
   */
  log: {
    info: (message: string, context?: any): void => 
      ipcRenderer.send(IPCChannels.LOG_INFO, { message, context }),
    warn: (message: string, context?: any): void => 
      ipcRenderer.send(IPCChannels.LOG_WARN, { message, context }),
    error: (message: string, context?: any): void => 
      ipcRenderer.send(IPCChannels.LOG_ERROR, { message, context }),
    debug: (message: string, context?: any): void => 
      ipcRenderer.send(IPCChannels.LOG_DEBUG, { message, context }),
  },

  /**
   * Update methods
   */
  update: {
    check: (): Promise<any> => ipcRenderer.invoke(IPCChannels.UPDATE_CHECK),
    download: (): Promise<any> => ipcRenderer.invoke(IPCChannels.UPDATE_DOWNLOAD),
    install: (): Promise<any> => ipcRenderer.invoke(IPCChannels.UPDATE_INSTALL),
    restart: (): Promise<any> => ipcRenderer.invoke(IPCChannels.UPDATE_RESTART),
    onAvailable: (listener: (update: any) => void): void => {
      ipcRenderer.on(IPCChannels.UPDATE_AVAILABLE, (event, update) => listener(update));
    },
    onProgress: (listener: (progress: any) => void): void => {
      ipcRenderer.on(IPCChannels.UPDATE_PROGRESS, (event, progress) => listener(progress));
    },
  },

  /**
   * Window management methods
   */
  window: {
    create: (type: string, options?: any): Promise<string> => 
      ipcRenderer.invoke(IPCChannels.WINDOW_CREATE, { type, options }),
    close: (id: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.WINDOW_CLOSE, id),
    minimize: (id: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.WINDOW_MINIMIZE, id),
    maximize: (id: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.WINDOW_MAXIMIZE, id),
    restore: (id: string): Promise<any> => 
      ipcRenderer.invoke(IPCChannels.WINDOW_RESTORE, id),
    getList: (): Promise<any> => ipcRenderer.invoke(IPCChannels.WINDOW_GET_LIST),
    getStatistics: (): Promise<any> => ipcRenderer.invoke(IPCChannels.WINDOW_GET_STATISTICS),
  },
};

/**
 * Expose API to renderer process via contextBridge
 * This ensures security by preventing direct access to ipcRenderer
 */
contextBridge.exposeInMainWorld('lucidAPI', api);

export type LucidAPI = typeof api;
