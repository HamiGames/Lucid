/// <reference types="electron" />
/// <reference types="node" />

import { contextBridge, ipcRenderer, IpcRendererEvent } from 'electron';
import {
  RENDERER_TO_MAIN_CHANNELS,
  MAIN_TO_RENDERER_CHANNELS,
  BIDIRECTIONAL_CHANNELS,
} from '../shared/ipc-channels';
import {
  API_ENDPOINTS,
  SERVICE_PORTS,
  TOR_CONFIG,
  WINDOW_CONFIGS,
  LUCID_ERROR_CODES,
  TIMEOUTS,
  DOCKER_CONFIG,
  DOCKER_COMPOSE_FILES,
  SERVICE_NAMES,
  PATHS,
  CHUNK_CONFIG,
  HARDWARE_WALLET_TYPES,
  USER_ROLES,
  SESSION_STATUSES,
  NODE_STATUSES,
  PAYOUT_STATUSES,
} from '../shared/constants';

type Listener = (data: unknown) => void;
type WrappedListener = (event: IpcRendererEvent, data: unknown) => void;

const validMainChannels = new Set<string>(Object.values(MAIN_TO_RENDERER_CHANNELS));
const listenerRegistry = new Map<string, Map<Listener, WrappedListener>>();

const validateMainChannel = (channel: string): boolean => {
  if (!validMainChannels.has(channel)) {
    console.warn(`Invalid main channel: ${channel}`);
    return false;
  }
  return true;
};

const registerListener = (channel: string, listener: Listener): void => {
  if (!validateMainChannel(channel)) return;

  const wrapped: WrappedListener = (_event, data) => listener(data);
  const channelMap = listenerRegistry.get(channel) ?? new Map<Listener, WrappedListener>();
  channelMap.set(listener, wrapped);
  listenerRegistry.set(channel, channelMap);

  ipcRenderer.on(channel, wrapped);
};

const unregisterListener = (channel: string, listener: Listener): void => {
  if (!validateMainChannel(channel)) return;

  const channelMap = listenerRegistry.get(channel);
  const wrapped = channelMap?.get(listener);
  if (!wrapped) return;

  ipcRenderer.off(channel, wrapped);
  channelMap?.delete(listener);

  if (channelMap && channelMap.size === 0) {
    listenerRegistry.delete(channel);
  }
};

const removeAllRegisteredListeners = (channel: string): void => {
  if (!validateMainChannel(channel)) return;

  const channelMap = listenerRegistry.get(channel);
  if (!channelMap) return;

  for (const wrapped of channelMap.values()) {
    ipcRenderer.off(channel, wrapped);
  }
  listenerRegistry.delete(channel);
};

contextBridge.exposeInMainWorld('electronAPI', {
  tor: {
    start: (config?: Record<string, unknown>) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_START, config),
    stop: (force?: boolean) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_STOP, { force }),
    restart: (config?: Record<string, unknown>) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_RESTART, config),
    getStatus: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_GET_STATUS),
    getMetrics: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_GET_METRICS),
    testConnection: (url: string, timeout?: number) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_TEST_CONNECTION, { url, timeout }),
    healthCheck: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.TOR_HEALTH_CHECK),
    getDefaults: () => ({
      socksPort: TOR_CONFIG.SOCKS_PORT,
      controlPort: TOR_CONFIG.CONTROL_PORT,
      dataDir: TOR_CONFIG.DATA_DIR,
      configFile: TOR_CONFIG.CONFIG_FILE,
      bootstrapTimeout: TOR_CONFIG.BOOTSTRAP_TIMEOUT,
      circuitBuildTimeout: TOR_CONFIG.CIRCUIT_BUILD_TIMEOUT,
      dockerExpose: '9050,9051,8888',
    }),
  },

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

  docker: {
    startServices: (services: string[], level?: keyof typeof DOCKER_COMPOSE_FILES) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_START_SERVICES, { services, level }),
    stopServices: (services: string[]) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_STOP_SERVICES, { services }),
    restartServices: (services: string[], level?: keyof typeof DOCKER_COMPOSE_FILES) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_RESTART_SERVICES, { services, level }),
    getServiceStatus: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_SERVICE_STATUS),
    getContainerLogs: (containerId: string, lines?: number, follow?: boolean) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_GET_CONTAINER_LOGS, {
        containerId,
        lines,
        follow,
      }),
    execCommand: (
      containerId: string,
      command: string[],
      workingDir?: string,
      env?: Record<string, string>,
    ) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.DOCKER_EXEC_COMMAND, {
        containerId,
        command,
        workingDir,
        env,
      }),
    getConfig: () => ({
      host: DOCKER_CONFIG.PI_HOST,
      sshUser: DOCKER_CONFIG.SSH_USER,
      sshPort: DOCKER_CONFIG.SSH_PORT,
      deployDir: DOCKER_CONFIG.DEPLOY_DIR,
      composeFiles: DOCKER_COMPOSE_FILES,
      serviceNames: SERVICE_NAMES,
    }),
  },

  api: {
    request: (method: string, url: string, data?: unknown, headers?: Record<string, string>) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_REQUEST, { method, url, data, headers }),
    get: (url: string, headers?: Record<string, string>) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_GET, { url, headers }),
    post: (url: string, data?: unknown, headers?: Record<string, string>) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_POST, { url, data, headers }),
    put: (url: string, data?: unknown, headers?: Record<string, string>) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_PUT, { url, data, headers }),
    delete: (url: string, headers?: Record<string, string>) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_DELETE, { url, headers }),
    upload: (url: string, file: File, headers?: Record<string, string>) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_UPLOAD, { url, file, headers }),
    download: (url: string, headers?: Record<string, string>) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.API_DOWNLOAD, { url, headers }),
  },

  auth: {
    login: (email: string, signature: string) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.AUTH_LOGIN, { email, signature }),
    logout: (token: string) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.AUTH_LOGOUT, { token }),
    verifyToken: (token: string) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.AUTH_VERIFY_TOKEN, { token }),
    refreshToken: (token: string) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.AUTH_REFRESH_TOKEN, { token }),
  },

  config: {
    get: (key: string) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.CONFIG_GET, { key }),
    set: (key: string, value: unknown) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.CONFIG_SET, { key, value }),
    reset: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.CONFIG_RESET),
    export: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.CONFIG_EXPORT),
    import: (config: unknown) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.CONFIG_IMPORT, { config }),
  },

  file: {
    open: (filters?: unknown) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.FILE_OPEN, { filters }),
    save: (data: unknown, filename?: string) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.FILE_SAVE, { data, filename }),
    saveAs: (data: unknown, filename?: string) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.FILE_SAVE_AS, { data, filename }),
    select: (filters?: unknown) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.FILE_SELECT, { filters }),
    download: (url: string, filename?: string) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.FILE_DOWNLOAD, { url, filename }),
  },

  system: {
    getInfo: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.SYSTEM_GET_INFO),
    getResources: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.SYSTEM_GET_RESOURCES),
    getNetworkInfo: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.SYSTEM_GET_NETWORK_INFO),
    showNotification: (title: string, body: string, icon?: string, actions?: unknown[]) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.SYSTEM_SHOW_NOTIFICATION, {
        title,
        body,
        icon,
        actions,
      }),
    openExternal: (url: string) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.SYSTEM_OPEN_EXTERNAL, { url }),
  },

  log: {
    info: (message: string) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.LOG_INFO, { message }),
    warn: (message: string) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.LOG_WARN, { message }),
    error: (message: string) => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.LOG_ERROR, { message }),
    debug: (message: string) =>
      ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.LOG_DEBUG, { message }),
  },

  update: {
    check: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.UPDATE_CHECK),
    download: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.UPDATE_DOWNLOAD),
    install: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.UPDATE_INSTALL),
    restart: () => ipcRenderer.invoke(RENDERER_TO_MAIN_CHANNELS.UPDATE_RESTART),
  },

  communication: {
    sendMessage: (targetWindow: string, channel: string, data: unknown) =>
      ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.WINDOW_SEND_MESSAGE, {
        targetWindow,
        channel,
        data,
      }),
    broadcast: (channel: string, data: unknown) =>
      ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.WINDOW_BROADCAST, { channel, data }),
    syncData: (key: string, data: unknown, timestamp: number) =>
      ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.DATA_SYNC, { key, data, timestamp }),
    getData: (key: string) => ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.DATA_GET, { key }),
    setData: (key: string, data: unknown) =>
      ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.DATA_SET, { key, data }),
    deleteData: (key: string) => ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.DATA_DELETE, { key }),
    subscribeEvent: (event: string, callback: string) =>
      ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.EVENT_SUBSCRIBE, { event, callback }),
    unsubscribeEvent: (subscriptionId: string) =>
      ipcRenderer.invoke(BIDIRECTIONAL_CHANNELS.EVENT_UNSUBSCRIBE, { subscriptionId }),
  },

  events: {
    on: (channel: string, callback: Listener) => registerListener(channel, callback),
    off: (channel: string, callback: Listener) => unregisterListener(channel, callback),
    once: (channel: string, callback: Listener) => {
      if (!validateMainChannel(channel)) return;
      const wrapped: WrappedListener = (_event, data) => callback(data);
      ipcRenderer.once(channel, wrapped);
    },
    removeAll: (channel: string) => removeAllRegisteredListeners(channel),
  },
});

contextBridge.exposeInMainWorld('utils', {
  platform: process.platform,
  isWindows: process.platform === 'win32',
  isMac: process.platform === 'darwin',
  isLinux: process.platform === 'linux',
  isDevelopment: process.env.NODE_ENV === 'development',
  isProduction: process.env.NODE_ENV === 'production',
  electronVersion: process.versions.electron,
  nodeVersion: process.versions.node,
  chromeVersion: process.versions.chrome,
  generateId: () => Math.random().toString(36).substring(2) + Date.now().toString(36),
  generateUUID: () =>
    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (character) => {
      const random = (Math.random() * 16) | 0;
      const value = character === 'x' ? random : (random & 0x3) | 0x8;
      return value.toString(16);
    }),
  formatDate: (date: Date | string) => new Date(date).toLocaleString('en-US', { hour12: false }),
  formatRelativeTime: (date: Date | string) => {
    const now = Date.now();
    const then = new Date(date).getTime();
    const diffSeconds = Math.floor((now - then) / 1000);

    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
    if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
    return `${Math.floor(diffSeconds / 86400)}d ago`;
  },
  formatBytes: (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  },
  truncate: (value: string, maxLength: number) =>
    value.length <= maxLength ? value : `${value.slice(0, maxLength - 3)}...`,
  capitalize: (value: string) => value.charAt(0).toUpperCase() + value.slice(1),
});

contextBridge.exposeInMainWorld('constants', {
  API_ENDPOINTS,
  SERVICE_PORTS,
  TOR_CONFIG,
  WINDOW_CONFIGS,
  LUCID_ERROR_CODES,
  TIMEOUTS,
  DOCKER_CONFIG,
  DOCKER_COMPOSE_FILES,
  SERVICE_NAMES,
  PATHS,
  CHUNK_CONFIG,
  HARDWARE_WALLET_TYPES,
  USER_ROLES,
  SESSION_STATUSES,
  NODE_STATUSES,
  PAYOUT_STATUSES,
});

delete (window as any).require;
delete (window as any).exports;
delete (window as any).module;