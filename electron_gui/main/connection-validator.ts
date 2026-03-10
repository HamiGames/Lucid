/**
 * LUCID Connection Validator - SPEC-1B Implementation
 * Validates connectivity to Docker services by phase
 */

import axios from 'axios';
import { SocksProxyAgent } from 'socks-proxy-agent';
import { API_ENDPOINTS } from '../shared/constants';

export interface ValidationResult {
  phase: string;
  success: boolean;
  services: Array<{
    name: string;
    endpoint: string;
    status: 'connected' | 'failed' | 'timeout';
    responseTime?: number;
    error?: string;
  }>;
  timestamp: string;
  totalServices: number;
  connectedServices: number;
}

export class ConnectionValidator {
  private torProxy: string = 'socks5://127.0.0.1:9050';
  private timeout: number = 5000;

  constructor() {
    // Constructor for future configuration options
  }

  /**
   * Validate Phase 1 - Foundation Services
   * Tests: MongoDB, Redis, Elasticsearch, Auth Service
   */
  async validatePhase1(): Promise<ValidationResult> {
    const phase = 'foundation';
    const services = [
      { name: 'MongoDB', endpoint: API_ENDPOINTS.MONGODB },
      { name: 'Redis', endpoint: API_ENDPOINTS.REDIS },
      { name: 'Elasticsearch', endpoint: API_ENDPOINTS.ELASTICSEARCH },
      { name: 'Auth Service', endpoint: API_ENDPOINTS.AUTH }
    ];

    return await this.validateServices(phase, services);
  }

  /**
   * Validate Phase 2 - Core Services
   * Tests: API Gateway, Blockchain Engine, Service Mesh, Session Anchoring
   */
  async validatePhase2(): Promise<ValidationResult> {
    const phase = 'core';
    const services = [
      { name: 'API Gateway', endpoint: API_ENDPOINTS.API_GATEWAY },
      { name: 'Blockchain Engine', endpoint: API_ENDPOINTS.BLOCKCHAIN_ENGINE },
      { name: 'Service Mesh', endpoint: API_ENDPOINTS.SERVICE_MESH },
      { name: 'Session Anchoring', endpoint: API_ENDPOINTS.SESSION_ANCHORING },
      { name: 'Block Manager', endpoint: API_ENDPOINTS.BLOCK_MANAGER },
      { name: 'Data Chain', endpoint: API_ENDPOINTS.DATA_CHAIN }
    ];

    return await this.validateServices(phase, services);
  }

  /**
   * Validate Phase 3 - Application Services
   * Tests: Session API, RDP Server, Session Controller, Resource Monitor, Node Management
   */
  async validatePhase3(): Promise<ValidationResult> {
    const phase = 'application';
    const services = [
      { name: 'Session API', endpoint: API_ENDPOINTS.SESSION_API },
      { name: 'RDP Server', endpoint: API_ENDPOINTS.RDP_SERVER },
      { name: 'Session Controller', endpoint: API_ENDPOINTS.SESSION_CONTROLLER },
      { name: 'Resource Monitor', endpoint: API_ENDPOINTS.RESOURCE_MONITOR },
      { name: 'Node Management', endpoint: API_ENDPOINTS.NODE_MANAGEMENT }
    ];

    return await this.validateServices(phase, services);
  }

  /**
   * Validate Phase 4 - Support Services
   * Tests: Admin Interface, TRON Payment Services
   */
  async validatePhase4(): Promise<ValidationResult> {
    const phase = 'support';
    const services = [
      { name: 'Admin Interface', endpoint: API_ENDPOINTS.ADMIN },
      { name: 'TRON Client', endpoint: API_ENDPOINTS.TRON_CLIENT },
      { name: 'Payout Router', endpoint: API_ENDPOINTS.PAYOUT_ROUTER },
      { name: 'Wallet Manager', endpoint: API_ENDPOINTS.WALLET_MANAGER },
      { name: 'USDT Manager', endpoint: API_ENDPOINTS.USDT_MANAGER },
      { name: 'TRX Staking', endpoint: API_ENDPOINTS.TRX_STAKING },
      { name: 'Payment Gateway', endpoint: API_ENDPOINTS.PAYMENT_GATEWAY }
    ];

    return await this.validateServices(phase, services);
  }

  /**
   * Validate all phases
   */
  async validateAllPhases(): Promise<ValidationResult[]> {
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
  async validateService(name: string, endpoint: string): Promise<{
    name: string;
    endpoint: string;
    status: 'connected' | 'failed' | 'timeout';
    responseTime?: number;
    error?: string;
  }> {
    const startTime = Date.now();
    
    try {
      const agent = new SocksProxyAgent(this.torProxy);
      const response = await axios.get(`${endpoint}/health`, {
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
      } else {
        return {
          name,
          endpoint,
          status: 'failed',
          error: `HTTP ${response.status}: ${response.statusText}`
        };
      }
    } catch (error: any) {
      const responseTime = Date.now() - startTime;
      
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        return {
          name,
          endpoint,
          status: 'timeout',
          error: 'Connection timeout'
        };
      } else if (error.code === 'ECONNREFUSED') {
        return {
          name,
          endpoint,
          status: 'failed',
          error: 'Connection refused'
        };
      } else {
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
  private async validateServices(
    phase: string, 
    services: Array<{ name: string; endpoint: string }>
  ): Promise<ValidationResult> {
    const serviceResults = await Promise.all(
      services.map(service => this.validateService(service.name, service.endpoint))
    );

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
  async validateTorConnection(): Promise<boolean> {
    try {
      const agent = new SocksProxyAgent(this.torProxy);
      const response = await axios.get('https://httpbin.org/ip', {
        httpAgent: agent,
        httpsAgent: agent,
        timeout: 10000
      });

      return response.status === 200;
    } catch (error) {
      console.error('Tor connection validation failed:', error);
      return false;
    }
  }

  /**
   * Get connection summary for all phases
   */
  async getConnectionSummary(): Promise<{
    torConnected: boolean;
    phases: ValidationResult[];
    overallHealth: 'healthy' | 'degraded' | 'critical';
    totalServices: number;
    connectedServices: number;
  }> {
    const torConnected = await this.validateTorConnection();
    const phases = await this.validateAllPhases();
    
    const totalServices = phases.reduce((sum, phase) => sum + phase.totalServices, 0);
    const connectedServices = phases.reduce((sum, phase) => sum + phase.connectedServices, 0);
    
    let overallHealth: 'healthy' | 'degraded' | 'critical';
    if (connectedServices === totalServices && torConnected) {
      overallHealth = 'healthy';
    } else if (connectedServices >= totalServices * 0.7 && torConnected) {
      overallHealth = 'degraded';
    } else {
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
  setTimeout(timeout: number): void {
    this.timeout = timeout;
  }

  /**
   * Set Tor proxy URL
   */
  setTorProxy(proxyUrl: string): void {
    this.torProxy = proxyUrl;
  }
}
