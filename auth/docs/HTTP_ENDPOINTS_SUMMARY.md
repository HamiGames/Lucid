# Lucid Authentication Service - HTTP Endpoints Summary

## Overview

The Lucid Authentication Service now follows the service-mesh-controller pattern for HTTP endpoint design, ensuring consistency across the entire Lucid project. All HTTP endpoints are customizable via YAML configuration files.

## Created Modules

### 1. `auth/http_server.py`
- **Purpose**: HTTP server module following service-mesh-controller pattern
- **Features**:
  - Customizable endpoint configuration loading
  - Integration with FastAPI application
  - Background task management for uvicorn server
  - Custom route setup based on configuration

### 2. `auth/api/endpoint_config.py`
- **Purpose**: Endpoint configuration manager
- **Features**:
  - Loads endpoint configuration from YAML files
  - Provides methods to check endpoint enablement
  - Manages rate limits per endpoint
  - Handles authentication requirements
  - CORS, validation, and logging configuration

### 3. `auth/config/endpoints.yaml`
- **Purpose**: Customizable endpoint configuration file
- **Features**:
  - Enable/disable endpoints per group
  - Configure rate limits per endpoint
  - Set authentication requirements
  - Customize CORS, validation, and logging
  - Define sub-endpoint configurations

## HTTP Endpoints

### System Endpoints
- `GET /health` - Health check (Docker healthcheck)
- `GET /meta/info` - Service metadata and information
- `GET /` - API root endpoint

### Authentication Endpoints (`/auth`)
- `POST /auth/register` - Register new user with TRON signature
- `POST /auth/login` - Login with TRON signature (returns JWT tokens)
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout and revoke session
- `POST /auth/verify` - Verify JWT token validity

### User Management Endpoints (`/users`)
- `GET /users/me` - Get current authenticated user
- `GET /users/{user_id}` - Get user by ID (with permission check)
- `PUT /users/{user_id}` - Update user profile (with permission check)

### Session Management Endpoints (`/sessions`)
- `GET /sessions` - List all active sessions for current user
- `GET /sessions/{session_id}` - Get session by ID (with ownership check)
- `DELETE /sessions/{session_id}` - Revoke specific session
- `DELETE /sessions` - Revoke all sessions for current user

### Hardware Wallet Endpoints (`/hw`)
- `POST /hw/connect` - Connect hardware wallet (Ledger, Trezor, KeepKey)
- `POST /hw/sign` - Sign message with hardware wallet
- `GET /hw/status/{wallet_id}` - Get hardware wallet connection status
- `POST /hw/disconnect/{wallet_id}` - Disconnect hardware wallet

## Endpoint Customization

All endpoints can be customized via `auth/config/endpoints.yaml`:

### Enable/Disable Endpoints
```yaml
endpoints:
  auth:
    enabled: true  # Set to false to disable all auth endpoints
  users:
    enabled: true
  sessions:
    enabled: true
  hardware_wallet:
    enabled: true
```

### Configure Rate Limits
```yaml
endpoints:
  auth:
    rate_limit: 30  # 30 requests per minute
    sub_endpoints:
      login:
        rate_limit: 20  # 20 login attempts per minute
```

### Set Authentication Requirements
```yaml
endpoints:
  users:
    authentication_required: true
  sessions:
    authentication_required: true
```

### Customize CORS
```yaml
customization:
  cors:
    enabled: true
    allow_origins: ["*"]  # Configure per environment
    allow_credentials: true
    allow_methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
```

## Integration with Main Application

The endpoint configuration is integrated into:
1. **`auth/main.py`**: Routers are only included if endpoints are enabled
2. **`auth/middleware/rate_limit.py`**: Rate limits use endpoint-specific configuration
3. **`auth/http_server.py`**: Custom routes are set up based on configuration

## Alignment with Lucid Project

The authentication service endpoints align with:
- **API Gateway**: Uses `/api/v1` prefix pattern (auth service uses direct paths)
- **Blockchain Core**: Similar health/meta endpoint structure
- **Session Management**: Consistent session endpoint patterns
- **Service Mesh Controller**: Same HTTP server module pattern

## Configuration File Location

- **Endpoint Configuration**: `auth/config/endpoints.yaml`
- **RBAC Policies**: `auth/config/rbac-policies.yaml`
- **Rate Limit Rules**: `auth/config/rate-limit-rules.yaml`
- **Hardware Wallet Config**: `auth/config/hardware-wallet-config.yaml`
- **Service Mesh Config**: `auth/config/service-mesh-config.yaml`

## Usage

### Check if Endpoint is Enabled
```python
from auth.api.endpoint_config import get_endpoint_config

config = get_endpoint_config()
if config.is_endpoint_enabled("auth"):
    # Auth endpoints are enabled
    pass
```

### Get Endpoint Rate Limit
```python
rate_limit = config.get_endpoint_rate_limit("auth")  # Returns 30 or None
```

### Get CORS Configuration
```python
cors_config = config.get_cors_config()
```

### Reload Configuration
```python
config.reload_config()  # Reload from YAML file
```

## Next Steps

1. ✅ HTTP endpoints created and functional
2. ✅ Endpoint configuration system implemented
3. ✅ Integration with main application complete
4. ✅ Rate limiting uses endpoint configuration
5. ⏳ Hardware wallet endpoints need implementation (currently return 501)
6. ⏳ TRON signature verification needs implementation in register/login

## Notes

- All endpoints are now functional (except hardware wallet which requires device integration)
- Endpoints can be enabled/disabled via YAML configuration
- Rate limits are customizable per endpoint
- Authentication requirements are configurable
- Follows service-mesh-controller pattern for consistency

