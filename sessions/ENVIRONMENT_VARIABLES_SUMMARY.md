# Environment Variables Summary for Session Containers

This document summarizes all environment variable requirements for session-related containers in `docker-compose.application.yml`.

## Container: session-pipeline

**Port:** 8087

### Required Environment Variables

| Variable | Source | Description | Default |
|----------|--------|-------------|---------|
| `SESSION_PIPELINE_PORT` | docker-compose environment | Service port | `8087` |
| `SESSION_PIPELINE_HOST` | docker-compose environment | Service hostname (for URLs) | `session-pipeline` |
| `MONGODB_URL` | `.env.foundation`, `.env.core` | MongoDB connection URL | **Required** |
| `REDIS_URL` | `.env.foundation`, `.env.core` | Redis connection URL | **Required** |
| `ELASTICSEARCH_URL` | `.env.foundation`, `.env.core` | Elasticsearch connection URL | Optional |
| `SECRET_KEY` | `.env.secrets` | Encryption secret key | **Required** (or `BLOCKCHAIN_SECRET_KEY` or `JWT_SECRET_KEY`) |
| `ENCRYPTION_KEY` | `.env.secrets` | Encryption key (32+ chars) | Optional |
| `JWT_SECRET_KEY` | `.env.secrets` | JWT secret key | Optional (fallback for SECRET_KEY) |

### Configuration Files
- `sessions/pipeline/config.py` - Uses Pydantic BaseSettings with `env_file=None` to read from environment
- `sessions/pipeline/entrypoint.py` - Reads `SESSION_PIPELINE_PORT` and always binds to `0.0.0.0`

---

## Container: session-recorder

**Port:** 8090

### Required Environment Variables

| Variable | Source | Description | Default |
|----------|--------|-------------|---------|
| `SESSION_RECORDER_PORT` | docker-compose environment | Service port | `8090` |
| `SESSION_RECORDER_HOST` | docker-compose environment | Service hostname (for URLs) | `session-recorder` |
| `MONGODB_URL` | `.env.foundation`, `.env.core` | MongoDB connection URL | **Required** |
| `REDIS_URL` | `.env.foundation`, `.env.core` | Redis connection URL | **Required** |
| `ELASTICSEARCH_URL` | `.env.foundation`, `.env.core` | Elasticsearch connection URL | Optional |

### Configuration Files
- `sessions/recorder/main.py` - Reads `SESSION_RECORDER_PORT` and always binds to `0.0.0.0`

---

## Container: session-processor

**Port:** 8091

### Required Environment Variables

| Variable | Source | Description | Default |
|----------|--------|-------------|---------|
| `SESSION_PROCESSOR_PORT` | docker-compose environment | Service port | `8091` |
| `SESSION_PROCESSOR_HOST` | docker-compose environment | Service hostname (for URLs) | `session-processor` |
| `MONGODB_URL` | `.env.foundation`, `.env.core` | MongoDB connection URL | **Required** |
| `REDIS_URL` | `.env.foundation`, `.env.core` | Redis connection URL | **Required** |
| `ELASTICSEARCH_URL` | `.env.foundation`, `.env.core` | Elasticsearch connection URL | Optional |
| `ENCRYPTION_KEY` | `.env.secrets` | Encryption key (32+ chars) | Optional |
| `SESSION_STORAGE_URL` | `.env.application` | Session storage service URL | Optional |
| `BLOCKCHAIN_ENGINE_URL` | `.env.core`, `.env.application` | Blockchain engine URL | Optional |
| `API_GATEWAY_URL` | `.env.core`, `.env.application` | API gateway URL | Optional |

### Configuration Files
- `sessions/processor/config.py` - Uses Pydantic BaseSettings with `env_file=None` to read from environment
- `sessions/processor/config.py` - `validate_config()` method reads `SESSION_PROCESSOR_PORT` and converts to int

---

## Container: session-storage

**Port:** 8082

### Required Environment Variables

| Variable | Source | Description | Default |
|----------|--------|-------------|---------|
| `SESSION_STORAGE_PORT` | docker-compose environment | Service port | `8082` |
| `SESSION_STORAGE_HOST` | docker-compose environment | Service hostname (for URLs) | `session-storage` |
| `MONGODB_URL` | `.env.foundation`, `.env.core` | MongoDB connection URL | **Required** |
| `REDIS_URL` | `.env.foundation`, `.env.core` | Redis connection URL | **Required** |
| `ELASTICSEARCH_URL` | `.env.foundation`, `.env.core` | Elasticsearch connection URL | Optional |
| `SESSION_STORAGE_WORKERS` | docker-compose environment | Uvicorn workers | `1` |

### Configuration Files
- `sessions/storage/main.py` - Reads `SESSION_STORAGE_PORT` and always binds to `0.0.0.0`
- `sessions/storage/session_storage.py` - `SessionStorage.__init__` validates `MONGODB_URL`/`MONGO_URL` and `REDIS_URL`

---

## Container: session-api

**Port:** 8087

### Required Environment Variables

| Variable | Source | Description | Default |
|----------|--------|-------------|---------|
| `SESSION_API_PORT` | docker-compose environment | Service port | `8087` |
| `SESSION_API_HOST` | docker-compose environment | Service hostname (for URLs) | `session-api` |
| `MONGODB_URL` | `.env.foundation`, `.env.core` | MongoDB connection URL | **Required** |
| `REDIS_URL` | `.env.foundation`, `.env.core` | Redis connection URL | **Required** |
| `ELASTICSEARCH_URL` | `.env.foundation`, `.env.core` | Elasticsearch connection URL | Optional |
| `API_GATEWAY_URL` | `.env.core`, `.env.application` | API gateway URL | Optional |
| `BLOCKCHAIN_ENGINE_URL` | `.env.core`, `.env.application` | Blockchain engine URL | Optional |
| `SESSION_API_WORKERS` | docker-compose environment | Uvicorn workers | `1` |

### Configuration Files
- `sessions/api/main.py` - Reads `SESSION_API_PORT` and always binds to `0.0.0.0`
- `sessions/api/session_api.py` - `SessionAPI.__init__` validates `MONGODB_URL`/`MONGO_URL` and `REDIS_URL`
- `sessions/api/routes.py` - `get_session_api()` dependency validates environment variables

---

## Common Patterns

### Port Configuration
- All containers read port from environment: `{SERVICE}_PORT`
- All containers bind to `0.0.0.0` (all interfaces) - **NOT** from environment variable
- Port numbers in code are defaults only, always overridden by environment variables

### Host Configuration
- `{SERVICE}_HOST` is the service name for URL construction (e.g., `http://session-pipeline:8087`)
- Bind address is **always** `0.0.0.0` in containers (not configurable)
- Service names should match docker-compose service names

### Database URLs
- Use `MONGODB_URL` (preferred) or `MONGO_URL` (fallback)
- Both variables are checked in initialization code
- URLs must **NOT** contain `localhost` or `127.0.0.1` - use service names instead
- Validation errors are raised if URLs use localhost or are missing

### Environment Variable Sources
All environment variables come from docker-compose `env_file` sections:
1. `.env.secrets` - Secret keys, passwords, encryption keys
2. `.env.foundation` - Foundation service URLs (MongoDB, Redis, Elasticsearch)
3. `.env.core` - Core service URLs (API Gateway, Blockchain Engine)
4. `.env.application` - Application-specific configuration

Docker-compose `environment` section overrides/adds:
- Service-specific ports (`SESSION_*_PORT`)
- Service-specific hosts (`SESSION_*_HOST`)
- Service URLs (`SESSION_*_URL`)

### Validation Rules
1. **Required variables must be set** - Validation raises `ValueError` if missing
2. **No localhost URLs** - Validation raises `ValueError` if URLs contain `localhost` or `127.0.0.1`
3. **Ports must be integers** - Port strings are converted to int with error handling
4. **Secrets must not be placeholders** - Validation checks for placeholder strings

---

## Consistency Checklist

✅ **Ports**: All containers use environment variables for ports  
✅ **Hosts**: All containers bind to `0.0.0.0` (hardcoded, correct for containers)  
✅ **Database URLs**: All containers validate `MONGODB_URL`/`MONGO_URL` and `REDIS_URL`  
✅ **Import paths**: All containers use consistent relative imports  
✅ **Error handling**: All containers validate environment variables with clear error messages  
✅ **Default values**: Default ports match docker-compose defaults  

---

## Notes

1. **Bind Address**: The bind address (`0.0.0.0`) is hardcoded because containers must listen on all interfaces to accept connections from Docker network.

2. **Service Names vs Bind Address**: 
   - `SESSION_*_HOST` = Service name (e.g., `session-pipeline`) - used for URL construction
   - Bind address = Always `0.0.0.0` - used for uvicorn `host` parameter

3. **Port Conflicts**: 
   - `session-pipeline` and `session-api` both use port 8087 (different containers, different services)

4. **Environment Variable Names**:
   - Use `MONGODB_URL` (not `MONGO_URI` or `MONGODB_URI`)
   - Use `REDIS_URL` (not `REDIS_URI`)
   - Use `{SERVICE}_PORT` pattern (not `{SERVICE}_SERVICE_PORT`)

