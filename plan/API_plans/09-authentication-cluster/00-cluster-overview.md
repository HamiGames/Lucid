# Authentication Cluster Overview

## Architecture Summary

The Authentication Cluster provides comprehensive user authentication, authorization, and session management for the Lucid RDP system. This cluster implements TRON address-based authentication with hardware wallet support and role-based access control.

## Service Components

### Core Services
- **Authentication Service** (`auth/authentication_service.py`) - Primary authentication engine
- **User Manager** (`auth/user_manager.py`) - User lifecycle and profile management  
- **Hardware Wallet Integration** (`auth/hardware_wallet.py`) - Ledger/Trezor/KeepKey support
- **Session Manager** (`auth/session_manager.py`) - JWT token and session handling
- **Permission Engine** (`auth/permissions.py`) - Role-based access control

## Port Configuration

- **Primary Port**: 8090 (Authentication API)
- **Health Check**: 8090/health
- **Metrics**: 8090/metrics
- **Admin API**: 8090/admin (internal only)

## Service Dependencies

### Internal Dependencies
- **MongoDB** (port 27017) - User data and session storage
- **Redis** (port 6379) - Token blacklist and rate limiting
- **TRON Node** (port 8091) - Address verification

### External Dependencies  
- **Hardware Wallets** - Ledger, Trezor, KeepKey devices
- **Email Service** - Magic link delivery
- **SMS Gateway** - TOTP verification

## API Categories

### Authentication APIs
- POST /auth/login - TRON signature authentication
- POST /auth/refresh - Token refresh
- POST /auth/logout - Token invalidation
- POST /auth/verify-ownership - Session ownership verification

### User Management APIs
- GET /auth/profile - User profile information
- PUT /auth/profile - Update profile
- GET /auth/permissions - User permissions
- GET /auth/active-sessions - Active sessions

### Hardware Wallet APIs
- POST /auth/hardware-wallet/verify - Hardware wallet verification
- GET /auth/hardware-wallet/status - Wallet connection status
- POST /auth/hardware-wallet/challenge - Challenge generation

## Security Features

### Authentication Security
- TRON signature verification with Ed25519
- JWT tokens (1hr access, 7day refresh)
- Account lockout after failed attempts
- Hardware wallet integration

### Authorization Security
- Role-based access control (User, Admin, Node)
- Permission-based endpoint access
- Session ownership verification
- Audit logging for all operations

## Integration Points

### Cross-Cluster Communication
- **API Gateway** - Authentication proxy and rate limiting
- **Admin Interface** - User management and role assignment
- **Session Management** - Session ownership validation
- **TRON Payment** - Wallet verification for payments

## Container Configuration

### Base Image
```dockerfile
FROM gcr.io/distroless/python3-debian11
```

### Environment Variables
- `LUCID_AUTH_SECRET_KEY` - JWT signing key
- `LUCID_AUTH_TOKEN_EXPIRE_MINUTES` - Token expiration
- `LUCID_AUTH_HARDWARE_WALLET_ENABLED` - Hardware wallet support
- `LUCID_AUTH_RATE_LIMIT_PER_MINUTE` - Rate limiting

## Health Monitoring

### Health Check Endpoints
- GET /health - Basic service health
- GET /health/auth - Authentication service status
- GET /health/hardware-wallet - Hardware wallet connectivity
- GET /health/database - Database connectivity

### Metrics Collected
- Authentication attempts (success/failure)
- Token refresh frequency
- Hardware wallet usage
- Session creation/destruction rates
