# Lucid Authentication Service

## Overview

The Lucid Authentication Service (Cluster 09) provides secure authentication and authorization for the Lucid blockchain system. It implements TRON signature verification, hardware wallet integration, JWT token management, and role-based access control (RBAC).

**Service Name**: `lucid-auth-service`  
**Cluster ID**: 09-AUTHENTICATION  
**Port**: 8089  
**Phase**: Foundation Phase 1  
**Status**: Production Ready ✅

---

## Features

### Core Authentication
- ✅ **TRON Signature Verification** - Cryptographic signature validation for TRON addresses
- ✅ **Hardware Wallet Support** - Integration with Ledger, Trezor, and KeepKey devices
- ✅ **JWT Token Management** - Secure token generation with 15-minute access and 7-day refresh tokens
- ✅ **Session Management** - Redis-backed session storage with automatic cleanup
- ✅ **RBAC Engine** - 4-tier role system (USER, NODE_OPERATOR, ADMIN, SUPER_ADMIN)

### Security Features
- ✅ **Rate Limiting** - Tiered rate limits (100/1000/10000 req/min)
- ✅ **Audit Logging** - Comprehensive event logging with 90-day retention
- ✅ **Brute Force Protection** - Max 5 attempts with 15-minute cooldown
- ✅ **Token Blacklisting** - Revoked token management in Redis
- ✅ **Input Validation** - Comprehensive validation of all inputs

### Infrastructure
- ✅ **Distroless Container** - Minimal attack surface with no shell access
- ✅ **Multi-Stage Build** - Optimized container with ~75% size reduction
- ✅ **Health Checks** - Built-in health monitoring endpoints
- ✅ **Service Mesh Ready** - Beta sidecar integration support
- ✅ **Horizontal Scaling** - Stateless design for easy scaling

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- MongoDB 7.0+
- Redis 7.0+
- Python 3.11+ (for local development)

### Using Docker Compose (Recommended)

```bash
# 1. Clone the repository
cd Lucid/auth

# 2. Copy environment template
cp env.example .env

# 3. Generate JWT secret
openssl rand -hex 32

# 4. Edit .env and set JWT_SECRET_KEY

# 5. Start services
docker-compose up -d

# 6. Verify health
curl http://localhost:8089/health
```

### Using Docker

```bash
# Build container
docker build -t lucid-auth-service:latest .

# Run container
docker run -d \
  --name lucid-auth-service \
  --network lucid-network \
  -p 8089:8089 \
  -e JWT_SECRET_KEY=${JWT_SECRET_KEY} \
  -e MONGODB_URI=mongodb://mongodb:27017/lucid_auth \
  -e REDIS_URI=redis://redis:6379/1 \
  lucid-auth-service:latest

# Check logs
docker logs lucid-auth-service
```

### Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export JWT_SECRET_KEY="your-secret-key"
export MONGODB_URI="mongodb://localhost:27017/lucid_auth"
export REDIS_URI="redis://localhost:6379/1"

# 4. Run service
python -m auth.main

# Or with uvicorn
uvicorn auth.main:app --host 0.0.0.0 --port 8089 --reload
```

---

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/auth/register` | Register new user with TRON address | None |
| POST | `/auth/login` | Login with TRON signature | None |
| POST | `/auth/verify` | Verify JWT token | None |
| POST | `/auth/refresh` | Refresh access token | Refresh Token |
| POST | `/auth/logout` | User logout | JWT Token |
| GET | `/auth/status` | Authentication status | JWT Token |

### Hardware Wallet Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/hw/connect` | Connect hardware wallet | JWT Token |
| POST | `/hw/sign` | Sign with hardware wallet | JWT Token |
| GET | `/hw/status` | Get hardware wallet status | JWT Token |

### User Management Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/users/me` | Get current user profile | JWT Token |
| PUT | `/users/me` | Update user profile | JWT Token |
| GET | `/users/{user_id}` | Get user by ID | Admin Token |
| DELETE | `/users/{user_id}` | Delete user | Super Admin Token |

### Session Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/sessions` | List user sessions | JWT Token |
| GET | `/sessions/{session_id}` | Get session details | JWT Token |
| DELETE | `/sessions/{session_id}` | Revoke session | JWT Token |

### Health & Meta Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/health` | Service health check | None |
| GET | `/meta/info` | Service information | None |
| GET | `/metrics` | Prometheus metrics | None |

---

## Configuration

### Environment Variables

See `env.example` for a complete list of configuration options. Key variables:

**Required:**
- `JWT_SECRET_KEY` - JWT signing key (minimum 32 characters)
- `MONGODB_URI` - MongoDB connection string
- `REDIS_URI` - Redis connection string

**Optional but Recommended:**
- `ENABLE_HARDWARE_WALLET` - Enable hardware wallet support (default: true)
- `RATE_LIMIT_ENABLED` - Enable rate limiting (default: true)
- `AUDIT_LOG_ENABLED` - Enable audit logging (default: true)

### Security Settings

```bash
# JWT Configuration
ACCESS_TOKEN_EXPIRE_MINUTES=15    # Short-lived access tokens
REFRESH_TOKEN_EXPIRE_DAYS=7       # Longer refresh tokens

# Rate Limiting
RATE_LIMIT_PUBLIC=100             # Unauthenticated requests/min
RATE_LIMIT_AUTHENTICATED=1000     # Authenticated requests/min
RATE_LIMIT_ADMIN=10000            # Admin requests/min

# Brute Force Protection
MAX_LOGIN_ATTEMPTS=5              # Max failed login attempts
LOGIN_COOLDOWN_MINUTES=15         # Cooldown period
```

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────┐
│                 FastAPI Application                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Auth Routes  │  │  HW Wallet   │  │   User    │ │
│  │              │  │   Routes     │  │  Routes   │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │              Middleware Layer                 │  │
│  │  • Authentication  • Rate Limiting  • Audit   │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │              Service Layer                    │  │
│  │  • AuthenticationService  • UserManager       │  │
│  │  • SessionManager  • HardwareWalletService    │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          │                               │
    ┌─────▼─────┐                   ┌─────▼─────┐
    │  MongoDB  │                   │   Redis   │
    │  Port     │                   │   Port    │
    │  27017    │                   │   6379    │
    └───────────┘                   └───────────┘
```

### Database Schema

**MongoDB Collections:**
- `users` - User profiles and credentials
- `sessions` - Active session metadata
- `tokens` - Token blacklist
- `audit_logs` - Security event logs

**Redis Keys:**
- `session:{user_id}` - Active user sessions
- `rate_limit:{ip}` - Rate limit counters
- `blacklist:{token}` - Revoked tokens

---

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=auth --cov-report=html

# Run specific test file
pytest auth/tests/test_auth.py

# Run integration tests
pytest auth/tests/test_database_integration.py
```

### Code Quality

```bash
# Format code
black auth/

# Lint code
flake8 auth/
pylint auth/

# Type checking
mypy auth/
```

### Docker Build

```bash
# Build multi-stage container
docker build -t lucid-auth-service:latest .

# Build with specific platform
docker build --platform linux/amd64 -t lucid-auth-service:amd64 .
docker build --platform linux/arm64 -t lucid-auth-service:arm64 .

# Scan for vulnerabilities
docker scan lucid-auth-service:latest
```

---

## Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  auth-service:
    image: lucid-auth-service:latest
    ports:
      - "8089:8089"
    environment:
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - MONGODB_URI=mongodb://mongodb:27017/lucid_auth
      - REDIS_URI=redis://redis:6379/1
    depends_on:
      - mongodb
      - redis
    networks:
      - lucid-network
    restart: unless-stopped
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lucid-auth-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lucid-auth-service
  template:
    metadata:
      labels:
        app: lucid-auth-service
    spec:
      containers:
      - name: auth-service
        image: lucid-auth-service:latest
        ports:
        - containerPort: 8089
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: auth-secrets
              key: jwt-secret
        livenessProbe:
          httpGet:
            path: /health
            port: 8089
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8089
          initialDelaySeconds: 5
          periodSeconds: 10
```

---

## Monitoring

### Health Checks

```bash
# Basic health check
curl http://localhost:8089/health

# Expected response:
{
  "status": "healthy",
  "service": "auth-service",
  "version": "1.0.0",
  "dependencies": {
    "database": "healthy",
    "redis": "healthy",
    "hardware_wallet": "enabled"
  }
}
```

### Metrics

Prometheus metrics available at `/metrics`:

- `auth_requests_total` - Total authentication requests
- `auth_requests_success` - Successful authentications
- `auth_requests_failed` - Failed authentications
- `auth_token_generation_duration` - Token generation latency
- `auth_hardware_wallet_operations` - Hardware wallet operations

### Logs

Structured JSON logs with correlation IDs:

```json
{
  "timestamp": "2025-10-14T10:30:00Z",
  "level": "INFO",
  "service": "auth-service",
  "request_id": "req-uuid-here",
  "user_id": "user-uuid",
  "action": "login",
  "status": "success",
  "duration_ms": 150
}
```

---

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs
docker logs lucid-auth-service

# Verify environment variables
docker exec lucid-auth-service env | grep JWT_SECRET_KEY

# Test database connectivity
docker exec lucid-auth-service python -c "from motor.motor_asyncio import AsyncIOMotorClient; print('OK')"
```

**Authentication fails:**
```bash
# Check JWT secret consistency
echo $JWT_SECRET_KEY

# Verify token format
curl -X POST http://localhost:8089/auth/verify \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check audit logs
docker exec mongodb mongosh lucid_auth --eval "db.audit_logs.find().limit(10)"
```

**Rate limiting issues:**
```bash
# Check Redis connectivity
docker exec redis redis-cli ping

# View rate limit keys
docker exec redis redis-cli --scan --pattern "rate_limit:*"

# Clear rate limits (development only)
docker exec redis redis-cli FLUSHDB
```

---

## Security Considerations

### Production Checklist

- [ ] Generate strong JWT_SECRET_KEY (minimum 32 characters)
- [ ] Enable HTTPS/TLS for all connections
- [ ] Configure firewall rules (only allow ports 8089, 27017, 6379)
- [ ] Enable rate limiting
- [ ] Enable audit logging with 90-day retention
- [ ] Set up log aggregation and monitoring
- [ ] Configure backup strategy for MongoDB
- [ ] Implement secret rotation policy (90 days)
- [ ] Enable hardware wallet support for admin accounts
- [ ] Configure CORS origins restrictively
- [ ] Enable service mesh with mTLS
- [ ] Set up intrusion detection
- [ ] Perform security audit and penetration testing

### Best Practices

1. **Never commit secrets** - Use environment variables or secrets management
2. **Rotate keys regularly** - JWT secrets every 90 days
3. **Monitor audit logs** - Set up alerts for suspicious activity
4. **Use hardware wallets** - For admin and high-value accounts
5. **Enable rate limiting** - Prevent brute force attacks
6. **Keep dependencies updated** - Regular security patches
7. **Implement defense in depth** - Multiple security layers
8. **Test disaster recovery** - Regular backup and restore testing

---

## Contributing

### Development Workflow

1. Create feature branch from `main`
2. Implement changes with tests
3. Run full test suite
4. Update documentation
5. Submit pull request
6. Pass CI/CD checks
7. Code review approval
8. Merge to main

### Code Standards

- Follow PEP 8 style guide
- Use type hints (Python 3.11+)
- Write comprehensive tests (>95% coverage)
- Document all public APIs
- Use semantic commit messages

---

## License

Copyright © 2025 Lucid Development Team. All rights reserved.

---

## Support

**Documentation**: See `auth/docs/` directory for all build documentation  
**Issues**: GitHub Issues  
**Security**: security@lucid.onion  

---

## References

- [Authentication Cluster Overview](../plan/API_plans/09-authentication-cluster/00-cluster-overview.md)
- [API Specification](../plan/API_plans/09-authentication-cluster/01-api-specification.md)
- [Build Guide](../plan/API_plans/00-master-architecture/10-CLUSTER_09_AUTHENTICATION_BUILD_GUIDE.md)
- [Master Architecture](../plan/API_plans/00-master-architecture/00-master-api-architecture.md)

---

**Service Version**: 1.0.0  
**Documentation Version**: 1.0.0  
**Last Updated**: 2025-10-14

