"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.LucidAPIClient = exports.getServiceEndpoint = void 0;
const axios_1 = __importDefault(require("axios"));
const socks_proxy_agent_1 = require("socks-proxy-agent");
const constants_1 = require("./constants");
// Service discovery helper function
function getServiceEndpoint(serviceName) {
    const endpoints = {
        auth: constants_1.API_ENDPOINTS.AUTH,
        gateway: constants_1.API_ENDPOINTS.API_GATEWAY,
        admin: constants_1.API_ENDPOINTS.ADMIN,
        blockchain: constants_1.API_ENDPOINTS.BLOCKCHAIN_ENGINE,
        session: constants_1.API_ENDPOINTS.SESSION_API,
        node: constants_1.API_ENDPOINTS.NODE_MANAGEMENT,
        mongodb: constants_1.API_ENDPOINTS.MONGODB,
        redis: constants_1.API_ENDPOINTS.REDIS,
        elasticsearch: constants_1.API_ENDPOINTS.ELASTICSEARCH,
        serviceMesh: constants_1.API_ENDPOINTS.SERVICE_MESH,
        sessionAnchoring: constants_1.API_ENDPOINTS.SESSION_ANCHORING,
        blockManager: constants_1.API_ENDPOINTS.BLOCK_MANAGER,
        dataChain: constants_1.API_ENDPOINTS.DATA_CHAIN,
        rdpServer: constants_1.API_ENDPOINTS.RDP_SERVER,
        sessionController: constants_1.API_ENDPOINTS.SESSION_CONTROLLER,
        resourceMonitor: constants_1.API_ENDPOINTS.RESOURCE_MONITOR,
        tronClient: constants_1.API_ENDPOINTS.TRON_CLIENT,
        payoutRouter: constants_1.API_ENDPOINTS.PAYOUT_ROUTER,
        walletManager: constants_1.API_ENDPOINTS.WALLET_MANAGER,
        usdtManager: constants_1.API_ENDPOINTS.USDT_MANAGER,
        trxStaking: constants_1.API_ENDPOINTS.TRX_STAKING,
        paymentGateway: constants_1.API_ENDPOINTS.PAYMENT_GATEWAY,
    };
    return endpoints[serviceName] || constants_1.API_ENDPOINTS.API_GATEWAY;
}
exports.getServiceEndpoint = getServiceEndpoint;
class LucidAPIClient {
    constructor(baseURL = constants_1.API_ENDPOINTS.API_GATEWAY) {
        this.baseURL = baseURL;
        this.torProxy = `socks5://127.0.0.1:${constants_1.TOR_CONFIG.SOCKS_PORT}`;
        const agent = new socks_proxy_agent_1.SocksProxyAgent(this.torProxy);
        this.client = axios_1.default.create({
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
        this.client.interceptors.response.use((response) => response, (error) => this.handleAPIError(error));
    }
    /**
     * Returns the underlying Axios instance for advanced use cases.
     * Prefer the helper HTTP methods whenever possible.
     */
    getHttpClient() {
        return this.client;
    }
    async get(url, config) {
        const response = await this.client.get(url, config);
        return response.data;
    }
    async post(url, data, config) {
        const response = await this.client.post(url, data, config);
        return response.data;
    }
    async put(url, data, config) {
        const response = await this.client.put(url, data, config);
        return response.data;
    }
    async delete(url, config) {
        const response = await this.client.delete(url, config);
        return response.data;
    }
    getAuthToken() {
        // Get token from localStorage or secure storage
        return localStorage.getItem('lucid_auth_token');
    }
    handleAPIError(error) {
        if (error.response?.data?.error) {
            const lucidError = error.response.data.error;
            throw new Error(`${lucidError.code}: ${lucidError.message}`);
        }
        if (error.code === 'ECONNREFUSED') {
            throw new Error(`${constants_1.LUCID_ERROR_CODES.TOR_CONNECTION_ERROR}: Tor connection failed`);
        }
        throw new Error(`${constants_1.LUCID_ERROR_CODES.INTERNAL_SERVER_ERROR}: ${error.message}`);
    }
    // User API methods
    async getUserProfile(userId) {
        const response = await this.client.get(`/api/v1/users/${userId}`);
        return response.data;
    }
    async updateUserProfile(userId, data) {
        const response = await this.client.put(`/api/v1/users/${userId}`, data);
        return response.data;
    }
    async deleteUser(userId) {
        await this.client.delete(`/api/v1/users/${userId}`);
    }
    // Session API methods
    async createSession(data) {
        const response = await this.client.post('/api/v1/sessions', data);
        return response.data;
    }
    async getSession(sessionId) {
        const response = await this.client.get(`/api/v1/sessions/${sessionId}`);
        return response.data;
    }
    async getUserSessions(userId) {
        const response = await this.client.get(`/api/v1/sessions?user_id=${userId}`);
        return response.data;
    }
    async updateSession(sessionId, data) {
        const response = await this.client.put(`/api/v1/sessions/${sessionId}`, data);
        return response.data;
    }
    async deleteSession(sessionId) {
        await this.client.delete(`/api/v1/sessions/${sessionId}`);
    }
    // Chunk API methods
    async uploadChunk(sessionId, chunkData) {
        await this.client.post(`/api/v1/sessions/${sessionId}/chunks`, chunkData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    }
    async downloadChunk(chunkId) {
        const response = await this.client.get(`/api/v1/chunks/${chunkId}`, {
            responseType: 'blob',
        });
        return response.data;
    }
    // Blockchain API methods
    async getBlock(height) {
        const response = await this.client.get(`/api/v1/blocks/${height}`);
        return response.data;
    }
    async getLatestBlock() {
        const response = await this.client.get('/api/v1/blocks/latest');
        return response.data;
    }
    async getBlockchainInfo() {
        const response = await this.client.get('/api/v1/blockchain/info');
        return response.data;
    }
    // Node API methods
    async registerNode(nodeData) {
        const response = await this.client.post('/api/v1/nodes/register', nodeData);
        return response.data;
    }
    async getNode(nodeId) {
        const response = await this.client.get(`/api/v1/nodes/${nodeId}`);
        return response.data;
    }
    async getNodeStatus(nodeId) {
        const response = await this.client.get(`/api/v1/nodes/${nodeId}/status`);
        return response.data;
    }
    async joinPool(nodeId, poolId) {
        await this.client.post(`/api/v1/nodes/${nodeId}/pool`, { poolId });
    }
    async leavePool(nodeId) {
        await this.client.delete(`/api/v1/nodes/${nodeId}/pool`);
    }
    async getPootScore(nodeId) {
        const response = await this.client.get(`/api/v1/nodes/${nodeId}/poot`);
        return response.data.score;
    }
    // Payout API methods
    async getPayoutHistory(nodeId) {
        const response = await this.client.get(`/api/v1/nodes/${nodeId}/payouts`);
        return response.data;
    }
    async getPayouts() {
        const response = await this.client.get('/api/v1/payouts');
        return response.data;
    }
    // Authentication API methods
    async login(email, signature) {
        const response = await this.client.post('/api/v1/auth/login', {
            email,
            signature,
        });
        return response.data;
    }
    async logout() {
        await this.client.post('/api/v1/auth/logout');
        localStorage.removeItem('lucid_auth_token');
    }
    async verifyToken(token) {
        const response = await this.client.post('/api/v1/auth/verify', { token });
        return response.data;
    }
    // Admin API methods
    async getSystemHealth() {
        const response = await this.client.get('/api/v1/admin/system/health');
        return response.data;
    }
    async getAllUsers() {
        const response = await this.client.get('/api/v1/admin/users');
        return response.data;
    }
    async getAllSessions() {
        const response = await this.client.get('/api/v1/admin/sessions');
        return response.data;
    }
    async getAllNodes() {
        const response = await this.client.get('/api/v1/admin/nodes');
        return response.data;
    }
    // Proof verification API methods
    async verifySessionProof(sessionId) {
        const response = await this.client.post(`/api/v1/proofs/verify/${sessionId}`);
        return response.data.verified;
    }
    async getMerkleProof(chunkId) {
        const response = await this.client.get(`/api/v1/proofs/merkle/${chunkId}`);
        return response.data;
    }
    // TRON Payment API methods
    async getWalletBalance(address) {
        const response = await this.client.get(`/api/v1/tron/balance/${address}`);
        return response.data;
    }
    async transferUSDT(fromAddress, toAddress, amount) {
        const response = await this.client.post('/api/v1/tron/transfer', {
            from_address: fromAddress,
            to_address: toAddress,
            amount,
        });
        return response.data.transaction_hash;
    }
}
exports.LucidAPIClient = LucidAPIClient;
