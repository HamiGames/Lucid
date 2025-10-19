/**
 * LUCID IPC Channels - SPEC-1B Implementation
 * Defines all IPC communication channels between main and renderer processes
 */

export const IPCChannels = {
  // Tor Management Channels
  TOR_GET_STATUS: 'tor:get-status',
  TOR_START: 'tor:start',
  TOR_STOP: 'tor:stop',
  TOR_RESTART: 'tor:restart',
  TOR_GET_VERSION: 'tor:get-version',
  TOR_GET_CIRCUITS: 'tor:get-circuits',
  TOR_GET_BANDWIDTH: 'tor:get-bandwidth',
  TOR_STATUS_CHANGED: 'tor:status-changed',

  // Window Management Channels
  WINDOW_CREATE: 'window:create',
  WINDOW_CLOSE: 'window:close',
  WINDOW_MINIMIZE: 'window:minimize',
  WINDOW_MAXIMIZE: 'window:maximize',
  WINDOW_RESTORE: 'window:restore',
  WINDOW_FOCUS: 'window:focus',
  WINDOW_CASCADE: 'window:cascade',
  WINDOW_TILE: 'window:tile',
  WINDOW_MINIMIZE_ALL: 'window:minimize-all',
  WINDOW_RESTORE_ALL: 'window:restore-all',
  WINDOW_CLOSE_ALL: 'window:close-all',
  WINDOW_GET_LIST: 'window:get-list',
  WINDOW_GET_STATISTICS: 'window:get-statistics',

  // Docker Service Channels
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

  // API Proxy Channels
  API_REQUEST: 'api:request',
  API_GET_ENDPOINTS: 'api:get-endpoints',
  API_TEST_CONNECTION: 'api:test-connection',

  // Hardware Wallet Channels
  HARDWARE_WALLET_CONNECT: 'hardware-wallet:connect',
  HARDWARE_WALLET_DISCONNECT: 'hardware-wallet:disconnect',
  HARDWARE_WALLET_GET_STATUS: 'hardware-wallet:get-status',
  HARDWARE_WALLET_GET_ADDRESS: 'hardware-wallet:get-address',
  HARDWARE_WALLET_SIGN: 'hardware-wallet:sign',
  HARDWARE_WALLET_VERIFY: 'hardware-wallet:verify',
  HARDWARE_WALLET_STATUS_CHANGED: 'hardware-wallet:status-changed',

  // Session Management Channels
  SESSION_CREATE: 'session:create',
  SESSION_GET: 'session:get',
  SESSION_UPDATE: 'session:update',
  SESSION_DELETE: 'session:delete',
  SESSION_LIST: 'session:list',
  SESSION_START_RECORDING: 'session:start-recording',
  SESSION_STOP_RECORDING: 'session:stop-recording',
  SESSION_UPLOAD_CHUNK: 'session:upload-chunk',
  SESSION_GET_CHUNKS: 'session:get-chunks',
  SESSION_GET_METADATA: 'session:get-metadata',

  // Blockchain Channels
  BLOCKCHAIN_GET_STATUS: 'blockchain:get-status',
  BLOCKCHAIN_GET_HEIGHT: 'blockchain:get-height',
  BLOCKCHAIN_GET_BLOCK: 'blockchain:get-block',
  BLOCKCHAIN_SUBMIT_PROOF: 'blockchain:submit-proof',
  BLOCKCHAIN_GET_PROOFS: 'blockchain:get-proofs',
  BLOCKCHAIN_ANCHOR_SESSION: 'blockchain:anchor-session',

  // Node Management Channels
  NODE_REGISTER: 'node:register',
  NODE_GET_STATUS: 'node:get-status',
  NODE_GET_METRICS: 'node:get-metrics',
  NODE_JOIN_POOL: 'node:join-pool',
  NODE_LEAVE_POOL: 'node:leave-pool',
  NODE_GET_POOLS: 'node:get-pools',
  NODE_CALCULATE_POOT: 'node:calculate-poot',

  // User Management Channels
  USER_LOGIN: 'user:login',
  USER_LOGOUT: 'user:logout',
  USER_GET_PROFILE: 'user:get-profile',
  USER_UPDATE_PROFILE: 'user:update-profile',
  USER_CHANGE_PASSWORD: 'user:change-password',
  USER_GET_SESSIONS: 'user:get-sessions',

  // Admin Channels
  ADMIN_GET_DASHBOARD: 'admin:get-dashboard',
  ADMIN_GET_USERS: 'admin:get-users',
  ADMIN_CREATE_USER: 'admin:create-user',
  ADMIN_UPDATE_USER: 'admin:update-user',
  ADMIN_DELETE_USER: 'admin:delete-user',
  ADMIN_GET_NODES: 'admin:get-nodes',
  ADMIN_MANAGE_NODE: 'admin:manage-node',
  ADMIN_GET_SYSTEM_LOGS: 'admin:get-system-logs',
  ADMIN_GET_AUDIT_LOGS: 'admin:get-audit-logs',
  ADMIN_SYSTEM_SHUTDOWN: 'admin:system-shutdown',
  ADMIN_SYSTEM_RESTART: 'admin:system-restart',
  ADMIN_EMERGENCY_LOCKDOWN: 'admin:emergency-lockdown',

  // TRON Payment Channels (Isolated)
  TRON_GET_WALLET: 'tron:get-wallet',
  TRON_GET_BALANCE: 'tron:get-balance',
  TRON_SEND_TRANSACTION: 'tron:send-transaction',
  TRON_GET_TRANSACTIONS: 'tron:get-transactions',
  TRON_STAKE_TRX: 'tron:stake-trx',
  TRON_UNSTAKE_TRX: 'tron:unstake-trx',
  TRON_GET_STAKING_INFO: 'tron:get-staking-info',

  // File System Channels
  FS_READ_FILE: 'fs:read-file',
  FS_WRITE_FILE: 'fs:write-file',
  FS_DELETE_FILE: 'fs:delete-file',
  FS_LIST_DIRECTORY: 'fs:list-directory',
  FS_CREATE_DIRECTORY: 'fs:create-directory',
  FS_GET_FILE_INFO: 'fs:get-file-info',

  // Configuration Channels
  CONFIG_GET: 'config:get',
  CONFIG_SET: 'config:set',
  CONFIG_RESET: 'config:reset',
  CONFIG_EXPORT: 'config:export',
  CONFIG_IMPORT: 'config:import',

  // Notification Channels
  NOTIFICATION_SHOW: 'notification:show',
  NOTIFICATION_HIDE: 'notification:hide',
  NOTIFICATION_CLEAR_ALL: 'notification:clear-all',

  // Update Channels
  UPDATE_CHECK: 'update:check',
  UPDATE_DOWNLOAD: 'update:download',
  UPDATE_INSTALL: 'update:install',
  UPDATE_STATUS_CHANGED: 'update:status-changed',

  // Security Channels
  SECURITY_GET_STATUS: 'security:get-status',
  SECURITY_SCAN_FILE: 'security:scan-file',
  SECURITY_VALIDATE_CERTIFICATE: 'security:validate-certificate',
  SECURITY_GENERATE_KEYPAIR: 'security:generate-keypair',

  // Logging Channels
  LOG_INFO: 'log:info',
  LOG_WARN: 'log:warn',
  LOG_ERROR: 'log:error',
  LOG_DEBUG: 'log:debug',

  // Error Handling Channels
  ERROR_REPORT: 'error:report',
  ERROR_GET_LOGS: 'error:get-logs',
  ERROR_CLEAR_LOGS: 'error:clear-logs',

  // Development Channels (Development only)
  DEV_OPEN_DEVTOOLS: 'dev:open-devtools',
  DEV_RELOAD_WINDOW: 'dev:reload-window',
  DEV_TOGGLE_DEBUG: 'dev:toggle-debug',
  DEV_GET_PERFORMANCE: 'dev:get-performance'
} as const;

// Type definitions for IPC message payloads
export interface IPCMessage<T = any> {
  id: string;
  channel: string;
  payload: T;
  timestamp: string;
  replyChannel?: string;
}

export interface IPCResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

// Tor-related types
export interface TorStatusMessage {
  connected: boolean;
  status: 'stopped' | 'starting' | 'connected' | 'error';
  socksPort: number;
  controlPort: number;
  version?: string;
  error?: string;
}

// Docker-related types
export interface DockerContainerMessage {
  id: string;
  name: string;
  image: string;
  status: string;
  ports: string[];
}

export interface DockerStatsMessage {
  id: string;
  cpu_percent: number;
  memory_usage: number;
  network_rx: number;
  network_tx: number;
}

// Hardware wallet types
export interface HardwareWalletMessage {
  type: 'ledger' | 'trezor' | 'keepkey';
  connected: boolean;
  address?: string;
  error?: string;
}

// Session types
export interface SessionMessage {
  sessionId: string;
  userId: string;
  state: string;
  config: any;
  metadata: any;
}

export interface SessionChunkMessage {
  chunkId: string;
  sessionId: string;
  sequenceNumber: number;
  data: Buffer;
  metadata: any;
}

// API request types
export interface APIRequestMessage {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  url: string;
  headers?: Record<string, string>;
  body?: any;
  timeout?: number;
}

// Configuration types
export interface ConfigMessage {
  key: string;
  value: any;
  scope: 'user' | 'system' | 'session';
}

// Notification types
export interface NotificationMessage {
  title: string;
  message: string;
  type: 'info' | 'warning' | 'error' | 'success';
  duration?: number;
  actions?: Array<{
    label: string;
    action: string;
  }>;
}

// Error types
export interface ErrorMessage {
  code: string;
  message: string;
  stack?: string;
  context?: any;
  timestamp: string;
}

// Development types
export interface PerformanceMessage {
  memory: {
    used: number;
    total: number;
    percentage: number;
  };
  cpu: {
    usage: number;
    cores: number;
  };
  uptime: number;
  windows: number;
}

// Channel validation
export function isValidChannel(channel: string): boolean {
  return Object.values(IPCChannels).includes(channel as any);
}

// Message validation
export function isValidMessage(message: any): message is IPCMessage {
  return (
    message &&
    typeof message === 'object' &&
    typeof message.id === 'string' &&
    typeof message.channel === 'string' &&
    typeof message.timestamp === 'string' &&
    isValidChannel(message.channel)
  );
}

// Response validation
export function isValidResponse(response: any): response is IPCResponse {
  return (
    response &&
    typeof response === 'object' &&
    typeof response.success === 'boolean' &&
    typeof response.timestamp === 'string'
  );
}