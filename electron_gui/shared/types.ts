// User types (from API Gateway - Cluster 01)
export interface User {
  user_id: string;
  email: string;
  tron_address: string;
  hardware_wallet?: HardwareWallet;
  role: 'user' | 'node_operator' | 'admin' | 'super_admin';
  created_at: string;
}

export interface HardwareWallet {
  type: 'ledger' | 'trezor' | 'keepkey';
  device_id: string;
  public_key: string;
  is_connected: boolean;
}

// Session types (from Session Management - Cluster 03)
export interface Session {
  session_id: string;
  user_id: string;
  status: 'active' | 'completed' | 'failed' | 'anchored';
  chunks: Chunk[];
  merkle_root?: string;
  blockchain_anchor?: BlockchainAnchor;
  created_at: string;
  updated_at: string;
}

export interface Chunk {
  chunk_id: string;
  session_id: string;
  sequence: number;
  hash: string;
  size: number;
  encrypted: boolean;
  compressed: boolean;
}

export interface BlockchainAnchor {
  block_id: string;
  block_height: number;
  transaction_id: string;
  merkle_proof: MerkleProof;
  timestamp: string;
}

export interface MerkleProof {
  root_hash: string;
  leaf_hash: string;
  path: string[];
  proof: boolean[];
}

// Node types (from Node Management - Cluster 05)
export interface Node {
  node_id: string;
  operator_id: string;
  status: 'registered' | 'active' | 'inactive' | 'suspended';
  pool_id?: string;
  poot_score: number;
  resources: NodeResources;
  created_at: string;
}

export interface NodeResources {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_bandwidth: number;
}

export interface Pool {
  pool_id: string;
  name: string;
  description: string;
  node_count: number;
  total_poot_score: number;
  status: 'active' | 'inactive';
  created_at: string;
}

// Blockchain types (from Blockchain Core - Cluster 02)
export interface Block {
  block_id: string;
  height: number;
  previous_hash: string;
  merkle_root: string;
  transactions: Transaction[];
  timestamp: string;
  consensus_votes?: ConsensusVote[];
}

export interface Transaction {
  transaction_id: string;
  type: 'session_anchor' | 'payout' | 'governance';
  data: any;
  timestamp: string;
}

export interface ConsensusVote {
  node_id: string;
  vote: 'approve' | 'reject';
  timestamp: string;
  signature: string;
}

// Admin types
export interface ServiceStatus {
  name: string;
  status: 'starting' | 'healthy' | 'unhealthy' | 'stopped';
  uptime: number;
  cpu: number;
  memory: number;
  port: number;
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'critical';
  services: ServiceStatus[];
  tor_status: 'connected' | 'disconnected';
  docker_status: 'running' | 'stopped';
}

// TRON Payment types (from TRON Payment - Cluster 07)
export interface Payout {
  payout_id: string;
  node_id: string;
  amount_usdt: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  transaction_hash?: string;
  created_at: string;
}

export interface TRONWallet {
  address: string;
  balance_trx: number;
  balance_usdt: number;
  is_hot_wallet: boolean;
}

// API Request/Response types
export interface SessionCreateRequest {
  user_id: string;
  duration_minutes: number;
  privacy_level: 'low' | 'medium' | 'high';
  metadata?: Record<string, any>;
}

export interface SessionCreateResponse {
  session_id: string;
  upload_url: string;
  status: string;
}

export interface NodeRegistration {
  operator_id: string;
  hardware_info: {
    cpu_cores: number;
    memory_gb: number;
    disk_gb: number;
    network_speed_mbps: number;
  };
  location: {
    country: string;
    region: string;
  };
}

// Error types
export interface LucidError {
  code: string;
  message: string;
  details?: Record<string, any>;
  request_id?: string;
  timestamp: string;
  service: string;
  version: string;
}

// Tor types
export interface TorStatus {
  is_connected: boolean;
  bootstrap_progress: number;
  circuits: TorCircuit[];
  proxy_port: number;
}

export interface TorCircuit {
  id: string;
  path: string[];
  status: 'building' | 'built' | 'extended';
  age: number;
}

// Docker types
export type ServiceLevel = 'admin' | 'developer' | 'user' | 'node';

export interface DockerService {
  name: string;
  container_id?: string;
  status: 'running' | 'stopped' | 'starting' | 'error';
  image: string;
  ports: string[];
  health?: 'healthy' | 'unhealthy' | 'starting';
}

// Window types
export interface WindowConfig {
  name: string;
  title: string;
  width: number;
  height: number;
  preload: string;
  level: ServiceLevel;
}

// IPC types
export interface IPCMessage {
  channel: string;
  data: any;
  id?: string;
}

export interface IPCResponse {
  success: boolean;
  data?: any;
  error?: LucidError;
  id?: string;
}
