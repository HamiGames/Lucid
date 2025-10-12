# API Gateway Cluster Overview

## Cluster Information

**Cluster ID**: 01-api-gateway-cluster  
**Cluster Name**: API Gateway Cluster (Cluster A)  
**Primary Port**: 8080 (HTTP), 8081 (HTTPS)  
**Service Type**: Entry point and routing layer

## Architecture Overview

The API Gateway Cluster serves as the primary entry point for all external API requests, providing routing, load balancing, authentication, rate limiting, and request/response transformation services.

```
┌─────────────────────────────────────────────────────────────┐
│                    External Clients                         │
│  Web UI, Mobile Apps, Third-party Integrations             │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTPS/HTTP (Port 8080/8081)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  API Gateway Cluster                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Router    │  │   Auth      │  │   Rate      │         │
│  │  Service    │  │  Service    │  │  Limiter    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Load      │  │   Request   │  │   Response  │         │
│  │  Balancer   │  │Transformer │  │Transformer │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────┬───────────────────────────────────────────┘
                  │ Internal routing
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend Service Clusters                       │
│  Blockchain Core, Session Management, RDP Services, etc.    │
└─────────────────────────────────────────────────────────────┘
```

## Services in Cluster

### 1. Gateway Router Service
- **Container**: `lucid-api-gateway`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8080 (HTTP), 8081 (HTTPS)
- **Responsibilities**:
  - Request routing to backend services
  - Load balancing across service instances
  - SSL/TLS termination
  - Request/response logging

### 2. Authentication Service
- **Container**: `lucid-auth-proxy`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8082
- **Responsibilities**:
  - JWT token validation
  - Magic link authentication
  - TOTP verification
  - Hardware wallet integration

### 3. Rate Limiting Service
- **Container**: `lucid-rate-limiter`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8083
- **Responsibilities**:
  - Request rate limiting
  - Quota management
  - DDoS protection
  - Usage analytics

## API Endpoints

### Meta Endpoints
- `GET /api/v1/meta/info` - Service information
- `GET /api/v1/meta/health` - Health check
- `GET /api/v1/meta/version` - Version information
- `GET /api/v1/meta/metrics` - Service metrics

### Authentication Endpoints
- `POST /api/v1/auth/login` - Magic link login
- `POST /api/v1/auth/verify` - TOTP verification
- `POST /api/v1/auth/refresh` - Token refresh
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/status` - Authentication status

### User Management Endpoints
- `GET /api/v1/users/me` - Current user info
- `PUT /api/v1/users/me` - Update user profile
- `GET /api/v1/users/{user_id}` - User details
- `POST /api/v1/users` - Create user account

### Session Management Endpoints
- `POST /api/v1/sessions` - Create new session
- `GET /api/v1/sessions` - List user sessions
- `GET /api/v1/sessions/{session_id}` - Session details
- `PUT /api/v1/sessions/{session_id}` - Update session
- `DELETE /api/v1/sessions/{session_id}` - Delete session

### Manifest Endpoints
- `GET /api/v1/manifests/{manifest_id}` - Get manifest
- `POST /api/v1/manifests` - Create manifest
- `PUT /api/v1/manifests/{manifest_id}` - Update manifest

### Trust Policy Endpoints
- `GET /api/v1/trust/policies` - List trust policies
- `POST /api/v1/trust/policies` - Create trust policy
- `PUT /api/v1/trust/policies/{policy_id}` - Update policy

### Chain Proxy Endpoints
- `GET /api/v1/chain/info` - Blockchain information
- `GET /api/v1/chain/blocks` - List blocks
- `GET /api/v1/chain/blocks/{block_id}` - Block details
- `POST /api/v1/chain/transactions` - Submit transaction

### Wallets Proxy Endpoints
- `GET /api/v1/wallets` - List user wallets
- `POST /api/v1/wallets` - Create wallet
- `GET /api/v1/wallets/{wallet_id}` - Wallet details
- `POST /api/v1/wallets/{wallet_id}/transactions` - Create transaction

## Dependencies

### Internal Dependencies
- **Blockchain Core Cluster**: Chain information, transaction submission
- **Session Management Cluster**: Session lifecycle management
- **Authentication Cluster**: User authentication and authorization
- **TRON Payment Cluster**: Payment operations (isolated)

### External Dependencies
- **MongoDB**: User data, session metadata, configuration
- **Redis**: Rate limiting counters, session cache
- **Tor Network**: Secure communication with backend services

## Configuration

### Environment Variables
```bash
# Service Configuration
SERVICE_NAME=api-gateway
API_VERSION=v1
DEBUG=false

# Port Configuration
HTTP_PORT=8080
HTTPS_PORT=8081
AUTH_PORT=8082
RATE_LIMITER_PORT=8083

# Backend Service URLs
BLOCKCHAIN_CORE_URL=http://blockchain-core:8084
SESSION_MANAGEMENT_URL=http://session-management:8085
AUTH_SERVICE_URL=http://auth-service:8086
TRON_PAYMENT_URL=http://tron-payment:8087

# Database Configuration
MONGODB_URI=mongodb://mongodb:27017/lucid_gateway
REDIS_URL=redis://redis:6379/0

# Security Configuration
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST_SIZE=200
RATE_LIMIT_ENABLED=true

# SSL Configuration
SSL_CERT_PATH=/certs/api-gateway.crt
SSL_KEY_PATH=/certs/api-gateway.key
SSL_ENABLED=true
```

### Docker Compose Configuration
```yaml
version: '3.8'
services:
  api-gateway:
    build:
      context: ./03-api-gateway
      dockerfile: Dockerfile
    image: lucid-api-gateway:latest
    container_name: lucid-api-gateway
    ports:
      - "8080:8080"
      - "8081:8081"
    environment:
      - SERVICE_NAME=api-gateway
      - MONGODB_URI=mongodb://mongodb:27017/lucid_gateway
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - mongodb
      - redis
    networks:
      - lucid-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/meta/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Performance Characteristics

### Expected Load
- **Requests per second**: 1000+ concurrent requests
- **Response time**: < 100ms for cached responses, < 500ms for backend calls
- **Availability**: 99.9% uptime
- **Throughput**: 10,000+ requests per minute

### Resource Requirements
- **CPU**: 2 cores minimum, 4 cores recommended
- **Memory**: 4GB minimum, 8GB recommended
- **Storage**: 20GB for logs and cache
- **Network**: 1Gbps minimum bandwidth

## Security Considerations

### Authentication & Authorization
- JWT token-based authentication
- Role-based access control (RBAC)
- Hardware wallet integration for enhanced security
- Magic link + TOTP two-factor authentication

### Network Security
- TLS 1.3 encryption for all external communications
- Tor network integration for anonymous access
- Rate limiting to prevent abuse
- DDoS protection mechanisms

### Data Protection
- Request/response logging with sensitive data filtering
- Audit trail for all administrative actions
- Secure session management
- Encryption at rest for cached data

## Monitoring & Observability

### Health Checks
- Service health endpoint: `/api/v1/meta/health`
- Dependency health monitoring
- Automatic failover mechanisms
- Circuit breaker pattern implementation

### Metrics Collection
- Request rate and response time metrics
- Error rate and status code distribution
- Resource utilization (CPU, memory, network)
- Business metrics (active sessions, user count)

### Logging
- Structured JSON logging
- Request/response correlation IDs
- Security event logging
- Performance monitoring logs

## Scaling Strategy

### Horizontal Scaling
- Load balancer distribution across multiple gateway instances
- Session affinity for stateful operations
- Auto-scaling based on CPU and memory utilization
- Geographic distribution for global access

### Vertical Scaling
- CPU and memory optimization
- Connection pooling for backend services
- Caching strategies for frequently accessed data
- Database query optimization

## Deployment Strategy

### Container Deployment
- Distroless base images for security
- Multi-stage builds for optimization
- Health checks and readiness probes
- Rolling updates with zero downtime

### Configuration Management
- Environment-specific configuration files
- Secret management for sensitive data
- Configuration validation on startup
- Hot reloading for non-critical changes

## Troubleshooting

### Common Issues
1. **High Response Times**: Check backend service health and network connectivity
2. **Authentication Failures**: Verify JWT token validity and auth service availability
3. **Rate Limiting Issues**: Review rate limit configuration and user quotas
4. **SSL/TLS Errors**: Check certificate validity and configuration

### Debugging Tools
- Service logs with correlation IDs
- Health check endpoints for all dependencies
- Metrics dashboard for performance monitoring
- Request tracing for end-to-end visibility

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
