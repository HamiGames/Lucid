// IPC channel definitions for Lucid Electron GUI
// Based on the electron-multi-gui-development.plan.md specifications

// Main process to renderer channels
export const MAIN_TO_RENDERER_CHANNELS = {
  // Tor status updates
  TOR_STATUS_UPDATE: 'tor-status-update',
  TOR_CONNECTION_CHANGED: 'tor-connection-changed',
  TOR_BOOTSTRAP_PROGRESS: 'tor-bootstrap-progress',
  TOR_CIRCUIT_UPDATE: 'tor-circuit-update',
  
  // Window management
  WINDOW_READY: 'window-ready',
  WINDOW_CLOSED: 'window-closed',
  WINDOW_FOCUSED: 'window-focused',
  WINDOW_BLURRED: 'window-blurred',
  
  // Docker service updates
  DOCKER_SERVICE_STATUS: 'docker-service-status',
  DOCKER_CONTAINER_UPDATE: 'docker-container-update',
  DOCKER_HEALTH_CHECK: 'docker-health-check',
  
  // System notifications
  SYSTEM_NOTIFICATION: 'system-notification',
  ERROR_OCCURRED: 'error-occurred',
  WARNING_OCCURRED: 'warning-occurred',
  
  // API responses
  API_RESPONSE: 'api-response',
  API_ERROR: 'api-error',
  
  // Authentication
  AUTH_STATUS_CHANGED: 'auth-status-changed',
  AUTH_TOKEN_EXPIRED: 'auth-token-expired',
  
  // Configuration updates
  CONFIG_UPDATED: 'config-updated',
  SETTINGS_CHANGED: 'settings-changed',
} as const;

// Renderer to main process channels
export const RENDERER_TO_MAIN_CHANNELS = {
  // Tor control
  TOR_START: 'tor-start',
  TOR_STOP: 'tor-stop',
  TOR_RESTART: 'tor-restart',
  TOR_GET_STATUS: 'tor-get-status',
  TOR_GET_METRICS: 'tor-get-metrics',
  TOR_TEST_CONNECTION: 'tor-test-connection',
  TOR_HEALTH_CHECK: 'tor-health-check',
  
  // Window control
  WINDOW_MINIMIZE: 'window-minimize',
  WINDOW_MAXIMIZE: 'window-maximize',
  WINDOW_RESTORE: 'window-restore',
  WINDOW_CLOSE: 'window-close',
  WINDOW_SET_SIZE: 'window-set-size',
  WINDOW_SET_POSITION: 'window-set-position',
  WINDOW_CENTER: 'window-center',
  WINDOW_SET_ALWAYS_ON_TOP: 'window-set-always-on-top',
  
  // Docker control
  DOCKER_START_SERVICES: 'docker-start-services',
  DOCKER_STOP_SERVICES: 'docker-stop-services',
  DOCKER_RESTART_SERVICES: 'docker-restart-services',
  DOCKER_GET_SERVICE_STATUS: 'docker-get-service-status',
  DOCKER_GET_CONTAINER_LOGS: 'docker-get-container-logs',
  DOCKER_EXEC_COMMAND: 'docker-exec-command',
  
  // API requests
  API_REQUEST: 'api-request',
  API_GET: 'api-get',
  API_POST: 'api-post',
  API_PUT: 'api-put',
  API_DELETE: 'api-delete',
  API_UPLOAD: 'api-upload',
  API_DOWNLOAD: 'api-download',
  
  // Authentication
  AUTH_LOGIN: 'auth-login',
  AUTH_LOGOUT: 'auth-logout',
  AUTH_VERIFY_TOKEN: 'auth-verify-token',
  AUTH_REFRESH_TOKEN: 'auth-refresh-token',
  
  // Configuration
  CONFIG_GET: 'config-get',
  CONFIG_SET: 'config-set',
  CONFIG_RESET: 'config-reset',
  CONFIG_EXPORT: 'config-export',
  CONFIG_IMPORT: 'config-import',
  
  // File operations
  FILE_OPEN: 'file-open',
  FILE_SAVE: 'file-save',
  FILE_SAVE_AS: 'file-save-as',
  FILE_SELECT: 'file-select',
  FILE_DOWNLOAD: 'file-download',
  
  // System operations
  SYSTEM_GET_INFO: 'system-get-info',
  SYSTEM_GET_RESOURCES: 'system-get-resources',
  SYSTEM_GET_NETWORK_INFO: 'system-get-network-info',
  SYSTEM_SHOW_NOTIFICATION: 'system-show-notification',
  SYSTEM_OPEN_EXTERNAL: 'system-open-external',
  
  // Logging
  LOG_INFO: 'log-info',
  LOG_WARN: 'log-warn',
  LOG_ERROR: 'log-error',
  LOG_DEBUG: 'log-debug',
  
  // Updates
  UPDATE_CHECK: 'update-check',
  UPDATE_DOWNLOAD: 'update-download',
  UPDATE_INSTALL: 'update-install',
  UPDATE_RESTART: 'update-restart',
} as const;

// Bidirectional channels
export const BIDIRECTIONAL_CHANNELS = {
  // Window communication
  WINDOW_SEND_MESSAGE: 'window-send-message',
  WINDOW_BROADCAST: 'window-broadcast',
  
  // Data synchronization
  DATA_SYNC: 'data-sync',
  DATA_GET: 'data-get',
  DATA_SET: 'data-set',
  DATA_DELETE: 'data-delete',
  
  // Event forwarding
  EVENT_FORWARD: 'event-forward',
  EVENT_SUBSCRIBE: 'event-subscribe',
  EVENT_UNSUBSCRIBE: 'event-unsubscribe',
} as const;

// Channel types for type safety
export type MainToRendererChannel = typeof MAIN_TO_RENDERER_CHANNELS[keyof typeof MAIN_TO_RENDERER_CHANNELS];
export type RendererToMainChannel = typeof RENDERER_TO_MAIN_CHANNELS[keyof typeof RENDERER_TO_MAIN_CHANNELS];
export type BidirectionalChannel = typeof BIDIRECTIONAL_CHANNELS[keyof typeof BIDIRECTIONAL_CHANNELS];
export type IPCChannel = MainToRendererChannel | RendererToMainChannel | BidirectionalChannel;

// IPC message types
export interface IPCMessage<T = any> {
  channel: IPCChannel;
  data: T;
  id?: string;
  timestamp?: number;
  source?: string;
}

export interface IPCResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  id?: string;
  timestamp?: number;
}

export interface IPCRequest<T = any> {
  channel: IPCChannel;
  data: T;
  id: string;
  timeout?: number;
}

// Specific message types for different channels
export interface TorStatusMessage {
  status: 'connecting' | 'connected' | 'disconnected';
  progress?: number;
  error?: string;
  circuits?: number;
}

export interface TorConnectionMessage {
  connected: boolean;
  timestamp: string;
  error?: string;
}

export interface TorBootstrapMessage {
  progress: number;
  summary: string;
  warning?: string;
}

export interface TorCircuitMessage {
  circuitId: string;
  status: 'building' | 'built' | 'extended' | 'closed';
  path: string[];
  age: number;
}

export interface DockerServiceMessage {
  service: string;
  status: 'starting' | 'running' | 'stopped' | 'error';
  containerId?: string;
  error?: string;
}

export interface DockerContainerMessage {
  containerId: string;
  status: 'created' | 'running' | 'paused' | 'restarting' | 'removing' | 'exited' | 'dead';
  name: string;
  image: string;
  ports: string[];
  health?: 'healthy' | 'unhealthy' | 'starting';
}

export interface DockerHealthMessage {
  service: string;
  healthy: boolean;
  lastCheck: string;
  responseTime: number;
  error?: string;
}

export interface SystemNotificationMessage {
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  duration?: number;
  actions?: Array<{
    label: string;
    action: string;
  }>;
}

export interface ErrorMessage {
  code: string;
  message: string;
  details?: any;
  stack?: string;
  timestamp: string;
}

export interface WarningMessage {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}

export interface APIResponseMessage<T = any> {
  requestId: string;
  data: T;
  status: number;
  headers: Record<string, string>;
}

export interface APIErrorMessage {
  requestId: string;
  error: string;
  status: number;
  details?: any;
}

export interface AuthStatusMessage {
  authenticated: boolean;
  user?: {
    id: string;
    email: string;
    role: string;
  };
  token?: string;
  expiresAt?: string;
}

export interface AuthTokenExpiredMessage {
  token: string;
  expiredAt: string;
  refreshToken?: string;
}

export interface ConfigUpdatedMessage {
  key: string;
  value: any;
  oldValue?: any;
  timestamp: string;
}

export interface SettingsChangedMessage {
  settings: Record<string, any>;
  timestamp: string;
}

// Request/Response types for specific operations
export interface TorStartRequest {
  config?: {
    socksPort?: number;
    controlPort?: number;
    dataDir?: string;
  };
}

export interface TorStartResponse {
  success: boolean;
  pid?: number;
  error?: string;
}

export interface TorStopRequest {
  force?: boolean;
}

export interface TorStopResponse {
  success: boolean;
  error?: string;
}

export interface TorRestartRequest {
  config?: {
    socksPort?: number;
    controlPort?: number;
    dataDir?: string;
  };
}

export interface TorRestartResponse {
  success: boolean;
  pid?: number;
  error?: string;
}

export interface TorGetStatusResponse {
  connected: boolean;
  bootstrapProgress: number;
  circuits: Array<{
    id: string;
    status: string;
    path: string[];
    age: number;
  }>;
  proxyPort: number;
  error?: string;
}

export interface TorGetMetricsResponse {
  bytesRead: number;
  bytesWritten: number;
  circuitsBuilt: number;
  circuitsFailed: number;
  bootstrapTime: number;
  uptime: number;
}

export interface TorTestConnectionRequest {
  url: string;
  timeout?: number;
}

export interface TorTestConnectionResponse {
  success: boolean;
  responseTime: number;
  error?: string;
}

export interface TorHealthCheckResponse {
  healthy: boolean;
  lastCheck: string;
  responseTime: number;
  tests: {
    socksProxy: boolean;
    controlPort: boolean;
    bootstrap: boolean;
    circuitBuild: boolean;
  };
  error?: string;
}

export interface DockerStartServicesRequest {
  services: string[];
  level?: 'admin' | 'developer' | 'user' | 'node';
}

export interface DockerStartServicesResponse {
  success: boolean;
  started: string[];
  failed: Array<{
    service: string;
    error: string;
  }>;
}

export interface DockerStopServicesRequest {
  services: string[];
}

export interface DockerStopServicesResponse {
  success: boolean;
  stopped: string[];
  failed: Array<{
    service: string;
    error: string;
  }>;
}

export interface DockerGetServiceStatusResponse {
  services: Array<{
    name: string;
    status: string;
    containerId?: string;
    image: string;
    ports: string[];
    health?: string;
    uptime: number;
  }>;
}

export interface DockerGetContainerLogsRequest {
  containerId: string;
  lines?: number;
  follow?: boolean;
}

export interface DockerGetContainerLogsResponse {
  logs: string[];
  error?: string;
}

export interface DockerExecCommandRequest {
  containerId: string;
  command: string[];
  workingDir?: string;
  env?: Record<string, string>;
}

export interface DockerExecCommandResponse {
  success: boolean;
  output: string;
  error?: string;
  exitCode?: number;
}

export interface APIRequestMessage<T = any> {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  url: string;
  data?: T;
  headers?: Record<string, string>;
  timeout?: number;
}

export interface APIResponseMessage<T = any> {
  requestId: string;
  data: T;
  status: number;
  headers: Record<string, string>;
}

export interface AuthLoginRequest {
  email: string;
  signature: string;
}

export interface AuthLoginResponse {
  success: boolean;
  token?: string;
  user?: {
    id: string;
    email: string;
    role: string;
  };
  error?: string;
}

export interface AuthLogoutRequest {
  token: string;
}

export interface AuthLogoutResponse {
  success: boolean;
  error?: string;
}

export interface AuthVerifyTokenRequest {
  token: string;
}

export interface AuthVerifyTokenResponse {
  valid: boolean;
  user?: {
    id: string;
    email: string;
    role: string;
  };
  expiresAt?: string;
  error?: string;
}

export interface ConfigGetRequest {
  key: string;
}

export interface ConfigGetResponse<T = any> {
  value: T;
  exists: boolean;
}

export interface ConfigSetRequest<T = any> {
  key: string;
  value: T;
}

export interface ConfigSetResponse {
  success: boolean;
  error?: string;
}

export interface SystemGetInfoResponse {
  platform: string;
  arch: string;
  version: string;
  uptime: number;
  memory: {
    total: number;
    free: number;
    used: number;
  };
  cpu: {
    usage: number;
    cores: number;
  };
}

export interface SystemGetResourcesResponse {
  memory: {
    total: number;
    free: number;
    used: number;
    percentage: number;
  };
  cpu: {
    usage: number;
    cores: number;
    loadAverage: number[];
  };
  disk: {
    total: number;
    free: number;
    used: number;
    percentage: number;
  };
  network: {
    interfaces: Array<{
      name: string;
      address: string;
      bytesReceived: number;
      bytesSent: number;
    }>;
  };
}

export interface SystemGetNetworkInfoResponse {
  interfaces: Array<{
    name: string;
    address: string;
    family: string;
    internal: boolean;
    mac: string;
  }>;
  defaultGateway?: string;
  dns: string[];
}

export interface SystemShowNotificationRequest {
  title: string;
  body: string;
  icon?: string;
  actions?: Array<{
    label: string;
    action: string;
  }>;
}

export interface SystemShowNotificationResponse {
  success: boolean;
  error?: string;
}

export interface SystemOpenExternalRequest {
  url: string;
}

export interface SystemOpenExternalResponse {
  success: boolean;
  error?: string;
}

// Event subscription types
export interface EventSubscriptionRequest {
  event: string;
  callback: string;
}

export interface EventSubscriptionResponse {
  success: boolean;
  subscriptionId: string;
  error?: string;
}

export interface EventUnsubscriptionRequest {
  subscriptionId: string;
}

export interface EventUnsubscriptionResponse {
  success: boolean;
  error?: string;
}

// Data synchronization types
export interface DataSyncRequest<T = any> {
  key: string;
  data: T;
  timestamp: number;
}

export interface DataSyncResponse {
  success: boolean;
  conflict?: boolean;
  error?: string;
}

export interface DataGetRequest {
  key: string;
}

export interface DataGetResponse<T = any> {
  data: T;
  exists: boolean;
  timestamp: number;
}

export interface DataSetRequest<T = any> {
  key: string;
  data: T;
}

export interface DataSetResponse {
  success: boolean;
  error?: string;
}

export interface DataDeleteRequest {
  key: string;
}

export interface DataDeleteResponse {
  success: boolean;
  error?: string;
}
