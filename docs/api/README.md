# Lucid API Documentation

This directory contains the comprehensive API documentation for the Lucid blockchain system. The documentation includes OpenAPI 3.0 specifications for all service clusters, interactive API references, and code examples.

## 📋 Table of Contents

- [Overview](#overview)
- [Service Architecture](#service-architecture)
- [API Specifications](#api-specifications)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Code Examples](#code-examples)
- [Swagger UI](#swagger-ui)
- [Development Setup](#development-setup)
- [Contributing](#contributing)

## 🏗️ Overview

The Lucid blockchain system consists of 8 core service clusters, each with its own API specification:

1. **API Gateway** - Primary entry point for all API requests
2. **Blockchain Core** - Core blockchain operations and consensus
3. **Session Management** - User session and data management
4. **RDP Services** - Remote Desktop Protocol services
5. **Node Management** - Worker node coordination and management
6. **Admin Interface** - System administration and monitoring
7. **TRON Payment** - TRON blockchain payment processing
8. **Auth Service** - Authentication and authorization

## 🏛️ Service Architecture

```mermaid
graph TB
    Client[Client Applications] --> Gateway[API Gateway]
    Gateway --> Auth[Auth Service]
    Gateway --> Session[Session Management]
    Gateway --> Blockchain[Blockchain Core]
    Gateway --> RDP[RDP Services]
    Gateway --> Node[Node Management]
    Gateway --> Admin[Admin Interface]
    Gateway --> Payment[TRON Payment]
    
    Auth --> DB[(Database)]
    Session --> DB
    Blockchain --> DB
    RDP --> DB
    Node --> DB
    Admin --> DB
    Payment --> DB
    
    Payment --> TRON[TRON Network]
    Blockchain --> LucidBlocks[Lucid Blocks Network]
```

## 📚 API Specifications

### OpenAPI 3.0 Specifications

All service APIs are documented using OpenAPI 3.0 specification format:

| Service | Specification | Description |
|---------|---------------|-------------|
| API Gateway | [`openapi/api-gateway.yaml`](openapi/api-gateway.yaml) | Primary API entry point with routing and rate limiting |
| Blockchain Core | [`openapi/blockchain-core.yaml`](openapi/blockchain-core.yaml) | Core blockchain operations and consensus mechanisms |
| Session Management | [`openapi/session-management.yaml`](openapi/session-management.yaml) | User session and data storage management |
| RDP Services | [`openapi/rdp-services.yaml`](openapi/rdp-services.yaml) | Remote desktop protocol services |
| Node Management | [`openapi/node-management.yaml`](openapi/node-management.yaml) | Worker node coordination and management |
| Admin Interface | [`openapi/admin-interface.yaml`](openapi/admin-interface.yaml) | System administration and monitoring |
| TRON Payment | [`openapi/tron-payment.yaml`](openapi/tron-payment.yaml) | TRON blockchain payment processing |
| Auth Service | [`openapi/auth-service.yaml`](openapi/auth-service.yaml) | Authentication and authorization |

### Service Endpoints

#### API Gateway
- **Base URL**: `https://api.lucid-blockchain.org/api/v1`
- **Authentication**: Bearer Token, API Key
- **Rate Limiting**: 1000 requests/hour per user
- **Key Features**: Request routing, rate limiting, authentication, response caching

#### Blockchain Core
- **Base URL**: `https://blockchain.lucid-blockchain.org/api/v1`
- **Authentication**: Bearer Token
- **Key Features**: Block creation, transaction processing, consensus mechanisms

#### Session Management
- **Base URL**: `https://sessions.lucid-blockchain.org/api/v1`
- **Authentication**: Bearer Token
- **Key Features**: Session creation, data storage, session monitoring

#### RDP Services
- **Base URL**: `https://rdp.lucid-blockchain.org/api/v1`
- **Authentication**: Bearer Token
- **Key Features**: Remote desktop connections, session streaming, user management

#### Node Management
- **Base URL**: `https://nodes.lucid-blockchain.org/api/v1`
- **Authentication**: Bearer Token
- **Key Features**: Node registration, health monitoring, load balancing

#### Admin Interface
- **Base URL**: `https://admin.lucid-blockchain.org/api/v1`
- **Authentication**: Bearer Token (Admin/Super Admin roles)
- **Key Features**: System monitoring, user management, audit logging

#### TRON Payment
- **Base URL**: `https://payment.lucid-blockchain.org/api/v1`
- **Authentication**: Bearer Token
- **Key Features**: TRON transactions, wallet management, subscription billing

#### Auth Service
- **Base URL**: `https://auth.lucid-blockchain.org/api/v1`
- **Authentication**: Bearer Token (for protected endpoints)
- **Key Features**: User authentication, registration, password management, 2FA

## 🔐 Authentication

The Lucid API uses multiple authentication methods:

### Bearer Token Authentication
```http
Authorization: Bearer <access_token>
```

### API Key Authentication
```http
X-API-Key: <api_key>
```

### Authentication Flow
1. Register/Login via Auth Service
2. Receive access token and refresh token
3. Use access token for API requests
4. Refresh token when access token expires

## ⚡ Rate Limiting

All APIs implement rate limiting to ensure fair usage:

| Service | Rate Limit | Window |
|---------|------------|--------|
| API Gateway | 1000 requests/hour | Per user |
| Auth Service | 100 requests/hour | Per IP |
| Payment Service | 500 requests/hour | Per user |
| Admin Interface | 2000 requests/hour | Per admin user |

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## 🚨 Error Handling

All APIs use consistent error response format:

```json
{
  "error": {
    "code": "LUCID_ERR_4001",
    "message": "User not found",
    "details": {
      "user_id": "123e4567-e89b-12d3-a456-426614174000"
    },
    "request_id": "req_123456789",
    "timestamp": "2024-01-01T00:00:00Z",
    "service": "auth-service",
    "version": "v1"
  }
}
```

### Error Code Registry

| Code | Description | HTTP Status |
|------|-------------|-------------|
| LUCID_ERR_4001 | User not found | 404 |
| LUCID_ERR_4002 | Invalid credentials | 401 |
| LUCID_ERR_4003 | Insufficient permissions | 403 |
| LUCID_ERR_4004 | Rate limit exceeded | 429 |
| LUCID_ERR_5001 | Payment processing failed | 402 |
| LUCID_ERR_5002 | Blockchain transaction failed | 500 |
| LUCID_ERR_6001 | Authentication failed | 401 |
| LUCID_ERR_6002 | Token expired | 401 |

## 💻 Code Examples

### JavaScript/Node.js

```javascript
// Initialize API client
const lucidAPI = new LucidAPI({
  baseURL: 'https://api.lucid-blockchain.org/api/v1',
  apiKey: 'your-api-key'
});

// Create a new session
const session = await lucidAPI.sessions.create({
  name: 'My Session',
  description: 'Remote desktop session',
  duration: 3600
});

// Upload session data
await lucidAPI.sessions.uploadData(session.id, {
  data: sessionData,
  chunk: 1,
  total_chunks: 10
});
```

### Python

```python
import requests
from lucid_sdk import LucidClient

# Initialize client
client = LucidClient(
    base_url='https://api.lucid-blockchain.org/api/v1',
    api_key='your-api-key'
)

# Create session
session = client.sessions.create(
    name='My Session',
    description='Remote desktop session',
    duration=3600
)

# Upload data
client.sessions.upload_data(
    session_id=session['id'],
    data=session_data,
    chunk=1,
    total_chunks=10
)
```

### cURL Examples

```bash
# Create session
curl -X POST https://api.lucid-blockchain.org/api/v1/sessions \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Session",
    "description": "Remote desktop session",
    "duration": 3600
  }'

# Get session status
curl -X GET https://api.lucid-blockchain.org/api/v1/sessions/{session_id} \
  -H "Authorization: Bearer your-token"
```

## 🎯 Swagger UI

Interactive API documentation is available via Swagger UI:

- **Production**: https://api.lucid-blockchain.org/docs
- **Development**: https://api-dev.lucid-blockchain.org/docs
- **Local**: http://localhost:8080/docs

### Features
- Interactive API testing
- Request/response examples
- Authentication testing
- Schema validation
- Code generation

## 🛠️ Development Setup

### Prerequisites
- Node.js 18+
- Python 3.9+
- Docker
- Git

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/HamiGames/Lucid.git
cd Lucid
```

2. **Install dependencies**
```bash
npm install
pip install -r requirements.txt
```

3. **Start development servers**
```bash
# Start all services
./scripts/start-dev.sh

# Or start individual services
cd cluster/api-gateway && npm run dev
cd cluster/auth-service && npm run dev
```

4. **Access Swagger UI**
```bash
# API Gateway
open http://localhost:8080/docs

# Auth Service
open http://localhost:8085/docs
```

### API Testing

```bash
# Run API tests
npm run test:api

# Run specific service tests
npm run test:api -- --service=auth-service

# Generate test coverage
npm run test:coverage
```

## 📊 Monitoring and Analytics

### API Metrics
- Request volume and response times
- Error rates and status codes
- Authentication success/failure rates
- Rate limiting statistics

### Health Checks
All services provide health check endpoints:
- `/health` - Basic health status
- `/health/detailed` - Detailed system status
- `/metrics` - Prometheus metrics

## 🔧 Configuration

### Environment Variables

```bash
# API Gateway
API_GATEWAY_PORT=8080
API_GATEWAY_RATE_LIMIT=1000
API_GATEWAY_CACHE_TTL=300

# Auth Service
AUTH_SERVICE_PORT=8085
AUTH_JWT_SECRET=your-jwt-secret
AUTH_TOKEN_EXPIRY=3600

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/lucid
REDIS_URL=redis://localhost:6379
```

### Docker Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  api-gateway:
    build: ./cluster/api-gateway
    ports:
      - "8080:8080"
    environment:
      - API_GATEWAY_PORT=8080
      - DATABASE_URL=postgresql://postgres:password@db:5432/lucid
  
  auth-service:
    build: ./cluster/auth-service
    ports:
      - "8085:8085"
    environment:
      - AUTH_SERVICE_PORT=8085
      - DATABASE_URL=postgresql://postgres:password@db:5432/lucid
```

## 📝 Contributing

### Adding New Endpoints

1. Update the OpenAPI specification
2. Add endpoint documentation
3. Include request/response examples
4. Update error code registry
5. Add tests

### Documentation Standards

- Use clear, concise descriptions
- Include all required parameters
- Provide realistic examples
- Document error conditions
- Follow OpenAPI 3.0 standards

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Update documentation
4. Add tests
5. Submit pull request

## 📞 Support

- **Documentation**: https://docs.lucid-blockchain.org
- **API Reference**: https://api.lucid-blockchain.org/docs
- **GitHub Issues**: https://github.com/HamiGames/Lucid/issues
- **Email**: dev@lucid-blockchain.org

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

---

**Last Updated**: January 2024  
**Version**: 1.0.0  
**Maintainer**: Lucid Development Team