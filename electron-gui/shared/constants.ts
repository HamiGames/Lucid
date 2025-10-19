// API Endpoints Configuration (from 00-master-api-architecture.md)
export const API_ENDPOINTS = {
  GATEWAY: 'http://localhost:8080',  // Proxied through Tor
  BLOCKCHAIN: 'http://localhost:8084',
  AUTH: 'http://localhost:8089',
  SESSIONS: 'http://localhost:8087',
  NODES: 'http://localhost:8095',
  ADMIN: 'http://localhost:8083',
  TRON_PAYMENT: 'http://localhost:8085',
} as const;

// Service ports mapping
export const SERVICE_PORTS = {
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
} as const;

// Tor configuration
export const TOR_CONFIG = {
  SOCKS_PORT: 9050,
  CONTROL_PORT: 9051,
  DATA_DIR: 'tor-data',
  CONFIG_FILE: 'torrc',
  BOOTSTRAP_TIMEOUT: 60000, // 60 seconds
  CIRCUIT_BUILD_TIMEOUT: 60000, // 60 seconds
} as const;

// Docker compose files for different service levels
export const DOCKER_COMPOSE_FILES = {
  admin: [
    'configs/docker/docker-compose.foundation.yml',
    'configs/docker/docker-compose.core.yml',
    'configs/docker/docker-compose.application.yml',
    'configs/docker/docker-compose.support.yml',
  ],
  developer: [
    'configs/docker/docker-compose.foundation.yml',
    'configs/docker/docker-compose.core.yml',
    'configs/docker/docker-compose.application.yml',
  ],
  user: [],
  node: [],
} as const;

// Service names mapping
export const SERVICE_NAMES = {
  API_GATEWAY: 'api-gateway',
  BLOCKCHAIN_CORE: 'lucid-blocks',
  AUTHENTICATION: 'auth-service',
  SESSION_MANAGEMENT: 'session-api',
  NODE_MANAGEMENT: 'node-management',
  ADMIN_INTERFACE: 'admin-interface',
  TRON_PAYMENT: 'tron-payment-service',
} as const;

// Window configurations
export const WINDOW_CONFIGS = {
  user: {
    name: 'user',
    title: 'Lucid User Interface',
    width: 1200,
    height: 800,
    level: 'user' as const,
  },
  developer: {
    name: 'developer',
    title: 'Lucid Developer Console',
    width: 1400,
    height: 900,
    level: 'developer' as const,
  },
  node: {
    name: 'node',
    title: 'Lucid Node Operator',
    width: 1200,
    height: 800,
    level: 'node' as const,
  },
  admin: {
    name: 'admin',
    title: 'Lucid System Administration',
    width: 1600,
    height: 1000,
    level: 'admin' as const,
  },
} as const;

// Error codes from Lucid API specification
export const LUCID_ERROR_CODES = {
  // Validation errors (1xxx)
  VALIDATION_ERROR: 'LUCID_ERR_1001',
  INVALID_USER_ID: 'LUCID_ERR_1002',
  INVALID_SESSION_ID: 'LUCID_ERR_1003',
  INVALID_CHUNK_ID: 'LUCID_ERR_1004',
  
  // Authentication/Authorization errors (2xxx)
  AUTHENTICATION_FAILED: 'LUCID_ERR_2001',
  AUTHORIZATION_DENIED: 'LUCID_ERR_2002',
  TOKEN_EXPIRED: 'LUCID_ERR_2003',
  INVALID_TOKEN: 'LUCID_ERR_2004',
  
  // Rate limiting errors (3xxx)
  RATE_LIMIT_EXCEEDED: 'LUCID_ERR_3001',
  TOO_MANY_REQUESTS: 'LUCID_ERR_3002',
  
  // Business logic errors (4xxx)
  SESSION_NOT_FOUND: 'LUCID_ERR_4001',
  SESSION_ALREADY_ANCHORED: 'LUCID_ERR_4002',
  NODE_NOT_REGISTERED: 'LUCID_ERR_4003',
  POOL_FULL: 'LUCID_ERR_4004',
  
  // System errors (5xxx)
  INTERNAL_SERVER_ERROR: 'LUCID_ERR_5001',
  DATABASE_ERROR: 'LUCID_ERR_5002',
  BLOCKCHAIN_ERROR: 'LUCID_ERR_5003',
  TOR_CONNECTION_ERROR: 'LUCID_ERR_5004',
} as const;

// File paths
export const PATHS = {
  TOR_BINARY_WIN: 'assets/tor/tor.exe',
  TOR_BINARY_LINUX: 'assets/tor/tor',
  TOR_BINARY_MAC: 'assets/tor/tor',
  TOR_CONFIG_TEMPLATE: 'assets/tor/torrc.template',
  APP_ICON: 'assets/icons/icon.ico',
} as const;

// Timeouts (in milliseconds)
export const TIMEOUTS = {
  API_REQUEST: 30000,
  TOR_BOOTSTRAP: 60000,
  DOCKER_STARTUP: 120000,
  FILE_UPLOAD: 300000,
  BLOCKCHAIN_CONFIRMATION: 60000,
} as const;

// Chunk configuration
export const CHUNK_CONFIG = {
  MAX_SIZE_MB: 10,
  MAX_SESSION_SIZE_GB: 100,
  COMPRESSION_LEVEL: 6,
  ENCRYPTION_ALGORITHM: 'AES-256-GCM',
} as const;

// Hardware wallet types
export const HARDWARE_WALLET_TYPES = {
  LEDGER: 'ledger',
  TREZOR: 'trezor',
  KEEPKEY: 'keepkey',
} as const;

// User roles
export const USER_ROLES = {
  USER: 'user',
  NODE_OPERATOR: 'node_operator',
  ADMIN: 'admin',
  SUPER_ADMIN: 'super_admin',
} as const;

// Session statuses
export const SESSION_STATUSES = {
  ACTIVE: 'active',
  COMPLETED: 'completed',
  FAILED: 'failed',
  ANCHORED: 'anchored',
} as const;

// Node statuses
export const NODE_STATUSES = {
  REGISTERED: 'registered',
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  SUSPENDED: 'suspended',
} as const;

// Payout statuses
export const PAYOUT_STATUSES = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;
