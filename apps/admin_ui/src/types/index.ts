export interface SystemStats {
  cpu: {
    usage: number
    cores: number
    loadAverage: number[]
  }
  memory: {
    total: number
    used: number
    free: number
    cached: number
  }
  disk: {
    total: number
    used: number
    free: number
    usage: number
  }
  network: {
    interfaces: NetworkInterface[]
    connections: number
  }
  uptime: number
}

export interface NetworkInterface {
  name: string
  ip: string
  mac: string
  status: 'up' | 'down'
  bytesIn: number
  bytesOut: number
}

export interface ServiceStatus {
  name: string
  status: 'running' | 'stopped' | 'error' | 'unknown'
  pid?: number
  uptime: number
  memory: number
  cpu: number
  port?: number
  health: 'healthy' | 'unhealthy' | 'unknown'
  lastCheck: string
}

export interface Session {
  id: string
  userId: string
  startTime: string
  endTime?: string
  status: 'active' | 'ended' | 'error'
  duration: number
  bandwidth: {
    in: number
    out: number
  }
  quality: 'high' | 'medium' | 'low'
}

export interface User {
  id: string
  username: string
  email: string
  role: 'admin' | 'user' | 'guest'
  status: 'active' | 'inactive' | 'suspended'
  createdAt: string
  lastLogin?: string
  sessions: number
}

export interface BlockchainStats {
  blockHeight: number
  lastBlockTime: string
  networkHashrate: string
  difficulty: number
  connections: number
  mempoolSize: number
}

export interface TorStats {
  status: 'connected' | 'disconnected' | 'error'
  circuitCount: number
  bandwidth: {
    read: number
    written: number
  }
  uptime: number
}
