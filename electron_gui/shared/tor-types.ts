// Tor-specific TypeScript types for Lucid Electron GUI
// Based on the electron-multi-gui-development.plan.md specifications

export interface TorStatus {
  is_connected: boolean;
  bootstrap_progress: number;
  circuits: TorCircuit[];
  proxy_port: number;
  status: 'connecting' | 'connected' | 'disconnected';
  last_connected?: string;
  error?: string;
}

export interface TorCircuit {
  id: string;
  path: string[];
  status: 'building' | 'built' | 'extended';
  age: number;
  purpose: string;
  flags: string[];
}

export interface TorConfig {
  socks_port: number;
  control_port: number;
  data_dir: string;
  config_file: string;
  bootstrap_timeout: number;
  circuit_build_timeout: number;
  exit_nodes?: string[];
  entry_nodes?: string[];
  strict_nodes?: boolean;
  exclude_nodes?: string[];
}

export interface TorBootstrapEvent {
  type: 'bootstrap';
  progress: number;
  summary: string;
  warning?: string;
}

export interface TorCircuitEvent {
  type: 'circuit';
  circuit: TorCircuit;
  action: 'created' | 'extended' | 'closed';
}

export interface TorStatusEvent {
  type: 'status';
  status: TorStatus;
}

export type TorEvent = TorBootstrapEvent | TorCircuitEvent | TorStatusEvent;

export interface TorConnectionOptions {
  socks_port?: number;
  control_port?: number;
  data_dir?: string;
  config_file?: string;
  bootstrap_timeout?: number;
  circuit_build_timeout?: number;
  auto_start?: boolean;
  retry_attempts?: number;
  retry_delay?: number;
}

export interface TorProxyConfig {
  host: string;
  port: number;
  protocol: 'socks4' | 'socks5';
  username?: string;
  password?: string;
}

export interface TorMetrics {
  bytes_read: number;
  bytes_written: number;
  circuits_built: number;
  circuits_failed: number;
  bootstrap_time: number;
  uptime: number;
}

export interface TorNodeInfo {
  fingerprint: string;
  nickname: string;
  address: string;
  port: number;
  flags: string[];
  uptime: number;
  bandwidth: {
    read: number;
    write: number;
  };
}

export interface TorNetworkStatus {
  consensus_valid_after: string;
  consensus_fresh_until: string;
  consensus_valid_until: string;
  voting_delay: number;
  recommended_client_protocols: string[];
  recommended_relay_protocols: string[];
  required_client_protocols: string[];
  required_relay_protocols: string[];
}

export interface TorVersionInfo {
  version: string;
  status: string;
  proto: string;
  protover: string;
}

export interface TorConnectionTest {
  url: string;
  timeout: number;
  expected_status: number;
  test_name: string;
}

export interface TorHealthCheck {
  is_healthy: boolean;
  last_check: string;
  response_time: number;
  error?: string;
  tests: {
    socks_proxy: boolean;
    control_port: boolean;
    bootstrap: boolean;
    circuit_build: boolean;
  };
}

// Tor event handler types
export type TorEventHandler = (event: TorEvent) => void;
export type TorStatusHandler = (status: TorStatus) => void;
export type TorErrorHandler = (error: Error) => void;

// Tor service interface
export interface TorService {
  start(): Promise<void>;
  stop(): Promise<void>;
  restart(): Promise<void>;
  getStatus(): Promise<TorStatus>;
  getMetrics(): Promise<TorMetrics>;
  getNetworkStatus(): Promise<TorNetworkStatus>;
  getVersionInfo(): Promise<TorVersionInfo>;
  testConnection(test: TorConnectionTest): Promise<boolean>;
  healthCheck(): Promise<TorHealthCheck>;
  addEventListener(event: string, handler: TorEventHandler): void;
  removeEventListener(event: string, handler: TorEventHandler): void;
  isRunning(): boolean;
  getProxyConfig(): TorProxyConfig;
}

// Tor configuration validation
export interface TorConfigValidation {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  config: TorConfig;
}

// Tor startup options
export interface TorStartupOptions {
  config_file?: string;
  data_directory?: string;
  socks_port?: number;
  control_port?: number;
  log_level?: 'debug' | 'info' | 'notice' | 'warn' | 'err';
  log_file?: string;
  pid_file?: string;
  user?: string;
  group?: string;
  chroot?: string;
  no_new_privs?: boolean;
  sandbox?: boolean;
}

// Tor circuit management
export interface TorCircuitManager {
  buildCircuit(): Promise<TorCircuit>;
  extendCircuit(circuitId: string, path: string[]): Promise<TorCircuit>;
  closeCircuit(circuitId: string): Promise<void>;
  getCircuits(): Promise<TorCircuit[]>;
  getCircuit(circuitId: string): Promise<TorCircuit | null>;
}

// Tor stream management
export interface TorStream {
  id: string;
  circuit_id: string;
  target_address: string;
  target_port: number;
  status: 'new' | 'connecting' | 'open' | 'closed';
  purpose: string;
  remote_host: string;
  remote_port: number;
}

export interface TorStreamManager {
  createStream(circuitId: string, target: string, port: number): Promise<TorStream>;
  closeStream(streamId: string): Promise<void>;
  getStreams(): Promise<TorStream[]>;
  getStream(streamId: string): Promise<TorStream | null>;
}

// Tor directory management
export interface TorDirectory {
  nickname: string;
  fingerprint: string;
  address: string;
  port: number;
  flags: string[];
  uptime: number;
  bandwidth: {
    read: number;
    write: number;
  };
  version: string;
  contact: string;
}

export interface TorDirectoryManager {
  getDirectories(): Promise<TorDirectory[]>;
  getDirectory(nickname: string): Promise<TorDirectory | null>;
  refreshDirectories(): Promise<void>;
}

// Tor statistics
export interface TorStatistics {
  bytes_read: number;
  bytes_written: number;
  circuits_built: number;
  circuits_failed: number;
  streams_created: number;
  streams_failed: number;
  bootstrap_time: number;
  uptime: number;
  last_reset: string;
}

export interface TorStatisticsManager {
  getStatistics(): Promise<TorStatistics>;
  resetStatistics(): Promise<void>;
  getBandwidthUsage(): Promise<{ read: number; write: number }>;
  getCircuitStatistics(): Promise<{ built: number; failed: number }>;
  getStreamStatistics(): Promise<{ created: number; failed: number }>;
}
