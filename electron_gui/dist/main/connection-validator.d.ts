/**
 * LUCID Connection Validator - SPEC-1B Implementation
 * Validates connectivity to Docker services by phase
 */
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
export declare class ConnectionValidator {
    private torProxy;
    private timeout;
    constructor();
    /**
     * Validate Phase 1 - Foundation Services
     * Tests: MongoDB, Redis, Elasticsearch, Auth Service
     */
    validatePhase1(): Promise<ValidationResult>;
    /**
     * Validate Phase 2 - Core Services
     * Tests: API Gateway, Blockchain Engine, Service Mesh, Session Anchoring
     */
    validatePhase2(): Promise<ValidationResult>;
    /**
     * Validate Phase 3 - Application Services
     * Tests: Session API, RDP Server, Session Controller, Resource Monitor, Node Management
     */
    validatePhase3(): Promise<ValidationResult>;
    /**
     * Validate Phase 4 - Support Services
     * Tests: Admin Interface, TRON Payment Services
     */
    validatePhase4(): Promise<ValidationResult>;
    /**
     * Validate all phases
     */
    validateAllPhases(): Promise<ValidationResult[]>;
    /**
     * Validate specific service endpoint
     */
    validateService(name: string, endpoint: string): Promise<{
        name: string;
        endpoint: string;
        status: 'connected' | 'failed' | 'timeout';
        responseTime?: number;
        error?: string;
    }>;
    /**
     * Validate multiple services
     */
    private validateServices;
    /**
     * Check if Tor proxy is available
     */
    validateTorConnection(): Promise<boolean>;
    /**
     * Get connection summary for all phases
     */
    getConnectionSummary(): Promise<{
        torConnected: boolean;
        phases: ValidationResult[];
        overallHealth: 'healthy' | 'degraded' | 'critical';
        totalServices: number;
        connectedServices: number;
    }>;
    /**
     * Set timeout for validation requests
     */
    setTimeout(timeout: number): void;
    /**
     * Set Tor proxy URL
     */
    setTorProxy(proxyUrl: string): void;
}
