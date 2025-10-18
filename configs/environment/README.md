# LUCID Environment Configuration Documentation

## Overview

This directory contains environment-specific configuration files for the Lucid blockchain system. Each environment file defines variables that control service behavior, security settings, and infrastructure configuration across all 10 service clusters.

## Environment Files

### Development Environment (`env.development`)
- **Purpose**: Local development and testing
- **Security**: Relaxed settings for development ease
- **Debugging**: Full debug logging and tracing enabled
- **Performance**: Optimized for development speed
- **Database**: Development databases with test data

### Staging Environment (`env.staging`)
- **Purpose**: Pre-production testing and validation
- **Security**: Moderate security settings
- **Debugging**: Limited debug information
- **Performance**: Production-like performance settings
- **Database**: Staging databases with production-like data

### Production Environment (`env.production`)
- **Purpose**: Live production deployment
- **Security**: Maximum security settings
- **Debugging**: Minimal logging for performance
- **Performance**: Optimized for production workloads
- **Database**: Production databases with real data

### Test Environment (`env.test`)
- **Purpose**: Automated testing and CI/CD
- **Security**: Minimal security for test speed
- **Debugging**: Full debug information
- **Performance**: Fast test execution
- **Database**: In-memory or temporary test databases

## Configuration Categories

### 1. Project Identification
- `LUCID_PROJECT`: Project identifier
- `LUCID_VERSION`: Version number
- `LUCID_ENVIRONMENT`: Environment name
- `LUCID_DEBUG`: Debug mode flag

### 2. Docker Configuration
- `DOCKER_BUILDKIT`: Docker BuildKit enablement
- `DOCKER_REGISTRY`: Container registry URL
- `DOCKER_NAMESPACE`: Registry namespace
- `DOCKER_IMAGE_PREFIX`: Image name prefix
- `LUCID_NETWORK_NAME`: Docker network name
- `LUCID_NETWORK_SUBNET`: Network subnet configuration

### 3. Service Configuration
Each service cluster has specific configuration variables:

#### API Gateway (Cluster 01)
- `API_GATEWAY_SERVICE_NAME`: Service identifier
- `API_GATEWAY_PORT`: Service port
- `API_GATEWAY_DEBUG`: Debug mode
- `API_GATEWAY_LOG_LEVEL`: Logging level

#### Blockchain Core (Cluster 02)
- `BLOCKCHAIN_ENGINE_SERVICE_NAME`: Engine identifier
- `BLOCKCHAIN_ENGINE_PORT`: Engine port
- `BLOCKCHAIN_NETWORK`: Network identifier
- `CONSENSUS_ALGORITHM`: Consensus mechanism
- `BLOCK_TIME_SECONDS`: Block creation interval

#### Session Management (Cluster 03)
- `SESSION_PIPELINE_PORT`: Pipeline service port
- `SESSION_RECORDER_PORT`: Recorder service port
- `SESSION_PROCESSOR_PORT`: Processor service port
- `SESSION_STORAGE_PORT`: Storage service port
- `SESSION_API_PORT`: API service port

#### RDP Services (Cluster 04)
- `RDP_SERVER_MANAGER_PORT`: Server manager port
- `RDP_XRDP_PORT`: XRDP service port
- `RDP_SESSION_CONTROLLER_PORT`: Session controller port
- `RDP_RESOURCE_MONITOR_PORT`: Resource monitor port

#### Node Management (Cluster 05)
- `NODE_MANAGEMENT_PORT`: Management service port
- `NODE_POOL_SIZE`: Pool size configuration
- `NODE_MIN_POOT_SCORE`: Minimum PoOT score

#### Admin Interface (Cluster 06)
- `ADMIN_INTERFACE_PORT`: Admin interface port
- `ADMIN_DEBUG`: Admin debug mode

#### TRON Payment (Cluster 07) - ISOLATED
- `TRON_PAYMENT_PORT`: Payment service port
- `TRON_NETWORK`: TRON network (mainnet/testnet)
- `TRON_ISOLATION_ENABLED`: Isolation enforcement

#### Storage Database (Cluster 08)
- `MONGODB_PORT`: MongoDB port
- `REDIS_PORT`: Redis port
- `ELASTICSEARCH_PORT`: Elasticsearch port

#### Authentication (Cluster 09)
- `AUTH_SERVICE_PORT`: Authentication service port
- `AUTH_DEBUG`: Authentication debug mode

#### Cross-Cluster Integration (Cluster 10)
- `SERVICE_MESH_ENABLED`: Service mesh enablement
- `CONSUL_PORT`: Consul service discovery port

### 4. Database Configuration

#### MongoDB
- `MONGODB_HOST`: Database host
- `MONGODB_DATABASE`: Database name
- `MONGODB_URI`: Connection URI
- `MONGODB_REPLICA_SET`: Replica set name
- `MONGODB_AUTH_ENABLED`: Authentication enablement
- `MONGODB_USER`: Database user
- `MONGODB_PASSWORD`: Database password

#### Redis
- `REDIS_HOST`: Redis host
- `REDIS_URI`: Connection URI
- `REDIS_PASSWORD`: Redis password
- `REDIS_CLUSTER_ENABLED`: Cluster mode enablement

#### Elasticsearch
- `ELASTICSEARCH_HOST`: Elasticsearch host
- `ELASTICSEARCH_URI`: Connection URI
- `ELASTICSEARCH_INDEX_PREFIX`: Index prefix
- `ELASTICSEARCH_CLUSTER_NAME`: Cluster name
- `ELASTICSEARCH_SECURITY_ENABLED`: Security enablement

### 5. Authentication Configuration
- `JWT_SECRET_KEY`: JWT signing key
- `JWT_ALGORITHM`: JWT algorithm
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiry
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiry
- `TRON_SIGNATURE_VERIFICATION_ENABLED`: TRON signature verification
- `ENABLE_HARDWARE_WALLET`: Hardware wallet support
- `RBAC_ENABLED`: Role-based access control

### 6. Rate Limiting Configuration
- `RATE_LIMIT_PUBLIC`: Public endpoint rate limit
- `RATE_LIMIT_AUTHENTICATED`: Authenticated endpoint rate limit
- `RATE_LIMIT_ADMIN`: Admin endpoint rate limit
- `RATE_LIMIT_CHUNK_UPLOAD`: Chunk upload rate limit

### 7. CORS Configuration
- `CORS_ORIGINS`: Allowed origins
- `CORS_ALLOW_CREDENTIALS`: Credential support
- `CORS_ALLOW_METHODS`: Allowed HTTP methods
- `CORS_ALLOW_HEADERS`: Allowed headers

### 8. Storage Paths
- `DATA_ROOT`: Root data directory
- `LOGS_ROOT`: Log directory
- `BACKUPS_ROOT`: Backup directory
- Service-specific storage paths

### 9. Logging Configuration
- `LOG_LEVEL`: Logging level
- `LOG_FORMAT`: Log format (json/text)
- `LOG_FILE_PATH`: Log file path
- `LOG_MAX_SIZE`: Maximum log file size
- `LOG_MAX_FILES`: Maximum log files
- `LOG_ROTATION_ENABLED`: Log rotation enablement

### 10. Health Check Configuration
- `HEALTH_CHECK_INTERVAL`: Check interval
- `HEALTH_CHECK_TIMEOUT`: Check timeout
- `HEALTH_CHECK_RETRIES`: Retry count
- `HEALTH_CHECK_START_PERIOD`: Startup period

### 11. Monitoring Configuration
- `METRICS_ENABLED`: Metrics collection
- `METRICS_PORT`: Metrics port
- `METRICS_PATH`: Metrics path
- `PROMETHEUS_ENABLED`: Prometheus integration
- `GRAFANA_ENABLED`: Grafana integration

### 12. Security Configuration
- `ENCRYPTION_KEY_ROTATION_DAYS`: Key rotation period
- `SESSION_ENCRYPTION_ENABLED`: Session encryption
- `TLS_ENABLED`: TLS enablement
- `MTLS_ENABLED`: Mutual TLS enablement
- `BCRYPT_ROUNDS`: Password hashing rounds
- `MAX_LOGIN_ATTEMPTS`: Maximum login attempts
- `LOGIN_COOLDOWN_MINUTES`: Login cooldown period

### 13. Container Configuration
- `DISTROLESS_PYTHON_BASE`: Python distroless base image
- `DISTROLESS_JAVA_BASE`: Java distroless base image
- `CONTAINER_MEMORY_LIMIT`: Memory limit
- `CONTAINER_CPU_LIMIT`: CPU limit
- `CONTAINER_RESTART_POLICY`: Restart policy

### 14. Network Configuration
- `NETWORK_TIMEOUT`: Network timeout
- `NETWORK_RETRY_ATTEMPTS`: Retry attempts
- `NETWORK_RETRY_DELAY`: Retry delay
- `NETWORK_KEEPALIVE`: Keep-alive enablement

### 15. Performance Configuration
- `UVICORN_WORKERS`: Worker count
- `UVICORN_WORKER_CLASS`: Worker class
- `UVICORN_MAX_REQUESTS`: Maximum requests per worker
- `UVICORN_MAX_REQUESTS_JITTER`: Request jitter

## Usage

### Loading Environment Variables

```bash
# Load development environment
source configs/environment/env.development

# Load staging environment
source configs/environment/env.staging

# Load production environment
source configs/environment/env.production

# Load test environment
source configs/environment/env.test
```

### Docker Compose Integration

```yaml
version: '3.8'
services:
  api-gateway:
    env_file:
      - configs/environment/env.development
    environment:
      - SERVICE_NAME=api-gateway
```

### Python Application Integration

```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('configs/environment/env.development')

# Access variables
service_name = os.getenv('API_GATEWAY_SERVICE_NAME')
port = int(os.getenv('API_GATEWAY_PORT', 8080))
```

## Security Considerations

### Secret Management
- **Never commit secrets to version control**
- Use environment-specific secret files
- Rotate secrets regularly
- Use secure secret management systems

### Environment Isolation
- **Development**: Relaxed security for ease of development
- **Staging**: Moderate security for testing
- **Production**: Maximum security for live systems
- **Test**: Minimal security for test speed

### Network Security
- **Development**: Local network access
- **Staging**: Limited external access
- **Production**: Tor-only access (.onion endpoints)
- **Test**: Isolated test network

## Validation

### Environment Validation Script
Use the provided validation script to ensure all required variables are set:

```bash
./scripts/config/validate-env.sh env.development
```

### Required Variables Checklist
- [ ] All service ports configured
- [ ] Database connection strings valid
- [ ] Authentication secrets set
- [ ] Network configuration correct
- [ ] Storage paths accessible
- [ ] Logging configuration valid

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   - Check variable names for typos
   - Ensure all required variables are set
   - Verify environment file is loaded

2. **Port Conflicts**
   - Check for port conflicts between services
   - Verify port ranges don't overlap
   - Use different ports for different environments

3. **Database Connection Issues**
   - Verify database credentials
   - Check network connectivity
   - Ensure database is running

4. **Permission Issues**
   - Check file and directory permissions
   - Verify user has required access
   - Ensure storage paths are writable

### Debug Mode
Enable debug mode for detailed logging:

```bash
export LUCID_DEBUG=true
export LOG_LEVEL=DEBUG
```

## Maintenance

### Regular Tasks
- [ ] Rotate secrets monthly
- [ ] Update environment files for new services
- [ ] Validate configuration changes
- [ ] Monitor environment-specific metrics

### Version Control
- [ ] Keep environment files in version control
- [ ] Use separate branches for environment changes
- [ ] Document all configuration changes
- [ ] Review changes before deployment

## References

- [Master Build Plan](../00-master-architecture/01-MASTER_BUILD_PLAN.md)
- [Build Requirements Guide](../00-master-architecture/13-BUILD_REQUIREMENTS_GUIDE.md)
- [Cluster Build Guides](../00-master-architecture/02-CLUSTER_01_API_GATEWAY_BUILD_GUIDE.md)
- [Docker Configuration](../docker/)
- [Security Configuration](../security/)

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-14  
**Next Review**: 2025-02-14
