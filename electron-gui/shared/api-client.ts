import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { SocksProxyAgent } from 'socks-proxy-agent';
import { 
  User, 
  Session, 
  SessionCreateRequest, 
  SessionCreateResponse,
  Node,
  NodeRegistration,
  Block,
  Payout,
  LucidError,
  API_ENDPOINTS,
  LUCID_ERROR_CODES
} from './types';

// Service discovery helper function
export function getServiceEndpoint(serviceName: string): string {
  const endpoints = {
    auth: API_ENDPOINTS.AUTH,
    gateway: API_ENDPOINTS.API_GATEWAY,
    admin: API_ENDPOINTS.ADMIN,
    blockchain: API_ENDPOINTS.BLOCKCHAIN_ENGINE,
    session: API_ENDPOINTS.SESSION_API,
    node: API_ENDPOINTS.NODE_MANAGEMENT,
    mongodb: API_ENDPOINTS.MONGODB,
    redis: API_ENDPOINTS.REDIS,
    elasticsearch: API_ENDPOINTS.ELASTICSEARCH,
    serviceMesh: API_ENDPOINTS.SERVICE_MESH,
    sessionAnchoring: API_ENDPOINTS.SESSION_ANCHORING,
    blockManager: API_ENDPOINTS.BLOCK_MANAGER,
    dataChain: API_ENDPOINTS.DATA_CHAIN,
    rdpServer: API_ENDPOINTS.RDP_SERVER,
    sessionController: API_ENDPOINTS.SESSION_CONTROLLER,
    resourceMonitor: API_ENDPOINTS.RESOURCE_MONITOR,
    tronClient: API_ENDPOINTS.TRON_CLIENT,
    payoutRouter: API_ENDPOINTS.PAYOUT_ROUTER,
    walletManager: API_ENDPOINTS.WALLET_MANAGER,
    usdtManager: API_ENDPOINTS.USDT_MANAGER,
    trxStaking: API_ENDPOINTS.TRX_STAKING,
    paymentGateway: API_ENDPOINTS.PAYMENT_GATEWAY,
  };
  
  return endpoints[serviceName] || API_ENDPOINTS.API_GATEWAY;
}

export class LucidAPIClient {
  private client: AxiosInstance;
  private torProxy: string = 'socks5://127.0.0.1:9050';
  private baseURL: string;
  
  constructor(baseURL: string = API_ENDPOINTS.GATEWAY) {
    this.baseURL = baseURL;
    const agent = new SocksProxyAgent(this.torProxy);
    
    this.client = axios.create({
      baseURL,
      httpAgent: agent,
      httpsAgent: agent,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    // Request interceptor for auth tokens
    this.client.interceptors.request.use((config) => {
      const token = this.getAuthToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
    
    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => this.handleAPIError(error)
    );
  }
  
  private getAuthToken(): string | null {
    // Get token from localStorage or secure storage
    return localStorage.getItem('lucid_auth_token');
  }
  
  private handleAPIError(error: any): Promise<never> {
    if (error.response?.data?.error) {
      const lucidError: LucidError = error.response.data.error;
      throw new Error(`${lucidError.code}: ${lucidError.message}`);
    }
    
    if (error.code === 'ECONNREFUSED') {
      throw new Error(`${LUCID_ERROR_CODES.TOR_CONNECTION_ERROR}: Tor connection failed`);
    }
    
    throw new Error(`${LUCID_ERROR_CODES.INTERNAL_SERVER_ERROR}: ${error.message}`);
  }
  
  // User API methods
  async getUserProfile(userId: string): Promise<User> {
    const response = await this.client.get(`/api/v1/users/${userId}`);
    return response.data;
  }
  
  async updateUserProfile(userId: string, data: Partial<User>): Promise<User> {
    const response = await this.client.put(`/api/v1/users/${userId}`, data);
    return response.data;
  }
  
  async deleteUser(userId: string): Promise<void> {
    await this.client.delete(`/api/v1/users/${userId}`);
  }
  
  // Session API methods
  async createSession(data: SessionCreateRequest): Promise<SessionCreateResponse> {
    const response = await this.client.post('/api/v1/sessions', data);
    return response.data;
  }
  
  async getSession(sessionId: string): Promise<Session> {
    const response = await this.client.get(`/api/v1/sessions/${sessionId}`);
    return response.data;
  }
  
  async getUserSessions(userId: string): Promise<Session[]> {
    const response = await this.client.get(`/api/v1/sessions?user_id=${userId}`);
    return response.data;
  }
  
  async updateSession(sessionId: string, data: Partial<Session>): Promise<Session> {
    const response = await this.client.put(`/api/v1/sessions/${sessionId}`, data);
    return response.data;
  }
  
  async deleteSession(sessionId: string): Promise<void> {
    await this.client.delete(`/api/v1/sessions/${sessionId}`);
  }
  
  // Chunk API methods
  async uploadChunk(sessionId: string, chunkData: FormData): Promise<void> {
    await this.client.post(`/api/v1/sessions/${sessionId}/chunks`, chunkData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }
  
  async downloadChunk(chunkId: string): Promise<Blob> {
    const response = await this.client.get(`/api/v1/chunks/${chunkId}`, {
      responseType: 'blob',
    });
    return response.data;
  }
  
  // Blockchain API methods
  async getBlock(height: number): Promise<Block> {
    const response = await this.client.get(`/api/v1/blocks/${height}`);
    return response.data;
  }
  
  async getLatestBlock(): Promise<Block> {
    const response = await this.client.get('/api/v1/blocks/latest');
    return response.data;
  }
  
  async getBlockchainInfo(): Promise<any> {
    const response = await this.client.get('/api/v1/blockchain/info');
    return response.data;
  }
  
  // Node API methods
  async registerNode(nodeData: NodeRegistration): Promise<Node> {
    const response = await this.client.post('/api/v1/nodes/register', nodeData);
    return response.data;
  }
  
  async getNode(nodeId: string): Promise<Node> {
    const response = await this.client.get(`/api/v1/nodes/${nodeId}`);
    return response.data;
  }
  
  async getNodeStatus(nodeId: string): Promise<any> {
    const response = await this.client.get(`/api/v1/nodes/${nodeId}/status`);
    return response.data;
  }
  
  async joinPool(nodeId: string, poolId: string): Promise<void> {
    await this.client.post(`/api/v1/nodes/${nodeId}/pool`, { poolId });
  }
  
  async leavePool(nodeId: string): Promise<void> {
    await this.client.delete(`/api/v1/nodes/${nodeId}/pool`);
  }
  
  async getPootScore(nodeId: string): Promise<number> {
    const response = await this.client.get(`/api/v1/nodes/${nodeId}/poot`);
    return response.data.score;
  }
  
  // Payout API methods
  async getPayoutHistory(nodeId: string): Promise<Payout[]> {
    const response = await this.client.get(`/api/v1/nodes/${nodeId}/payouts`);
    return response.data;
  }
  
  async getPayouts(): Promise<Payout[]> {
    const response = await this.client.get('/api/v1/payouts');
    return response.data;
  }
  
  // Authentication API methods
  async login(email: string, signature: string): Promise<{ token: string; user: User }> {
    const response = await this.client.post('/api/v1/auth/login', {
      email,
      signature,
    });
    return response.data;
  }
  
  async logout(): Promise<void> {
    await this.client.post('/api/v1/auth/logout');
    localStorage.removeItem('lucid_auth_token');
  }
  
  async verifyToken(token: string): Promise<User> {
    const response = await this.client.post('/api/v1/auth/verify', { token });
    return response.data;
  }
  
  // Admin API methods
  async getSystemHealth(): Promise<any> {
    const response = await this.client.get('/api/v1/admin/system/health');
    return response.data;
  }
  
  async getAllUsers(): Promise<User[]> {
    const response = await this.client.get('/api/v1/admin/users');
    return response.data;
  }
  
  async getAllSessions(): Promise<Session[]> {
    const response = await this.client.get('/api/v1/admin/sessions');
    return response.data;
  }
  
  async getAllNodes(): Promise<Node[]> {
    const response = await this.client.get('/api/v1/admin/nodes');
    return response.data;
  }
  
  // Proof verification API methods
  async verifySessionProof(sessionId: string): Promise<boolean> {
    const response = await this.client.post(`/api/v1/proofs/verify/${sessionId}`);
    return response.data.verified;
  }
  
  async getMerkleProof(chunkId: string): Promise<any> {
    const response = await this.client.get(`/api/v1/proofs/merkle/${chunkId}`);
    return response.data;
  }
  
  // TRON Payment API methods
  async getWalletBalance(address: string): Promise<{ trx: number; usdt: number }> {
    const response = await this.client.get(`/api/v1/tron/balance/${address}`);
    return response.data;
  }
  
  async transferUSDT(fromAddress: string, toAddress: string, amount: number): Promise<string> {
    const response = await this.client.post('/api/v1/tron/transfer', {
      from_address: fromAddress,
      to_address: toAddress,
      amount,
    });
    return response.data.transaction_hash;
  }
}
