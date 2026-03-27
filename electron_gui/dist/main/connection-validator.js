"use strict";
/**
 * LUCID Connection Validator - SPEC-1B Implementation
 * Validates connectivity to Docker services by phase
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ConnectionValidator = void 0;
const axios_1 = __importDefault(require("axios"));
const socks_proxy_agent_1 = require("socks-proxy-agent");
const constants_1 = require("../shared/constants");
class ConnectionValidator {
    constructor() {
        this.torProxy = 'socks5://127.0.0.1:9050';
        this.timeout = 5000;
        // Constructor for future configuration options
    }
    /**
     * Validate Phase 1 - Foundation Services
     * Tests: MongoDB, Redis, Elasticsearch, Auth Service
     */
    async validatePhase1() {
        const phase = 'foundation';
        const services = [
            { name: 'MongoDB', endpoint: constants_1.API_ENDPOINTS.MONGODB },
            { name: 'Redis', endpoint: constants_1.API_ENDPOINTS.REDIS },
            { name: 'Elasticsearch', endpoint: constants_1.API_ENDPOINTS.ELASTICSEARCH },
            { name: 'Auth Service', endpoint: constants_1.API_ENDPOINTS.AUTH }
        ];
        return await this.validateServices(phase, services);
    }
    /**
     * Validate Phase 2 - Core Services
     * Tests: API Gateway, Blockchain Engine, Service Mesh, Session Anchoring
     */
    async validatePhase2() {
        const phase = 'core';
        const services = [
            { name: 'API Gateway', endpoint: constants_1.API_ENDPOINTS.API_GATEWAY },
            { name: 'Blockchain Engine', endpoint: constants_1.API_ENDPOINTS.BLOCKCHAIN_ENGINE },
            { name: 'Service Mesh', endpoint: constants_1.API_ENDPOINTS.SERVICE_MESH },
            { name: 'Session Anchoring', endpoint: constants_1.API_ENDPOINTS.SESSION_ANCHORING },
            { name: 'Block Manager', endpoint: constants_1.API_ENDPOINTS.BLOCK_MANAGER },
            { name: 'Data Chain', endpoint: constants_1.API_ENDPOINTS.DATA_CHAIN }
        ];
        return await this.validateServices(phase, services);
    }
    /**
     * Validate Phase 3 - Application Services
     * Tests: Session API, RDP Server, Session Controller, Resource Monitor, Node Management
     */
    async validatePhase3() {
        const phase = 'application';
        const services = [
            { name: 'Session API', endpoint: constants_1.API_ENDPOINTS.SESSION_API },
            { name: 'RDP Server', endpoint: constants_1.API_ENDPOINTS.RDP_SERVER },
            { name: 'Session Controller', endpoint: constants_1.API_ENDPOINTS.SESSION_CONTROLLER },
            { name: 'Resource Monitor', endpoint: constants_1.API_ENDPOINTS.RESOURCE_MONITOR },
            { name: 'Node Management', endpoint: constants_1.API_ENDPOINTS.NODE_MANAGEMENT }
        ];
        return await this.validateServices(phase, services);
    }
    /**
     * Validate Phase 4 - Support Services
     * Tests: Admin Interface, TRON Payment Services
     */
    async validatePhase4() {
        const phase = 'support';
        const services = [
            { name: 'Admin Interface', endpoint: constants_1.API_ENDPOINTS.ADMIN },
            { name: 'TRON Client', endpoint: constants_1.API_ENDPOINTS.TRON_CLIENT },
            { name: 'Payout Router', endpoint: constants_1.API_ENDPOINTS.PAYOUT_ROUTER },
            { name: 'Wallet Manager', endpoint: constants_1.API_ENDPOINTS.WALLET_MANAGER },
            { name: 'USDT Manager', endpoint: constants_1.API_ENDPOINTS.USDT_MANAGER },
            { name: 'TRX Staking', endpoint: constants_1.API_ENDPOINTS.TRX_STAKING },
            { name: 'Payment Gateway', endpoint: constants_1.API_ENDPOINTS.PAYMENT_GATEWAY }
        ];
        return await this.validateServices(phase, services);
    }
    /**
     * Validate all phases
     */
    async validateAllPhases() {
        const results = await Promise.all([
            this.validatePhase1(),
            this.validatePhase2(),
            this.validatePhase3(),
            this.validatePhase4()
        ]);
        return results;
    }
    /**
     * Validate specific service endpoint
     */
    async validateService(name, endpoint) {
        const startTime = Date.now();
        try {
            const agent = new socks_proxy_agent_1.SocksProxyAgent(this.torProxy);
            const response = await axios_1.default.get(`${endpoint}/health`, {
                httpAgent: agent,
                httpsAgent: agent,
                timeout: this.timeout,
                headers: {
                    'User-Agent': 'Lucid-Electron-GUI/1.0.0'
                }
            });
            const responseTime = Date.now() - startTime;
            if (response.status >= 200 && response.status < 300) {
                return {
                    name,
                    endpoint,
                    status: 'connected',
                    responseTime
                };
            }
            else {
                return {
                    name,
                    endpoint,
                    status: 'failed',
                    error: `HTTP ${response.status}: ${response.statusText}`
                };
            }
        }
        catch (error) {
            const responseTime = Date.now() - startTime;
            if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
                return {
                    name,
                    endpoint,
                    status: 'timeout',
                    error: 'Connection timeout'
                };
            }
            else if (error.code === 'ECONNREFUSED') {
                return {
                    name,
                    endpoint,
                    status: 'failed',
                    error: 'Connection refused'
                };
            }
            else {
                return {
                    name,
                    endpoint,
                    status: 'failed',
                    error: error.message || 'Unknown error'
                };
            }
        }
    }
    /**
     * Validate multiple services
     */
    async validateServices(phase, services) {
        const serviceResults = await Promise.all(services.map(service => this.validateService(service.name, service.endpoint)));
        const connectedServices = serviceResults.filter(result => result.status === 'connected').length;
        const success = connectedServices === services.length;
        return {
            phase,
            success,
            services: serviceResults,
            timestamp: new Date().toISOString(),
            totalServices: services.length,
            connectedServices
        };
    }
    /**
     * Check if Tor proxy is available
     */
    async validateTorConnection() {
        try {
            const agent = new socks_proxy_agent_1.SocksProxyAgent(this.torProxy);
            const response = await axios_1.default.get('https://httpbin.org/ip', {
                httpAgent: agent,
                httpsAgent: agent,
                timeout: 10000
            });
            return response.status === 200;
        }
        catch (error) {
            console.error('Tor connection validation failed:', error);
            return false;
        }
    }
    /**
     * Get connection summary for all phases
     */
    async getConnectionSummary() {
        const torConnected = await this.validateTorConnection();
        const phases = await this.validateAllPhases();
        const totalServices = phases.reduce((sum, phase) => sum + phase.totalServices, 0);
        const connectedServices = phases.reduce((sum, phase) => sum + phase.connectedServices, 0);
        let overallHealth;
        if (connectedServices === totalServices && torConnected) {
            overallHealth = 'healthy';
        }
        else if (connectedServices >= totalServices * 0.7 && torConnected) {
            overallHealth = 'degraded';
        }
        else {
            overallHealth = 'critical';
        }
        return {
            torConnected,
            phases,
            overallHealth,
            totalServices,
            connectedServices
        };
    }
    /**
     * Set timeout for validation requests
     */
    setTimeout(timeout) {
        this.timeout = timeout;
    }
    /**
     * Set Tor proxy URL
     */
    setTorProxy(proxyUrl) {
        this.torProxy = proxyUrl;
    }
}
exports.ConnectionValidator = ConnectionValidator;
