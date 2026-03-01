import React, { useState, useEffect } from 'react';

interface DocumentationSection {
  id: string;
  title: string;
  content: string;
  category: string;
  tags: string[];
  lastUpdated: string;
}

interface DocumentationFilters {
  category: string;
  search: string;
  tags: string[];
}

const DocumentationPage: React.FC = () => {
  const [sections, setSections] = useState<DocumentationSection[]>([]);
  const [selectedSection, setSelectedSection] = useState<DocumentationSection | null>(null);
  const [filters, setFilters] = useState<DocumentationFilters>({
    category: 'all',
    search: '',
    tags: []
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDocumentation();
  }, []);

  const loadDocumentation = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load documentation from the system
      const docs = await loadDocumentationFromSystem();
      setSections(docs);
      
      if (docs.length > 0) {
        setSelectedSection(docs[0]);
      }
    } catch (error) {
      console.error('Failed to load documentation:', error);
      setError('Failed to load documentation');
    } finally {
      setIsLoading(false);
    }
  };

  const loadDocumentationFromSystem = async (): Promise<DocumentationSection[]> => {
    // Mock documentation sections - in real implementation, these would come from the documentation service
    const mockDocs: DocumentationSection[] = [
      {
        id: 'api-overview',
        title: 'API Overview',
        content: `# API Overview

The Lucid API provides a comprehensive set of endpoints for managing sessions, users, nodes, and blockchain operations.

## Base URL
- Development: \`http://localhost:3000/api\`
- Production: \`https://api.lucid.network\`

## Authentication
All API requests require authentication using JWT tokens. Include the token in the Authorization header:

\`\`\`
Authorization: Bearer <your-token>
\`\`\`

## Rate Limiting
API requests are rate limited to 1000 requests per hour per user.

## Response Format
All API responses follow a consistent format:

\`\`\`json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully",
  "timestamp": "2024-01-01T00:00:00Z"
}
\`\`\``,
        category: 'API',
        tags: ['api', 'overview', 'authentication'],
        lastUpdated: '2024-01-01T00:00:00Z'
      },
      {
        id: 'session-management',
        title: 'Session Management',
        content: `# Session Management

Sessions are the core entity in the Lucid system, representing encrypted data storage and retrieval operations.

## Creating a Session

\`\`\`http
POST /api/sessions
Content-Type: application/json
Authorization: Bearer <token>

{
  "data": "encrypted-data",
  "metadata": {
    "description": "My session data"
  }
}
\`\`\`

## Retrieving a Session

\`\`\`http
GET /api/sessions/{sessionId}
Authorization: Bearer <token>
\`\`\`

## Session States
- \`active\`: Session is currently being used
- \`idle\`: Session is not being accessed
- \`terminated\`: Session has been closed
- \`anchored\`: Session has been anchored to blockchain

## Session Lifecycle
1. **Creation**: Session is created with encrypted data
2. **Active**: Session is being used by the client
3. **Idle**: Session is not being accessed
4. **Termination**: Session is closed by the client
5. **Anchoring**: Session is anchored to blockchain for permanence`,
        category: 'API',
        tags: ['sessions', 'api', 'lifecycle'],
        lastUpdated: '2024-01-01T00:00:00Z'
      },
      {
        id: 'node-operations',
        title: 'Node Operations',
        content: `# Node Operations

Nodes are the distributed computing resources that power the Lucid network.

## Node Registration

\`\`\`http
POST /api/nodes/register
Content-Type: application/json
Authorization: Bearer <token>

{
  "operator_id": "operator123",
  "resources": {
    "cpu_cores": 4,
    "memory_gb": 8,
    "disk_gb": 100,
    "network_speed_mbps": 1000
  },
  "location": {
    "country": "US",
    "region": "California"
  }
}
\`\`\`

## Node Status
Nodes can have the following statuses:
- \`registered\`: Node is registered but not active
- \`active\`: Node is active and processing sessions
- \`inactive\`: Node is not processing sessions
- \`suspended\`: Node is suspended by admin

## PoOT Score
The Proof of Operational Trust (PoOT) score determines a node's reliability and performance.`,
        category: 'API',
        tags: ['nodes', 'api', 'registration'],
        lastUpdated: '2024-01-01T00:00:00Z'
      },
      {
        id: 'blockchain-integration',
        title: 'Blockchain Integration',
        content: `# Blockchain Integration

Lucid integrates with blockchain networks to provide permanent data anchoring.

## Anchoring Process
1. Session data is hashed using Merkle trees
2. Hash is submitted to blockchain network
3. Transaction is confirmed and recorded
4. Session is marked as anchored

## Supported Networks
- TRON (Primary)
- Ethereum (Secondary)
- Bitcoin (Experimental)

## Anchoring API

\`\`\`http
POST /api/blockchain/anchor
Content-Type: application/json
Authorization: Bearer <token>

{
  "session_ids": ["session1", "session2"],
  "priority": "normal"
}
\`\`\``,
        category: 'Blockchain',
        tags: ['blockchain', 'anchoring', 'tron'],
        lastUpdated: '2024-01-01T00:00:00Z'
      },
      {
        id: 'security-guide',
        title: 'Security Guide',
        content: `# Security Guide

Security is paramount in the Lucid system. This guide covers best practices and security considerations.

## Data Encryption
- All session data is encrypted using AES-256
- Encryption keys are derived from user passwords
- Keys are never stored on the server

## Authentication
- JWT tokens with 24-hour expiration
- TOTP for two-factor authentication
- Hardware wallet support for enhanced security

## Network Security
- All communications encrypted with TLS
- Tor network integration for anonymity
- No IP address logging

## Best Practices
1. Use strong, unique passwords
2. Enable two-factor authentication
3. Keep software updated
4. Use hardware wallets when possible
5. Regularly backup important data`,
        category: 'Security',
        tags: ['security', 'encryption', 'authentication'],
        lastUpdated: '2024-01-01T00:00:00Z'
      },
      {
        id: 'troubleshooting',
        title: 'Troubleshooting',
        content: `# Troubleshooting

Common issues and their solutions.

## Connection Issues
- Check internet connection
- Verify Tor is running
- Check firewall settings
- Try different Tor circuits

## Authentication Problems
- Verify token is valid
- Check token expiration
- Ensure correct credentials
- Try refreshing the token

## Performance Issues
- Check system resources
- Monitor network latency
- Verify node availability
- Check for rate limiting

## Error Codes
- \`400\`: Bad Request
- \`401\`: Unauthorized
- \`403\`: Forbidden
- \`404\`: Not Found
- \`429\`: Rate Limited
- \`500\`: Internal Server Error`,
        category: 'Support',
        tags: ['troubleshooting', 'errors', 'support'],
        lastUpdated: '2024-01-01T00:00:00Z'
      }
    ];

    return mockDocs;
  };

  const handleFilterChange = (key: keyof DocumentationFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSectionSelect = (section: DocumentationSection) => {
    setSelectedSection(section);
  };

  const filteredSections = sections.filter(section => {
    const matchesCategory = filters.category === 'all' || section.category === filters.category;
    const matchesSearch = filters.search === '' || 
      section.title.toLowerCase().includes(filters.search.toLowerCase()) ||
      section.content.toLowerCase().includes(filters.search.toLowerCase());
    const matchesTags = filters.tags.length === 0 || 
      filters.tags.some(tag => section.tags.includes(tag));
    
    return matchesCategory && matchesSearch && matchesTags;
  });

  const categories = ['all', ...Array.from(new Set(sections.map(s => s.category)))];
  const allTags = Array.from(new Set(sections.flatMap(s => s.tags)));

  return (
    <div className="developer-content">
      <div className="developer-card">
        <div className="developer-card-header">
          <div>
            <h2 className="developer-card-title">API Documentation</h2>
            <p className="developer-card-subtitle">
              Complete API documentation and guides
            </p>
          </div>
          <div className="developer-card-actions">
            <button 
              className="developer-btn developer-btn-secondary"
              onClick={loadDocumentation}
              disabled={isLoading}
            >
              Refresh
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
          <div>
            <div className="developer-form-group">
              <label className="developer-form-label">Category</label>
              <select
                className="developer-form-input"
                value={filters.category}
                onChange={(e) => handleFilterChange('category', e.target.value)}
              >
                {categories.map(category => (
                  <option key={category} value={category}>
                    {category === 'all' ? 'All Categories' : category}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <div className="developer-form-group">
              <label className="developer-form-label">Search</label>
              <input
                type="text"
                className="developer-form-input"
                placeholder="Search documentation..."
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
              />
            </div>
          </div>
        </div>

        {isLoading && (
          <div className="developer-loading">
            <div className="developer-loading-spinner"></div>
            <p>Loading documentation...</p>
          </div>
        )}

        {error && (
          <div className="developer-error">
            <div className="developer-error-icon">⚠️</div>
            <div className="developer-error-title">Error</div>
            <div className="developer-error-message">{error}</div>
            <button 
              className="developer-btn developer-btn-primary"
              onClick={loadDocumentation}
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !error && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
            <div>
              <h3 style={{ marginBottom: '1rem', color: '#f8fafc' }}>Documentation Sections</h3>
              <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
                {filteredSections.map(section => (
                  <div
                    key={section.id}
                    className={`developer-card ${selectedSection?.id === section.id ? 'active' : ''}`}
                    style={{ 
                      padding: '1rem', 
                      marginBottom: '0.5rem',
                      cursor: 'pointer',
                      border: selectedSection?.id === section.id ? '2px solid #3b82f6' : '1px solid rgba(51, 65, 85, 0.3)'
                    }}
                    onClick={() => handleSectionSelect(section)}
                  >
                    <h4 style={{ margin: '0 0 0.5rem 0', color: '#f8fafc' }}>{section.title}</h4>
                    <p style={{ margin: '0 0 0.5rem 0', color: '#94a3b8', fontSize: '0.875rem' }}>
                      {section.category}
                    </p>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {section.tags.slice(0, 3).map(tag => (
                        <span
                          key={tag}
                          style={{
                            background: 'rgba(59, 130, 246, 0.2)',
                            color: '#60a5fa',
                            padding: '0.25rem 0.5rem',
                            borderRadius: '0.25rem',
                            fontSize: '0.75rem'
                          }}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              {selectedSection ? (
                <div className="developer-card">
                  <div className="developer-card-header">
                    <div>
                      <h3 className="developer-card-title">{selectedSection.title}</h3>
                      <p className="developer-card-subtitle">
                        {selectedSection.category} • Updated {new Date(selectedSection.lastUpdated).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div 
                    style={{ 
                      lineHeight: '1.6',
                      color: '#d1d5db'
                    }}
                    dangerouslySetInnerHTML={{ 
                      __html: selectedSection.content.replace(/\n/g, '<br>').replace(/```([^`]+)```/g, '<pre style="background: rgba(30, 41, 59, 0.5); padding: 1rem; border-radius: 0.5rem; overflow-x: auto;"><code>$1</code></pre>') 
                    }}
                  />
                </div>
              ) : (
                <div className="developer-empty-state">
                  <div className="developer-empty-state-icon">📚</div>
                  <div className="developer-empty-state-title">Select a Documentation Section</div>
                  <div className="developer-empty-state-description">
                    Choose a section from the list to view its documentation.
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export { DocumentationPage };
