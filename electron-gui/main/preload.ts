// main/preload.ts - Preload script for secure IPC
// Based on the electron-multi-gui-development.plan.md specifications

import { contextBridge, ipcRenderer } from 'electron';
import {
  RENDERER_TO_MAIN_CHANNELS,
  MAIN_TO_RENDERER_CHANNELS,
  BIDIRECTIONAL_CHANNELS,
} from '../shared/ipc-channels';

// Expose secure APIs to renderer processes
contextBridge.exposeInMainWorld('electronAPI', {
  // Tor control APIs
  tor: {
    start: (config?: any) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_START, config),
    stop: (force?: boolean) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_STOP, { force }),
    restart: (config?: any) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_RESTART, config),
    getStatus: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_GET_STATUS),
    getMetrics: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_GET_METRICS),
    testConnection: (url: string, timeout?: number) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_TEST_CONNECTION, { url, timeout }),
    healthCheck: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_HEALTH_CHECK),
  },

  // Window control APIs
  window: {
    minimize: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.WINDOW_MINIMIZE),
    maximize: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.WINDOW_MAXIMIZE),
    restore: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.WINDOW_RESTORE),
    close: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.WINDOW_CLOSE),
    setSize: (width: number, height: number) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.WINDOW_SET_SIZE, { width, height }),
    setPosition: (x: number, y: number) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.WINDOW_SET_POSITION, { x, y }),
    center: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.WINDOW_CENTER),
    setAlwaysOnTop: (alwaysOnTop: boolean) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.WINDOW_SET_ALWAYS_ON_TOP, { alwaysOnTop }),
  },

  // Docker control APIs
  docker: {
    startServices: (services: string[], level?: string) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_START_SERVICES, { services, level }),
    stopServices: (services: string[]) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_STOP_SERVICES, { services }),
    restartServices: (services: string[]) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_RESTART_SERVICES, { services }),
    getServiceStatus: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_SERVICE_STATUS),
    getContainerLogs: (containerId: string, lines?: number, follow?: boolean) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_CONTAINER_LOGS, { containerId, lines, follow }),
    execCommand: (containerId: string, command: string[], workingDir?: string, env?: Record<string, string>) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_EXEC_COMMAND, { containerId, command, workingDir, env }),
  },

  // API request APIs
  api: {
    request: (method: string, url: string, data?: any, headers?: Record<string, string>) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_REQUEST, { method, url, data, headers }),
    get: (url: string, headers?: Record<string, string>) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_GET, { url, headers }),
    post: (url: string, data?: any, headers?: Record<string, string>) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_POST, { url, data, headers }),
    put: (url: string, data?: any, headers?: Record<string, string>) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_PUT, { url, data, headers }),
    delete: (url: string, headers?: Record<string, string>) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_DELETE, { url, headers }),
    upload: (url: string, file: File, headers?: Record<string, string>) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_UPLOAD, { url, file, headers }),
    download: (url: string, headers?: Record<string, string>) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_DOWNLOAD, { url, headers }),
  },

  // Authentication APIs
  auth: {
    login: (email: string, signature: string) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.AUTH_LOGIN, { email, signature }),
    logout: (token: string) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.AUTH_LOGOUT, { token }),
    verifyToken: (token: string) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.AUTH_VERIFY_TOKEN, { token }),
    refreshToken: (token: string) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.AUTH_REFRESH_TOKEN, { token }),
  },

  // Configuration APIs
  config: {
    get: (key: string) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.CONFIG_GET, { key }),
    set: (key: string, value: any) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.CONFIG_SET, { key, value }),
    reset: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.CONFIG_RESET),
    export: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.CONFIG_EXPORT),
    import: (config: any) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.CONFIG_IMPORT, { config }),
  },

  // File operation APIs
  file: {
    open: (filters?: any) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.FILE_OPEN, { filters }),
    save: (data: any, filename?: string) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.FILE_SAVE, { data, filename }),
    saveAs: (data: any, filename?: string) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.FILE_SAVE_AS, { data, filename }),
    select: (filters?: any) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.FILE_SELECT, { filters }),
    download: (url: string, filename?: string) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.FILE_DOWNLOAD, { url, filename }),
  },

  // System operation APIs
  system: {
    getInfo: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.SYSTEM_GET_INFO),
    getResources: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.SYSTEM_GET_RESOURCES),
    getNetworkInfo: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.SYSTEM_GET_NETWORK_INFO),
    showNotification: (title: string, body: string, icon?: string, actions?: any[]) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.SYSTEM_SHOW_NOTIFICATION, { title, body, icon, actions }),
    openExternal: (url: string) => 
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.SYSTEM_OPEN_EXTERNAL, { url }),
  },

  // Logging APIs
  log: {
    info: (message: string) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.LOG_INFO, { message }),
    warn: (message: string) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.LOG_WARN, { message }),
    error: (message: string) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.LOG_ERROR, { message }),
    debug: (message: string) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.LOG_DEBUG, { message }),
  },

  // Update APIs
  update: {
    check: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.UPDATE_CHECK),
    download: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.UPDATE_DOWNLOAD),
    install: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.UPDATE_INSTALL),
    restart: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.UPDATE_RESTART),
  },

  // Bidirectional communication APIs
  communication: {
    sendMessage: (targetWindow: string, channel: string, data: any) => 
      ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.WINDOW_SEND_MESSAGE, { targetWindow, channel, data }),
    broadcast: (channel: string, data: any) => 
      ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.WINDOW_BROADCAST, { channel, data }),
    syncData: (key: string, data: any, timestamp: number) => 
      ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.DATA_SYNC, { key, data, timestamp }),
    getData: (key: string) => ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.DATA_GET, { key }),
    setData: (key: string, data: any) => ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.DATA_SET, { key, data }),
    deleteData: (key: string) => ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.DATA_DELETE, { key }),
    subscribeEvent: (event: string, callback: string) => 
      ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.EVENT_SUBSCRIBE, { event, callback }),
    unsubscribeEvent: (subscriptionId: string) => 
      ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.EVENT_UNSUBSCRIBE, { subscriptionId }),
  },

  // Event listeners for main process events
  on: (channel: string, callback: (data: any) => void) => {
    const validChannels = Object.values(MAIN_TO_RENDERER_CHANNELS);
    if (validChannels.includes(channel as any)) {
      ipcRenderer.on(channel, (event, data) => callback(data));
    } else {
      console.warn(`Invalid channel: ${channel}`);
    }
  },

  off: (channel: string, callback: (data: any) => void) => {
    const validChannels = Object.values(MAIN_TO_RENDERER_CHANNELS);
    if (validChannels.includes(channel as any)) {
      ipcRenderer.off(channel, callback);
    } else {
      console.warn(`Invalid channel: ${channel}`);
    }
  },

  once: (channel: string, callback: (data: any) => void) => {
    const validChannels = Object.values(MAIN_TO_RENDERER_CHANNELS);
    if (validChannels.includes(channel as any)) {
      ipcRenderer.once(channel, (event, data) => callback(data));
    } else {
      console.warn(`Invalid channel: ${channel}`);
    }
  },

  // Remove all listeners for a channel
  removeAllListeners: (channel: string) => {
    const validChannels = Object.values(MAIN_TO_RENDERER_CHANNELS);
    if (validChannels.includes(channel as any)) {
      ipcRenderer.removeAllListeners(channel);
    } else {
      console.warn(`Invalid channel: ${channel}`);
    }
  },
});

// Expose utility functions
contextBridge.exposeInMainWorld('utils', {
  // Platform detection
  platform: process.platform,
  isWindows: process.platform === 'win32',
  isMac: process.platform === 'darwin',
  isLinux: process.platform === 'linux',

  // Environment detection
  isDevelopment: process.env.NODE_ENV === 'development',
  isProduction: process.env.NODE_ENV === 'production',

  // Version info
  version: process.versions.electron,
  nodeVersion: process.versions.node,
  chromeVersion: process.versions.chrome,

  // Utility functions
  generateId: () => Math.random().toString(36).substring(2) + Date.now().toString(36),
  generateUUID: () => 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  }),

  // Date utilities
  formatDate: (date: Date | string) => {
    const d = new Date(date);
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  },

  formatRelativeTime: (date: Date | string) => {
    const now = new Date();
    const target = new Date(date);
    const diffInSeconds = Math.floor((now.getTime() - target.getTime()) / 1000);

    if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
  },

  // File size utilities
  formatBytes: (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },

  // String utilities
  truncateString: (str: string, maxLength: number) => {
    if (str.length <= maxLength) return str;
    return str.substring(0, maxLength - 3) + '...';
  },

  capitalizeFirst: (str: string) => {
    return str.charAt(0).toUpperCase() + str.slice(1);
  },

  // Validation utilities
  isValidEmail: (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  isValidTronAddress: (address: string) => {
    return address.length === 34 && address.startsWith('T');
  },

  // Local storage utilities
  setLocalStorage: (key: string, value: any) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error('Failed to save to localStorage:', error);
    }
  },

  getLocalStorage: (key: string, defaultValue: any) => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.error('Failed to read from localStorage:', error);
      return defaultValue;
    }
  },

  removeLocalStorage: (key: string) => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Failed to remove from localStorage:', error);
    }
  },
});

// Expose constants
contextBridge.exposeInMainWorld('constants', {
  // API endpoints
  API_ENDPOINTS: {
    GATEWAY: 'http://localhost:8080',
    BLOCKCHAIN: 'http://localhost:8084',
    AUTH: 'http://localhost:8089',
    SESSIONS: 'http://localhost:8087',
    NODES: 'http://localhost:8095',
    ADMIN: 'http://localhost:8083',
    TRON_PAYMENT: 'http://localhost:8085',
  },

  // Service ports
  SERVICE_PORTS: {
    API_GATEWAY: 8080,
    API_GATEWAY_HTTPS: 8081,
    ADMIN_INTERFACE: 8083,
    BLOCKCHAIN_CORE: 8084,
    TRON_PAYMENT: 8085,
    BLOCK_MANAGER: 8086,
    SESSION_API: 8087,
    STORAGE_DATABASE: 8088,
    AUTHENTICATION: 8089,
    RDP_SERVER_MANAGER: 8090,
    XRDP_INTEGRATION: 8091,
    SESSION_CONTROLLER: 8092,
    RESOURCE_MONITOR: 8093,
    NODE_MANAGEMENT: 8095,
  },

  // Tor configuration
  TOR_CONFIG: {
    SOCKS_PORT: 9050,
    CONTROL_PORT: 9051,
    DATA_DIR: 'tor-data',
    CONFIG_FILE: 'torrc',
    BOOTSTRAP_TIMEOUT: 60000,
    CIRCUIT_BUILD_TIMEOUT: 60000,
  },

  // Window configurations
  WINDOW_CONFIGS: {
    user: {
      name: 'user',
      title: 'Lucid User Interface',
      width: 1200,
      height: 800,
      level: 'user',
    },
    developer: {
      name: 'developer',
      title: 'Lucid Developer Console',
      width: 1400,
      height: 900,
      level: 'developer',
    },
    node: {
      name: 'node',
      title: 'Lucid Node Operator',
      width: 1200,
      height: 800,
      level: 'node',
    },
    admin: {
      name: 'admin',
      title: 'Lucid System Administration',
      width: 1600,
      height: 1000,
      level: 'admin',
    },
  },

  // Error codes
  LUCID_ERROR_CODES: {
    VALIDATION_ERROR: 'LUCID_ERR_1001',
    INVALID_USER_ID: 'LUCID_ERR_1002',
    INVALID_SESSION_ID: 'LUCID_ERR_1003',
    INVALID_CHUNK_ID: 'LUCID_ERR_1004',
    AUTHENTICATION_FAILED: 'LUCID_ERR_2001',
    AUTHORIZATION_DENIED: 'LUCID_ERR_2002',
    TOKEN_EXPIRED: 'LUCID_ERR_2003',
    INVALID_TOKEN: 'LUCID_ERR_2004',
    RATE_LIMIT_EXCEEDED: 'LUCID_ERR_3001',
    TOO_MANY_REQUESTS: 'LUCID_ERR_3002',
    SESSION_NOT_FOUND: 'LUCID_ERR_4001',
    SESSION_ALREADY_ANCHORED: 'LUCID_ERR_4002',
    NODE_NOT_REGISTERED: 'LUCID_ERR_4003',
    POOL_FULL: 'LUCID_ERR_4004',
    INTERNAL_SERVER_ERROR: 'LUCID_ERR_5001',
    DATABASE_ERROR: 'LUCID_ERR_5002',
    BLOCKCHAIN_ERROR: 'LUCID_ERR_5003',
    TOR_CONNECTION_ERROR: 'LUCID_ERR_5004',
  },

  // Timeouts
  TIMEOUTS: {
    API_REQUEST: 30000,
    TOR_BOOTSTRAP: 60000,
    DOCKER_STARTUP: 120000,
    FILE_UPLOAD: 300000,
    BLOCKCHAIN_CONFIRMATION: 60000,
  },
});

// Security: Prevent the renderer from accessing Node.js APIs
delete (window as any).require;
delete (window as any).exports;
delete (window as any).module;
