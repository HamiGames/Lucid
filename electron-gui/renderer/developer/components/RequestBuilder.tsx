import React, { useState, useEffect } from 'react';

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

interface RequestBuilderProps {
  endpoint: APIEndpoint;
  request: APIRequest;
  onChange: (request: APIRequest) => void;
  onSend: () => void;
  isLoading?: boolean;
  className?: string;
}

export const RequestBuilder: React.FC<RequestBuilderProps> = ({
  endpoint,
  request,
  onChange,
  onSend,
  isLoading = false,
  className = ''
}) => {
  const [headers, setHeaders] = useState<Array<{ key: string; value: string }>>([]);
  const [params, setParams] = useState<Array<{ key: string; value: string }>>([]);
  const [bodyText, setBodyText] = useState<string>('');
  const [bodyType, setBodyType] = useState<'json' | 'form' | 'raw'>('json');

  useEffect(() => {
    // Initialize headers from request
    const headerArray = Object.entries(request.headers || {}).map(([key, value]) => ({ key, value }));
    setHeaders(headerArray);

    // Initialize params from request
    const paramArray = Object.entries(request.params || {}).map(([key, value]) => ({ key, value }));
    setParams(paramArray);

    // Initialize body
    if (request.body) {
      if (typeof request.body === 'string') {
        setBodyText(request.body);
        setBodyType('raw');
      } else {
        setBodyText(JSON.stringify(request.body, null, 2));
        setBodyType('json');
      }
    }
  }, [request]);

  const handleMethodChange = (method: string) => {
    const newRequest = { ...request, method };
    onChange(newRequest);
  };

  const handleUrlChange = (url: string) => {
    const newRequest = { ...request, url };
    onChange(newRequest);
  };

  const handleHeaderChange = (index: number, key: string, value: string) => {
    const newHeaders = [...headers];
    newHeaders[index] = { key, value };
    setHeaders(newHeaders);

    const headersObj = newHeaders.reduce((acc, { key, value }) => {
      if (key.trim()) {
        acc[key.trim()] = value;
      }
      return acc;
    }, {} as Record<string, string>);

    const newRequest = { ...request, headers: headersObj };
    onChange(newRequest);
  };

  const handleHeaderAdd = () => {
    setHeaders([...headers, { key: '', value: '' }]);
  };

  const handleHeaderRemove = (index: number) => {
    const newHeaders = headers.filter((_, i) => i !== index);
    setHeaders(newHeaders);

    const headersObj = newHeaders.reduce((acc, { key, value }) => {
      if (key.trim()) {
        acc[key.trim()] = value;
      }
      return acc;
    }, {} as Record<string, string>);

    const newRequest = { ...request, headers: headersObj };
    onChange(newRequest);
  };

  const handleParamChange = (index: number, key: string, value: string) => {
    const newParams = [...params];
    newParams[index] = { key, value };
    setParams(newParams);

    const paramsObj = newParams.reduce((acc, { key, value }) => {
      if (key.trim()) {
        acc[key.trim()] = value;
      }
      return acc;
    }, {} as Record<string, string>);

    const newRequest = { ...request, params: paramsObj };
    onChange(newRequest);
  };

  const handleParamAdd = () => {
    setParams([...params, { key: '', value: '' }]);
  };

  const handleParamRemove = (index: number) => {
    const newParams = params.filter((_, i) => i !== index);
    setParams(newParams);

    const paramsObj = newParams.reduce((acc, { key, value }) => {
      if (key.trim()) {
        acc[key.trim()] = value;
      }
      return acc;
    }, {} as Record<string, string>);

    const newRequest = { ...request, params: paramsObj };
    onChange(newRequest);
  };

  const handleBodyChange = (text: string) => {
    setBodyText(text);

    let body: any = text;
    if (bodyType === 'json') {
      try {
        body = JSON.parse(text);
      } catch (e) {
        // Invalid JSON, keep as string
      }
    }

    const newRequest = { ...request, body };
    onChange(newRequest);
  };

  const handleBodyTypeChange = (type: 'json' | 'form' | 'raw') => {
    setBodyType(type);
    
    let body: any = bodyText;
    if (type === 'json') {
      try {
        body = JSON.parse(bodyText);
      } catch (e) {
        // Invalid JSON, keep as string
      }
    }

    const newRequest = { ...request, body };
    onChange(newRequest);
  };

  const handleSend = () => {
    onSend();
  };

  const getMethodColor = (method: string): string => {
    switch (method) {
      case 'GET': return '#10b981';
      case 'POST': return '#3b82f6';
      case 'PUT': return '#f59e0b';
      case 'DELETE': return '#ef4444';
      case 'PATCH': return '#8b5cf6';
      default: return '#6b7280';
    }
  };

  const isJsonValid = (text: string): boolean => {
    if (bodyType !== 'json') return true;
    try {
      JSON.parse(text);
      return true;
    } catch {
      return false;
    }
  };

  return (
    <div className={`request-builder ${className}`} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Method and URL */}
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <select
          value={request.method}
          onChange={(e) => handleMethodChange(e.target.value)}
          style={{
            padding: '0.5rem',
            border: '1px solid rgba(51, 65, 85, 0.3)',
            borderRadius: '0.25rem',
            background: 'rgba(15, 23, 42, 0.5)',
            color: '#f8fafc',
            fontSize: '0.875rem',
            fontWeight: '600',
            textTransform: 'uppercase',
            minWidth: '80px'
          }}
        >
          <option value="GET">GET</option>
          <option value="POST">POST</option>
          <option value="PUT">PUT</option>
          <option value="DELETE">DELETE</option>
          <option value="PATCH">PATCH</option>
        </select>
        
        <input
          type="text"
          value={request.url}
          onChange={(e) => handleUrlChange(e.target.value)}
          placeholder="Enter URL..."
          style={{
            flex: 1,
            padding: '0.5rem',
            border: '1px solid rgba(51, 65, 85, 0.3)',
            borderRadius: '0.25rem',
            background: 'rgba(15, 23, 42, 0.5)',
            color: '#f8fafc',
            fontSize: '0.875rem'
          }}
        />
        
        <button
          onClick={handleSend}
          disabled={isLoading}
          style={{
            padding: '0.5rem 1rem',
            background: isLoading ? '#6b7280' : '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '0.25rem',
            fontSize: '0.875rem',
            fontWeight: '500',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.2s'
          }}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>

      {/* Headers */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <label style={{ color: '#d1d5db', fontSize: '0.875rem', fontWeight: '500' }}>Headers</label>
          <button
            onClick={handleHeaderAdd}
            style={{
              background: 'transparent',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              color: '#60a5fa',
              padding: '0.25rem 0.5rem',
              borderRadius: '0.25rem',
              fontSize: '0.75rem',
              cursor: 'pointer'
            }}
          >
            + Add Header
          </button>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {headers.map((header, index) => (
            <div key={index} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="Header name"
                value={header.key}
                onChange={(e) => handleHeaderChange(index, e.target.value, header.value)}
                style={{
                  flex: 1,
                  padding: '0.5rem',
                  border: '1px solid rgba(51, 65, 85, 0.3)',
                  borderRadius: '0.25rem',
                  background: 'rgba(15, 23, 42, 0.5)',
                  color: '#f8fafc',
                  fontSize: '0.875rem'
                }}
              />
              <input
                type="text"
                placeholder="Header value"
                value={header.value}
                onChange={(e) => handleHeaderChange(index, header.key, e.target.value)}
                style={{
                  flex: 1,
                  padding: '0.5rem',
                  border: '1px solid rgba(51, 65, 85, 0.3)',
                  borderRadius: '0.25rem',
                  background: 'rgba(15, 23, 42, 0.5)',
                  color: '#f8fafc',
                  fontSize: '0.875rem'
                }}
              />
              <button
                onClick={() => handleHeaderRemove(index)}
                style={{
                  background: 'transparent',
                  border: '1px solid #ef4444',
                  color: '#ef4444',
                  padding: '0.5rem',
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                  fontSize: '0.75rem'
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Query Parameters */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <label style={{ color: '#d1d5db', fontSize: '0.875rem', fontWeight: '500' }}>Query Parameters</label>
          <button
            onClick={handleParamAdd}
            style={{
              background: 'transparent',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              color: '#60a5fa',
              padding: '0.25rem 0.5rem',
              borderRadius: '0.25rem',
              fontSize: '0.75rem',
              cursor: 'pointer'
            }}
          >
            + Add Parameter
          </button>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {params.map((param, index) => (
            <div key={index} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="Parameter name"
                value={param.key}
                onChange={(e) => handleParamChange(index, e.target.value, param.value)}
                style={{
                  flex: 1,
                  padding: '0.5rem',
                  border: '1px solid rgba(51, 65, 85, 0.3)',
                  borderRadius: '0.25rem',
                  background: 'rgba(15, 23, 42, 0.5)',
                  color: '#f8fafc',
                  fontSize: '0.875rem'
                }}
              />
              <input
                type="text"
                placeholder="Parameter value"
                value={param.value}
                onChange={(e) => handleParamChange(index, param.key, e.target.value)}
                style={{
                  flex: 1,
                  padding: '0.5rem',
                  border: '1px solid rgba(51, 65, 85, 0.3)',
                  borderRadius: '0.25rem',
                  background: 'rgba(15, 23, 42, 0.5)',
                  color: '#f8fafc',
                  fontSize: '0.875rem'
                }}
              />
              <button
                onClick={() => handleParamRemove(index)}
                style={{
                  background: 'transparent',
                  border: '1px solid #ef4444',
                  color: '#ef4444',
                  padding: '0.5rem',
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                  fontSize: '0.75rem'
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Request Body */}
      {(request.method === 'POST' || request.method === 'PUT' || request.method === 'PATCH') && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <label style={{ color: '#d1d5db', fontSize: '0.875rem', fontWeight: '500' }}>Request Body</label>
            <select
              value={bodyType}
              onChange={(e) => handleBodyTypeChange(e.target.value as 'json' | 'form' | 'raw')}
              style={{
                padding: '0.25rem 0.5rem',
                border: '1px solid rgba(51, 65, 85, 0.3)',
                borderRadius: '0.25rem',
                background: 'rgba(15, 23, 42, 0.5)',
                color: '#f8fafc',
                fontSize: '0.75rem'
              }}
            >
              <option value="json">JSON</option>
              <option value="form">Form Data</option>
              <option value="raw">Raw</option>
            </select>
          </div>
          
          <textarea
            value={bodyText}
            onChange={(e) => handleBodyChange(e.target.value)}
            placeholder={bodyType === 'json' ? 'Enter JSON...' : 'Enter request body...'}
            style={{
              width: '100%',
              height: '120px',
              padding: '0.75rem',
              border: `1px solid ${isJsonValid(bodyText) ? 'rgba(51, 65, 85, 0.3)' : '#ef4444'}`,
              borderRadius: '0.25rem',
              background: 'rgba(15, 23, 42, 0.5)',
              color: '#f8fafc',
              fontSize: '0.875rem',
              fontFamily: bodyType === 'json' ? 'monospace' : 'inherit',
              resize: 'vertical'
            }}
          />
          
          {bodyType === 'json' && !isJsonValid(bodyText) && (
            <div style={{ color: '#ef4444', fontSize: '0.75rem', marginTop: '0.25rem' }}>
              Invalid JSON format
            </div>
          )}
        </div>
      )}

      {/* Endpoint Info */}
      <div style={{
        padding: '0.75rem',
        background: 'rgba(30, 41, 59, 0.5)',
        borderRadius: '0.5rem',
        border: '1px solid rgba(51, 65, 85, 0.3)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Endpoint:</span>
          <span style={{ 
            color: getMethodColor(endpoint.method),
            fontSize: '0.75rem',
            fontWeight: '600',
            textTransform: 'uppercase'
          }}>
            {endpoint.method}
          </span>
          <code style={{ 
            color: '#60a5fa',
            fontSize: '0.75rem',
            background: 'rgba(59, 130, 246, 0.2)',
            padding: '0.125rem 0.25rem',
            borderRadius: '0.125rem'
          }}>
            {endpoint.path}
          </code>
        </div>
        <p style={{ margin: '0', color: '#94a3b8', fontSize: '0.75rem' }}>
          {endpoint.description}
        </p>
      </div>
    </div>
  );
};
