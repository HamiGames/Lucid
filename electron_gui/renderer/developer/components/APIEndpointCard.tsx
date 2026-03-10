import React from 'react';

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

interface APIEndpointCardProps {
  endpoint: APIEndpoint;
  isSelected?: boolean;
  onSelect?: () => void;
  onTest?: () => void;
  className?: string;
}

export const APIEndpointCard: React.FC<APIEndpointCardProps> = ({
  endpoint,
  isSelected = false,
  onSelect,
  onTest,
  className = ''
}) => {
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

  const getMethodIcon = (method: string): string => {
    switch (method) {
      case 'GET': return '📥';
      case 'POST': return '📤';
      case 'PUT': return '🔄';
      case 'DELETE': return '🗑️';
      case 'PATCH': return '🔧';
      default: return '❓';
    }
  };

  const handleCardClick = () => {
    onSelect?.();
  };

  const handleTestClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onTest?.();
  };

  return (
    <div
      className={`developer-card ${isSelected ? 'active' : ''} ${className}`}
      style={{
        padding: '1rem',
        marginBottom: '0.5rem',
        cursor: 'pointer',
        border: isSelected ? '2px solid #3b82f6' : '1px solid rgba(51, 65, 85, 0.3)',
        transition: 'all 0.2s ease'
      }}
      onClick={handleCardClick}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>{getMethodIcon(endpoint.method)}</span>
            <span
              style={{
                background: getMethodColor(endpoint.method),
                color: 'white',
                padding: '0.25rem 0.5rem',
                borderRadius: '0.25rem',
                fontSize: '0.75rem',
                fontWeight: '600',
                textTransform: 'uppercase'
              }}
            >
              {endpoint.method}
            </span>
            <h4 style={{ margin: '0', color: '#f8fafc', fontSize: '1rem' }}>{endpoint.name}</h4>
          </div>
          <p style={{ margin: '0 0 0.5rem 0', color: '#94a3b8', fontSize: '0.875rem' }}>
            {endpoint.description}
          </p>
          <code style={{ 
            background: 'rgba(30, 41, 59, 0.5)', 
            color: '#60a5fa', 
            padding: '0.25rem 0.5rem', 
            borderRadius: '0.25rem',
            fontSize: '0.75rem',
            fontFamily: 'monospace'
          }}>
            {endpoint.path}
          </code>
        </div>
        <button
          className="developer-btn developer-btn-primary"
          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
          onClick={handleTestClick}
        >
          Test
        </button>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ 
            fontSize: '0.75rem', 
            color: '#64748b',
            background: 'rgba(51, 65, 85, 0.3)',
            padding: '0.25rem 0.5rem',
            borderRadius: '0.25rem'
          }}>
            {endpoint.category}
          </span>
          {endpoint.tags.slice(0, 2).map(tag => (
            <span
              key={tag}
              style={{
                fontSize: '0.75rem',
                color: '#60a5fa',
                background: 'rgba(59, 130, 246, 0.2)',
                padding: '0.25rem 0.5rem',
                borderRadius: '0.25rem'
              }}
            >
              {tag}
            </span>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem', color: '#94a3b8' }}>
          {endpoint.parameters && (
            <span>📝 {endpoint.parameters.length} params</span>
          )}
          {endpoint.responses && (
            <span>📊 {endpoint.responses.length} responses</span>
          )}
        </div>
      </div>

      {endpoint.parameters && endpoint.parameters.length > 0 && (
        <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(51, 65, 85, 0.3)' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.5rem' }}>Parameters:</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {endpoint.parameters.slice(0, 3).map(param => (
              <span
                key={param.name}
                style={{
                  fontSize: '0.75rem',
                  color: param.required ? '#ef4444' : '#94a3b8',
                  background: param.required ? 'rgba(239, 68, 68, 0.2)' : 'rgba(51, 65, 85, 0.3)',
                  padding: '0.25rem 0.5rem',
                  borderRadius: '0.25rem',
                  border: param.required ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(51, 65, 85, 0.3)'
                }}
              >
                {param.name} ({param.type})
              </span>
            ))}
            {endpoint.parameters.length > 3 && (
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                +{endpoint.parameters.length - 3} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
