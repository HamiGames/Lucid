// File: electron-gui/shared/ipc-channels.ts

/**
 * Lucid Electron GUI IPC channel catalogue and payload contracts.
 * Channel naming follows the service layout documented in `plan/constants`.
 */

type ValueOf<T> = T[keyof T];

export const RENDERER_TO_MAIN_CHANNELS = {
  TOR_START: 'tor:start',
  TOR_STOP: 'tor:stop',
  TOR_RESTART: 'tor:restart',
  TOR_GET_STATUS: 'tor:get-status',
  TOR_GET_METRICS: 'tor:get-metrics',
  TOR_TEST_CONNECTION: 'tor:test-connection',
  TOR_HEALTH_CHECK: 'tor:health-check',

  WINDOW_MINIMIZE: 'window:minimize',
  WINDOW_MAXIMIZE: 'window:maximize',
  WINDOW_RESTORE: 'window:restore',
  WINDOW_CLOSE: 'window:close',
  WINDOW_SET_SIZE: 'window:set-size',
  WINDOW_SET_POSITION: 'window:set-position',
  WINDOW_CENTER: 'window:center',
  WINDOW_SET_ALWAYS_ON_TOP: 'window:set-always-on-top',

  DOCKER_START_SERVICES: 'docker:start-services',
  DOCKER_STOP_SERVICES: 'docker:stop-services',
  DOCKER_RESTART_SERVICES: 'docker:restart-services',
  DOCKER_GET_SERVICE_STATUS: 'docker:get-service-status',
  DOCKER_GET_CONTAINER_LOGS: 'docker:get-container-logs',
  DOCKER_EXEC_COMMAND: 'docker:exec-command',

  API_REQUEST: 'api:request',
  API_GET: 'api:get',
  API_POST: 'api:post',
  API_PUT: 'api:put',
  API_DELETE: 'api:delete',
  API_UPLOAD: 'api:upload',
  API_DOWNLOAD: 'api:download',

  AUTH_LOGIN: 'auth:login',
  AUTH_LOGOUT: 'auth:logout',
  AUTH_VERIFY_TOKEN: 'auth:verify-token',
  AUTH_REFRESH_TOKEN: 'auth:refresh-token',

  CONFIG_GET: 'config:get',
  CONFIG_SET: 'config:set',
  CONFIG_RESET: 'config:reset',
  CONFIG_EXPORT: 'config:export',
  CONFIG_IMPORT: 'config:import',

  FILE_OPEN: 'file:open',
  FILE_SAVE: 'file:save',
  FILE_SAVE_AS: 'file:save-as',
  FILE_SELECT: 'file:select',
  FILE_DOWNLOAD: 'file:download',

  SYSTEM_GET_INFO: 'system:get-info',
  SYSTEM_GET_RESOURCES: 'system:get-resources',
  SYSTEM_GET_NETWORK_INFO: 'system:get-network-info',
  SYSTEM_SHOW_NOTIFICATION: 'system:show-notification',
  SYSTEM_OPEN_EXTERNAL: 'system:open-external',

  LOG_INFO: 'log:info',
  LOG_WARN: 'log:warn',
  LOG_ERROR: 'log:error',
  LOG_DEBUG: 'log:debug',

  UPDATE_CHECK: 'update:check',
  UPDATE_DOWNLOAD: 'update:download',
  UPDATE_INSTALL: 'update:install',
  UPDATE_RESTART: 'update:restart',
} as const;

export const MAIN_TO_RENDERER_CHANNELS = {
  TOR_STATUS_UPDATE: 'tor:status-update',
  TOR_CONNECTION_CHANGED: 'tor:connection-changed',
  TOR_CONNECTION_UPDATE: 'tor:connection-changed',
  TOR_BOOTSTRAP_PROGRESS: 'tor:bootstrap-progress',
  TOR_BOOTSTRAP_UPDATE: 'tor:bootstrap-progress',
  TOR_CIRCUIT_UPDATE: 'tor:circuit-update',

  DOCKER_SERVICE_STATUS: 'docker:service-status',
  DOCKER_CONTAINER_UPDATE: 'docker:container-update',
  DOCKER_HEALTH_CHECK: 'docker:health-check',

  SYSTEM_NOTIFICATION: 'system:notification',
  ERROR_OCCURRED: 'error:occurred',

  AUTH_STATUS_CHANGED: 'auth:status-changed',
  AUTH_TOKEN_EXPIRED: 'auth:token-expired',

  CONFIG_UPDATED: 'config:updated',
  SETTINGS_CHANGED: 'settings:changed',

  UPDATE_AVAILABLE: 'update:available',
  UPDATE_PROGRESS: 'update:progress',
  UPDATE_COMPLETED: 'update:completed',
  LOG_EVENT: 'log:event',
} as const;

export const BIDIRECTIONAL_CHANNELS = {
  WINDOW_SEND_MESSAGE: 'window:send-message',
  WINDOW_BROADCAST: 'window:broadcast',
  DATA_SYNC: 'data:sync',
  DATA_GET: 'data:get',
  DATA_SET: 'data:set',
  DATA_DELETE: 'data:delete',
  EVENT_SUBSCRIBE: 'event:subscribe',
  EVENT_UNSUBSCRIBE: 'event:unsubscribe',
} as const;

export const IPCChannels = {
  ...RENDERER_TO_MAIN_CHANNELS,
  ...MAIN_TO_RENDERER_CHANNELS,
  ...BIDIRECTIONAL_CHANNELS,
  WINDOW_CREATE: 'window:create',
  WINDOW_CLOSE: 'window:close',
  WINDOW_MINIMIZE: 'window:minimize',
  WINDOW_MAXIMIZE: 'window:maximize',
  WINDOW_RESTORE: 'window:restore',
  WINDOW_GET_LIST: 'window:get-list',
  WINDOW_GET_STATISTICS: 'window:get-statistics',
  DOCKER_GET_STATUS: 'docker:get-status',
  DOCKER_CONNECT_SSH: 'docker:connect-ssh',
  DOCKER_DISCONNECT: 'docker:disconnect',
  DOCKER_GET_CONTAINERS: 'docker:get-containers',
  DOCKER_GET_CONTAINER: 'docker:get-container',
  DOCKER_START_CONTAINER: 'docker:start-container',
  DOCKER_STOP_CONTAINER: 'docker:stop-container',
  DOCKER_RESTART_CONTAINER: 'docker:restart-container',
  DOCKER_REMOVE_CONTAINER: 'docker:remove-container',
  DOCKER_GET_LOGS: 'docker:get-logs',
  DOCKER_GET_STATS: 'docker:get-stats',
  DOCKER_GET_ALL_STATS: 'docker:get-all-stats',
  DOCKER_PULL_IMAGE: 'docker:pull-image',
  DOCKER_GET_IMAGES: 'docker:get-images',
} as const;

export type RendererToMainChannel = ValueOf<typeof RENDERER_TO_MAIN_CHANNELS>;
export type MainToRendererChannel = ValueOf<typeof MAIN_TO_RENDERER_CHANNELS>;
export type BidirectionalChannel = ValueOf<typeof BIDIRECTIONAL_CHANNELS>;
export type IpcChannel = ValueOf<typeof IPCChannels>;

/* ------------------------------------------------------------------------ */
/* Generic IPC payload helpers                                              */
/* ------------------------------------------------------------------------ */

export interface IPCMessage<T = unknown> {
  id: string;
  channel: string;
  payload: T;
  timestamp: string;
  replyChannel?: string;
}

export interface IPCResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

/* ------------------------------------------------------------------------ */
/* Tor payloads                                                             */
/* ------------------------------------------------------------------------ */

export interface TorStartRequest {
  config?: Record<string, unknown>;
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
  config?: Record<string, unknown>;
}

export interface TorRestartResponse {
  success: boolean;
  error?: string;
}

export interface TorCircuitDescriptor {
  id: string;
  status: 'building' | 'built' | 'extended' | 'closed';
  path: string[];
  age: number;
  purpose?: string;
  flags?: string[];
}

export interface TorGetStatusResponse {
  connected: boolean;
  connecting: boolean;
  bootstrapProgress: number;
  circuits: TorCircuitDescriptor[];
  proxyPort: number;
  controlPort: number;
  error?: string;
  lastConnected?: string;
}

export interface TorGetMetricsResponse {
  uptimeSeconds: number;
  bytesRead: number;
  bytesWritten: number;
  circuitsBuilt: number;
  circuitsFailed: number;
  lastUpdated: string;
}

export interface TorTestConnectionRequest {
  url: string;
  timeout?: number;
  expectedStatus?: number;
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

export interface TorStatusMessage {
  status: 'connected' | 'connecting' | 'disconnected' | 'error';
  progress?: number;
  circuits?: number;
  proxyPort?: number;
  error?: string;
}

export interface TorConnectionMessage {
  connected: boolean;
  timestamp: string;
  error?: string;
}

export interface TorBootstrapMessage {
  progress: number;
  summary?: string;
  warning?: string;
}

export interface TorCircuitMessage {
  circuitId: string;
  status: TorCircuitDescriptor['status'];
  path: string[];
  age: number;
  purpose?: string;
  flags?: string[];
}

/* ------------------------------------------------------------------------ */
/* Docker payloads                                                          */
/* ------------------------------------------------------------------------ */

export type DockerServiceStatus = 'stopped' | 'starting' | 'running' | 'error';
export type DockerServiceHealth = 'healthy' | 'unhealthy' | 'starting';

export interface DockerServiceState {
  service: string;
  displayName: string;
  image: string;
  level: 'support' | 'core' | 'application' | 'admin' | 'developer' | 'user' | 'node';
  plane: 'support' | 'core' | 'application' | 'ops';
  status: DockerServiceStatus;
  containerId?: string;
  ports: string[];
  health?: DockerServiceHealth;
  error?: string;
  updatedAt: string;
}

export interface DockerStartServicesRequest {
  services: string[];
  level?: string;
}

export interface DockerServiceOperationFailure {
  service: string;
  error: string;
}

export interface DockerStartServicesResponse {
  success: boolean;
  started: string[];
  failed: DockerServiceOperationFailure[];
  services: DockerServiceState[];
  level?: string;
  timestamp: string;
}

export interface DockerStopServicesRequest {
  services: string[];
}

export interface DockerStopServicesResponse {
  success: boolean;
  stopped: string[];
  failed: DockerServiceOperationFailure[];
  services: DockerServiceState[];
  timestamp: string;
}

export interface DockerRestartServicesResponse {
  success: boolean;
  restarted: string[];
  failed: DockerServiceOperationFailure[];
  services: DockerServiceState[];
  timestamp: string;
}

export interface DockerGetServiceStatusResponse {
  services: DockerServiceState[];
  generatedAt: string;
}

export interface DockerGetContainerLogsRequest {
  containerId: string;
  lines?: number;
  follow?: boolean;
}

export interface DockerGetContainerLogsResponse {
  containerId: string;
  logs: string[];
  error?: string;
  generatedAt: string;
}

export interface DockerExecCommandRequest {
  containerId: string;
  command: string[];
  workingDir?: string;
  env?: Record<string, string>;
}

export interface DockerExecCommandResponse {
  success: boolean;
  containerId: string;
  output: string;
  error?: string;
  exitCode: number;
  startedAt: string;
  finishedAt: string;
}

export interface DockerServiceMessage {
  service: string;
  status: DockerServiceStatus;
  containerId?: string;
  error?: string;
  level?: string;
  plane?: string;
  timestamp: string;
}

export interface DockerContainerMessage {
  containerId: string;
  status: DockerServiceStatus | string;
  name: string;
  image: string;
  ports: string[];
  health?: DockerServiceHealth | string;
  updatedAt: string;
}

export interface DockerHealthMessage {
  service: string;
  healthy: boolean;
  lastCheck: string;
  responseTime: number;
  error?: string;
}

/* ------------------------------------------------------------------------ */
/* Authentication payloads                                                  */
/* ------------------------------------------------------------------------ */

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
  expiresAt?: string;
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
  success: boolean;
  user?: {
    id: string;
    email: string;
    role: string;
  };
  expiresAt?: string;
  error?: string;
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
  timestamp?: string;
}

export interface AuthTokenExpiredMessage {
  reason: string;
  timestamp: string;
}

/* ------------------------------------------------------------------------ */
/* Configuration & notification payloads                                   */
/* ------------------------------------------------------------------------ */

export interface ConfigUpdatedMessage {
  key: string;
  value: unknown;
  scope: 'user' | 'system' | 'session';
  updatedAt: string;
  updatedBy?: string;
}

export interface SettingsChangedMessage {
  category: string;
  changes: Record<string, unknown>;
  timestamp: string;
}

export interface SystemNotificationMessage {
  title: string;
  body: string;
  level?: 'info' | 'success' | 'warning' | 'error';
  icon?: string;
  actions?: Array<{ label: string; action: string }>;
  timeout?: number;
}

export interface WarningMessage {
  code: string;
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

export interface ErrorMessage {
  code: string;
  message: string;
  timestamp: string;
  severity?: 'info' | 'warning' | 'error' | 'critical';
  details?: Record<string, unknown>;
  stack?: string;
}

/* ------------------------------------------------------------------------ */
/* API proxy payloads                                                       */
/* ------------------------------------------------------------------------ */

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

export interface APIRequestMessage {
  method: HttpMethod;
  url: string;
  data?: unknown;
  headers?: Record<string, string>;
  timeout?: number;
}

export interface APIResponseMessage {
  requestId: string;
  data: unknown;
  status: number;
  headers?: Record<string, string>;
}

export interface APIErrorMessage {
  requestId: string;
  error: string;
  status: number;
  details?: unknown;
}

/* ------------------------------------------------------------------------ */
/* Logging payloads                                                         */
/* ------------------------------------------------------------------------ */

export interface LogEventMessage {
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  timestamp: string;
  context?: Record<string, unknown>;
}

/* ------------------------------------------------------------------------ */
/* Validation helpers                                                       */
/* ------------------------------------------------------------------------ */

export function isValidChannel(channel: string): channel is IpcChannel {
  return Object.values(IPCChannels).includes(channel as IpcChannel);
}

export function isValidMessage(message: unknown): message is IPCMessage {
  if (!message || typeof message !== 'object') {
    return false;
  }

  const candidate = message as Record<string, unknown>;
  return (
    typeof candidate.id === 'string' &&
    typeof candidate.channel === 'string' &&
    typeof candidate.timestamp === 'string' &&
    isValidChannel(candidate.channel)
  );
}

export function isValidResponse(response: unknown): response is IPCResponse {
  if (!response || typeof response !== 'object') {
    return false;
  }

  const candidate = response as Record<string, unknown>;
  return typeof candidate.success === 'boolean' && typeof candidate.timestamp === 'string';
}