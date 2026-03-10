import React, { useState, useEffect } from 'react';
import { APIEndpointCard } from '../components/APIEndpointCard';
import { RequestBuilder } from '../components/RequestBuilder';
import { ResponseViewer } from '../components/ResponseViewer';
import { useApi } from '../../common/hooks/useApi';

interface APIEndpoint {
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

interface APIRequest {
  method: string;
  url: string;
  headers: Record<string, string>;
  body?: any;
  params?: Record<string, string>;
}

interface APIResponse {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  data: any;
  duration: number;
  timestamp: string;
}

const APIExplorerPage: React.FC = () => {
  const [endpoints, setEndpoints] = useState<APIEndpoint[]>([]);
  const [selectedEndpoint, setSelectedEndpoint] = useState<APIEndpoint | null>(null);
  const [currentRequest, setCurrentRequest] = useState<APIRequest | null>(null);
  const [response, setResponse] = useState<APIResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const { apiClient } = useApi();

  useEffect(() => {
    loadAPIEndpoints();
  }, []);

  const loadAPIEndpoints = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load API endpoints from the system
      const endpoints = await loadEndpointsFromSystem();
      setEndpoints(endpoints);
    } catch (error) {
      console.error('Failed to load API endpoints:', error);
      setError('Failed to load API endpoints');
    } finally {
      setIsLoading(false);
    }
  };

  const loadEndpointsFromSystem = async (): Promise<APIEndpoint[]> => {
    // Mock API endpoints - in real implementation, these would come from the API
    return [
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
      }
    ];
  };

  const handleEndpointSelect = (endpoint: APIEndpoint) => {
    setSelectedEndpoint(endpoint);
    setCurrentRequest({
      method: endpoint.method,
      url: endpoint.path,
      headers: {
        'Content-Type': 'application/json'
      },
      params: {}
    });
    setResponse(null);
  };

  const handleRequestChange = (request: APIRequest) => {
    setCurrentRequest(request);
  };

  const handleSendRequest = async () => {
    if (!currentRequest) return;

    try {
      setIsLoading(true);
      setError(null);

      const startTime = Date.now();
      
      // Send the request using the API client
      const apiResponse = await apiClient.request({
        method: currentRequest.method,
        url: currentRequest.url,
        headers: currentRequest.headers,
        data: currentRequest.body,
        params: currentRequest.params
      });

      const duration = Date.now() - startTime;

      setResponse({
        status: apiResponse.status,
        statusText: apiResponse.statusText,
        headers: apiResponse.headers,
        data: apiResponse.data,
        duration,
        timestamp: new Date().toISOString()
      });
    } catch (error: any) {
      console.error('Request failed:', error);
      setError(error.message || 'Request failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearResponse = () => {
    setResponse(null);
    setError(null);
  };

  const filteredEndpoints = endpoints.filter(endpoint => {
    const matchesSearch = endpoint.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         endpoint.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         endpoint.path.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || endpoint.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const categories = ['all', ...Array.from(new Set(endpoints.map(e => e.category)))];

  return (
    <div className="developer-content">
      <div className="developer-card">
        <div className="developer-card-header">
          <div>
            <h2 className="developer-card-title">API Explorer</h2>
            <p className="developer-card-subtitle">
              Explore and test API endpoints
            </p>
          </div>
          <div className="developer-card-actions">
            <button 
              className="developer-btn developer-btn-secondary"
              onClick={loadAPIEndpoints}
              disabled={isLoading}
            >
              Refresh
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
          <div>
            <div className="developer-form-group">
              <label className="developer-form-label">Search Endpoints</label>
              <input
                type="text"
                className="developer-form-input"
                placeholder="Search by name, description, or path..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
          <div>
            <div className="developer-form-group">
              <label className="developer-form-label">Category</label>
              <select
                className="developer-form-input"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                {categories.map(category => (
                  <option key={category} value={category}>
                    {category === 'all' ? 'All Categories' : category}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {isLoading && (
          <div className="developer-loading">
            <div className="developer-loading-spinner"></div>
            <p>Loading API endpoints...</p>
          </div>
        )}

        {error && (
          <div className="developer-error">
            <div className="developer-error-icon">⚠️</div>
            <div className="developer-error-title">Error</div>
            <div className="developer-error-message">{error}</div>
            <button 
              className="developer-btn developer-btn-primary"
              onClick={loadAPIEndpoints}
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !error && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
            <div>
              <h3 style={{ marginBottom: '1rem', color: '#f8fafc' }}>Available Endpoints</h3>
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {filteredEndpoints.map(endpoint => (
                  <APIEndpointCard
                    key={endpoint.id}
                    endpoint={endpoint}
                    isSelected={selectedEndpoint?.id === endpoint.id}
                    onSelect={() => handleEndpointSelect(endpoint)}
                  />
                ))}
              </div>
            </div>

            <div>
              {selectedEndpoint && currentRequest && (
                <>
                  <h3 style={{ marginBottom: '1rem', color: '#f8fafc' }}>Request Builder</h3>
                  <RequestBuilder
                    endpoint={selectedEndpoint}
                    request={currentRequest}
                    onChange={handleRequestChange}
                    onSend={handleSendRequest}
                    isLoading={isLoading}
                  />
                </>
              )}

              {response && (
                <>
                  <h3 style={{ marginBottom: '1rem', color: '#f8fafc' }}>Response</h3>
                  <ResponseViewer
                    response={response}
                    onClear={handleClearResponse}
                  />
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export { APIExplorerPage };
