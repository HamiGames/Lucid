import { LucidAPIClient } from '../../../shared/api-client';

export interface APIEndpoint {
  id: string;
  name: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  path: string;
  description: string;
  parameters?: Array<{
    name: string;
    type: string;
    required: boolean;
    description: string;
  }>;
  responses?: Array<{
    status: number;
    description: string;
    schema?: any;
  }>;
  category: string;
  tags: string[];
}

export interface APIRequest {
  method: string;
  url: string;
  headers: Record<string, string>;
  body?: any;
  params?: Record<string, string>;
}

export interface APIResponse {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  data: any;
  duration: number;
  timestamp: string;
}

export interface APIRequestHistory {
  id: string;
  request: APIRequest;
  response: APIResponse;
  timestamp: string;
  name?: string;
}

class APIService {
  private apiClient: LucidAPIClient;
  private requestHistory: APIRequestHistory[] = [];
  private endpointsCache: APIEndpoint[] = [];
  private lastEndpointsUpdate: number = 0;
  private readonly CACHE_DURATION = 300000; // 5 minutes

  constructor() {
    this.apiClient = new LucidAPIClient();
  }

  async getAPIEndpoints(forceRefresh: boolean = false): Promise<APIEndpoint[]> {
    const now = Date.now();
    
    if (!forceRefresh && this.endpointsCache.length > 0 && (now - this.lastEndpointsUpdate) < this.CACHE_DURATION) {
      return this.endpointsCache;
    }

    try {
      // Load API endpoints from the system
      const endpoints = await this.loadEndpointsFromSystem();
      this.endpointsCache = endpoints;
      this.lastEndpointsUpdate = now;
      return endpoints;
    } catch (error) {
      console.error('Failed to load API endpoints:', error);
      throw new Error('Failed to load API endpoints');
    }
  }

  private async loadEndpointsFromSystem(): Promise<APIEndpoint[]> {
    // Mock API endpoints - in real implementation, these would come from the API
    const mockEndpoints: APIEndpoint[] = [
      {
        id: 'auth-login',
        name: 'User Login',
        method: 'POST',
        path: '/api/auth/login',
        description: 'Authenticate user with email and password',
        parameters: [
          {
            name: 'email',
            type: 'string',
            required: true,
            description: 'User email address'
          },
          {
            name: 'password',
            type: 'string',
            required: true,
            description: 'User password'
          }
        ],
        responses: [
          {
            status: 200,
            description: 'Login successful',
            schema: {
              type: 'object',
              properties: {
                token: { type: 'string' },
                user: { type: 'object' }
              }
            }
          },
          {
            status: 401,
            description: 'Invalid credentials'
          }
        ],
        category: 'Authentication',
        tags: ['auth', 'login', 'user']
      },
      {
        id: 'auth-logout',
        name: 'User Logout',
        method: 'POST',
        path: '/api/auth/logout',
        description: 'Logout user and invalidate token',
        responses: [
          {
            status: 200,
            description: 'Logout successful'
          }
        ],
        category: 'Authentication',
        tags: ['auth', 'logout', 'user']
      },
      {
        id: 'sessions-list',
        name: 'List Sessions',
        method: 'GET',
        path: '/api/sessions',
        description: 'Get list of user sessions',
        parameters: [
          {
            name: 'limit',
            type: 'number',
            required: false,
            description: 'Number of sessions to return'
          },
          {
            name: 'offset',
            type: 'number',
            required: false,
            description: 'Number of sessions to skip'
          }
        ],
        responses: [
          {
            status: 200,
            description: 'Sessions retrieved successfully',
            schema: {
              type: 'array',
              items: { type: 'object' }
            }
          }
        ],
        category: 'Sessions',
        tags: ['sessions', 'list', 'user']
      },
      {
        id: 'sessions-create',
        name: 'Create Session',
        method: 'POST',
        path: '/api/sessions',
        description: 'Create a new session',
        parameters: [
          {
            name: 'data',
            type: 'string',
            required: true,
            description: 'Encrypted session data'
          },
          {
            name: 'metadata',
            type: 'object',
            required: false,
            description: 'Session metadata'
          }
        ],
        responses: [
          {
            status: 201,
            description: 'Session created successfully'
          }
        ],
        category: 'Sessions',
        tags: ['sessions', 'create', 'user']
      },
      {
        id: 'nodes-status',
        name: 'Node Status',
        method: 'GET',
        path: '/api/nodes/status',
        description: 'Get status of all nodes',
        responses: [
          {
            status: 200,
            description: 'Node status retrieved successfully'
          }
        ],
        category: 'Nodes',
        tags: ['nodes', 'status', 'monitoring']
      },
      {
        id: 'blockchain-status',
        name: 'Blockchain Status',
        method: 'GET',
        path: '/api/blockchain/status',
        description: 'Get blockchain network status',
        responses: [
          {
            status: 200,
            description: 'Blockchain status retrieved successfully'
          }
        ],
        category: 'Blockchain',
        tags: ['blockchain', 'status', 'network']
      }
    ];

    return mockEndpoints;
  }

  async sendRequest(request: APIRequest): Promise<APIResponse> {
    const startTime = Date.now();
    
    try {
      // Send the request using the API client
      const response = await this.apiClient.request({
        method: request.method as any,
        url: request.url,
        headers: request.headers,
        data: request.body,
        params: request.params
      });

      const duration = Date.now() - startTime;

      const apiResponse: APIResponse = {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        data: response.data,
        duration,
        timestamp: new Date().toISOString()
      };

      // Save to history
      this.addToHistory({
        id: `req-${Date.now()}`,
        request,
        response: apiResponse,
        timestamp: new Date().toISOString()
      });

      return apiResponse;
    } catch (error: any) {
      const duration = Date.now() - startTime;
      
      // Create error response
      const errorResponse: APIResponse = {
        status: error.status || 500,
        statusText: error.statusText || 'Internal Server Error',
        headers: error.headers || {},
        data: error.data || { error: error.message },
        duration,
        timestamp: new Date().toISOString()
      };

      // Save to history
      this.addToHistory({
        id: `req-${Date.now()}`,
        request,
        response: errorResponse,
        timestamp: new Date().toISOString()
      });

      throw error;
    }
  }

  private addToHistory(historyItem: APIRequestHistory): void {
    this.requestHistory.unshift(historyItem);
    
    // Keep only last 100 requests
    if (this.requestHistory.length > 100) {
      this.requestHistory = this.requestHistory.slice(0, 100);
    }
  }

  getRequestHistory(): APIRequestHistory[] {
    return [...this.requestHistory];
  }

  getRequestHistoryById(id: string): APIRequestHistory | null {
    return this.requestHistory.find(item => item.id === id) || null;
  }

  clearRequestHistory(): void {
    this.requestHistory = [];
  }

  saveRequestToHistory(historyItem: APIRequestHistory): void {
    this.addToHistory(historyItem);
  }

  updateRequestHistoryName(id: string, name: string): void {
    const item = this.requestHistory.find(item => item.id === id);
    if (item) {
      item.name = name;
    }
  }

  deleteRequestFromHistory(id: string): void {
    this.requestHistory = this.requestHistory.filter(item => item.id !== id);
  }

  exportRequestHistory(): string {
    return JSON.stringify(this.requestHistory, null, 2);
  }

  importRequestHistory(data: string): void {
    try {
      const imported = JSON.parse(data);
      if (Array.isArray(imported)) {
        this.requestHistory = imported;
      }
    } catch (error) {
      throw new Error('Invalid request history data');
    }
  }

  clearEndpointsCache(): void {
    this.endpointsCache = [];
    this.lastEndpointsUpdate = 0;
  }

  async testEndpoint(endpoint: APIEndpoint, request: APIRequest): Promise<APIResponse> {
    return this.sendRequest(request);
  }

  async validateRequest(request: APIRequest): Promise<{
    isValid: boolean;
    errors: string[];
  }> {
    const errors: string[] = [];

    // Validate method
    if (!request.method) {
      errors.push('Method is required');
    }

    // Validate URL
    if (!request.url) {
      errors.push('URL is required');
    } else {
      try {
        new URL(request.url);
      } catch {
        errors.push('Invalid URL format');
      }
    }

    // Validate headers
    if (request.headers) {
      for (const [key, value] of Object.entries(request.headers)) {
        if (!key.trim()) {
          errors.push('Header key cannot be empty');
        }
        if (!value.trim()) {
          errors.push(`Header value for "${key}" cannot be empty`);
        }
      }
    }

    // Validate body for POST/PUT/PATCH
    if (['POST', 'PUT', 'PATCH'].includes(request.method)) {
      if (request.body && typeof request.body === 'string') {
        try {
          JSON.parse(request.body);
        } catch {
          errors.push('Invalid JSON in request body');
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }
}

export const apiService = new APIService();
