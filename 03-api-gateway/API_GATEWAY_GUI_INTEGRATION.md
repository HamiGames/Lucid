# API Gateway - GUI API Bridge Integration

## Summary

Added complete api-gui-bridge integration support to the api-gateway container. The api-gateway now includes configuration, routing, and proxy support for the gui-api-bridge service.

## Changes Made

### 1. Configuration Layer
**File:** `03-api-gateway/api/app/config.py`

**Added:**
- `GUI_API_BRIDGE_URL` field - Environment variable for gui-api-bridge service URL
- `validate_gui_api_bridge_url()` validator - Validates GUI bridge URL configuration
- Optional configuration (no crash if not set, with warning if misconfigured)

### 2. Main Application
**File:** `03-api-gateway/api/app/main.py`

**Added:**
- Import of `gui` router module
- Registration of gui router with prefix `/api/v1/gui` and tag `GUI Bridge`
- Startup logging for `GUI_API_BRIDGE_URL`

### 3. GUI Router Endpoints
**File:** `03-api-gateway/api/app/routers/gui.py` (NEW)

**Endpoints Implemented:**
- `GET /api/v1/gui/info` - Get GUI Bridge service information
- `GET /api/v1/gui/health` - Check GUI Bridge health status
- `GET /api/v1/gui/status` - Get GUI Bridge connection status
- `POST /api/v1/gui/electron/connect` - Handle Electron GUI connection
- `POST /api/v1/gui/electron/disconnect` - Handle Electron GUI disconnection
- `GET /api/v1/gui/electron/routes` - List available GUI routes

**Request Models:**
- `ElectronConnectionRequest` - Connection data with session_id, client_version, platform
- `ElectronDisconnectionRequest` - Disconnection data with session_id

### 4. GUI Bridge Service
**File:** `03-api-gateway/services/gui_bridge_service.py` (NEW)

**Features:**
- `GuiBridgeService` class for managing GUI Bridge integration
- Health checks and connectivity monitoring
- Proxy request handling to gui-api-bridge
- Electron GUI connection/disconnection lifecycle management
- Error handling with `GuiBridgeServiceError`

**Methods:**
- `initialize()` - Initialize HTTP session
- `close()` - Close HTTP session
- `health_check()` - Check service health
- `get_bridge_info()` - Get service information
- `handle_electron_connect()` - Handle GUI connection
- `handle_electron_disconnect()` - Handle GUI disconnection
- `proxy_gui_request()` - Generic proxy request method

### 5. Proxy Service Update
**File:** `03-api-gateway/services/proxy_service.py`

**Updated:**
- Added `gui` service to `service_urls` dictionary
- Changed to use correct config field names:
  - `blockchain` → `BLOCKCHAIN_CORE_URL`
  - `session` → `SESSION_MANAGEMENT_URL`
  - `tron` → `TRON_PAYMENT_URL`
  - `gui` → `GUI_API_BRIDGE_URL` (NEW)

### 6. Meta Router Update
**File:** `03-api-gateway/api/app/routers/meta.py`

**Updated:**
- Added `gui_api_bridge` to dependencies health check dictionary

## Environment Configuration

**Required Environment Variable:**
```bash
GUI_API_BRIDGE_URL=http://gui-api-bridge:8102
```

**Example Docker Compose Entry:**
```yaml
environment:
  - GUI_API_BRIDGE_URL=http://gui-api-bridge:8102
```

## API Gateway Endpoint Summary

### All Registered Endpoints

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| Meta | `/api/v1/meta` | `/info`, `/health`, `/version`, `/metrics` |
| Auth | `/api/v1/auth` | `/login`, `/verify`, `/refresh`, `/logout`, `/status` |
| Users | `/api/v1/users` | `/me`, `/{user_id}`, `POST /` |
| Sessions | `/api/v1/sessions` | `/`, `/{session_id}` (CRUD) |
| Manifests | `/api/v1/manifests` | `/`, `/{manifest_id}` |
| Trust | `/api/v1/trust` | `/policies`, `/policies/{policy_id}` |
| Chain | `/api/v1/chain` | `/info`, `/blocks`, `/blocks/{block_id}`, `/transactions` |
| Wallets | `/api/v1/wallets` | `/`, `/{wallet_id}`, `/{wallet_id}/transactions` |
| **GUI Bridge** | **`/api/v1/gui`** | **`/info`, `/health`, `/status`, `/electron/connect`, `/electron/disconnect`, `/electron/routes`** |

## Health Check Dependencies

The meta health check endpoint now monitors:
- mongodb
- redis
- blockchain_core
- tron_payment
- **gui_api_bridge** (NEW)

## Service Architecture

```
┌─────────────────────────────────────────┐
│        Electron GUI Application         │
└────────────────┬────────────────────────┘
                 │
                 ↓
         ┌───────────────┐
         │ gui-api-bridge│ (Port 8102)
         └───────┬───────┘
                 │
                 ↓
    ┌────────────────────────────┐
    │     API Gateway            │
    │  /api/v1/gui/* endpoints   │
    │    (Port 8080)             │
    └────────────────────────────┘
         │         │        │        │
         ↓         ↓        ↓        ↓
    ┌────────┐ ┌──────┐ ┌──────┐ ┌──────┐
    │MongoDB │ │Redis │ │Auth  │ │Chain │
    └────────┘ └──────┘ └──────┘ └──────┘
```

## Integration Testing

To test the GUI Bridge integration:

1. **Health Check:**
   ```bash
   curl http://api-gateway:8080/api/v1/gui/health
   ```

2. **Bridge Info:**
   ```bash
   curl http://api-gateway:8080/api/v1/gui/info
   ```

3. **Bridge Status:**
   ```bash
   curl http://api-gateway:8080/api/v1/gui/status
   ```

4. **Electron Connection:**
   ```bash
   curl -X POST http://api-gateway:8080/api/v1/gui/electron/connect \
     -H "Content-Type: application/json" \
     -d '{"session_id":"test","client_version":"1.0","platform":"linux"}'
   ```

## Dependencies

- aiohttp (for HTTP proxy requests)
- FastAPI (already included)
- Pydantic (already included)

## Error Handling

- Missing `GUI_API_BRIDGE_URL` - Service returns warning, operates without GUI Bridge
- Bridge service unavailable - Returns 503 Service Unavailable
- Connection issues - Returns appropriate HTTP error codes with descriptive messages
- Network timeouts - Handled gracefully with error response

## Future Enhancements

- WebSocket support for real-time GUI updates
- Circuit breaker pattern for GUI service failures
- Caching of GUI Bridge responses
- GUI-specific rate limiting
- Role-based access control for GUI endpoints
