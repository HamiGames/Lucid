# Lucid API Gateway

**Cluster ID**: 01-api-gateway-cluster  
**Service Type**: Entry point and routing layer  
**Container Type**: Distroless (gcr.io/distroless/python3-debian12)

## Overview

The API Gateway serves as the primary entry point for all external API requests to the Lucid blockchain system, providing:

- Request routing and load balancing
- JWT-based authentication and authorization
- Rate limiting and DDoS protection
- SSL/TLS termination
- Request/response transformation
- Audit logging and monitoring

## Architecture

### Service Structure

```
lucid_blocks (on-chain blockchain) ─┐
                                    ├─> API Gateway ─> External Clients
TRON Payment (isolated service) ────┘
```

**Important**: 
- `lucid_blocks`: On-chain blockchain system for session data and manifests
- `TRON`: Isolated payment service for USDT/TRX transactions (NOT part of lucid_blocks)

## Directory Structure

```
03-api-gateway/
├── Dockerfile                    # Distroless multi-stage build
├── docker-compose.yml           # Docker Compose configuration
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables example
├── api/
│   └── app/
│       ├── main.py             # FastAPI application entry point
│       ├── config.py           # Configuration management
│       ├── middleware/         # Custom middleware
│       ├── routers/            # API route handlers
│       ├── services/           # Business logic services
│       ├── models/             # Data models
│       ├── database/           # Database layer
│       └── utils/              # Utility functions
├── gateway/                    # Gateway configuration
├── scripts/                    # Deployment scripts
└── docs/                       # Documentation

```

## Quick Start

### Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- Python 3.11+ (for local development)

### Setup

1. **Clone the repository**:
   ```bash
   cd 03-api-gateway
   ```

2. **Copy environment file**:
   ```bash
   cp .env.example .env
   ```

3. **Update environment variables** in `.env`:
   - Set `JWT_SECRET_KEY` (minimum 32 characters)
   - Set `MONGO_PASSWORD`
   - Set `REDIS_PASSWORD`
   - Configure backend service URLs

4. **Build and run**:
   ```bash
   docker-compose up -d
   ```

5. **Verify health**:
   ```bash
   curl http://localhost:8080/api/v1/meta/health
   ```

## Development

### Local Development Setup

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run locally**:
   ```bash
   cd api
   python -m app.main
   ```

### Testing

```bash
pytest api/tests/
```

## Configuration

### Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_NAME` | Service identifier | `api-gateway` |
| `HTTP_PORT` | HTTP port | `8080` |
| `HTTPS_PORT` | HTTPS port | `8081` |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `MONGODB_URI` | MongoDB connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `BLOCKCHAIN_CORE_URL` | lucid_blocks service URL | Required |
| `TRON_PAYMENT_URL` | TRON payment service URL | Required |

See `.env.example` for complete list.

## API Documentation

When `DEBUG=true`, interactive API documentation is available at:

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- OpenAPI Spec: `http://localhost:8080/openapi.json`

## Deployment

### Build Distroless Container

```bash
./scripts/build.sh
```

### Deploy to Production

```bash
./scripts/deploy.sh
```

### Deploy to Raspberry Pi (via SSH)

```bash
# From Windows 11 build host
./scripts/deploy-pi.sh
```

## Security

- **Distroless container**: Minimal attack surface
- **Non-root user**: Runs as UID 65532
- **JWT authentication**: Secure token-based auth
- **Rate limiting**: Protection against abuse
- **TLS 1.3**: Encrypted communications
- **Input validation**: Comprehensive request validation

## Monitoring

### Health Checks

- Service: `GET /api/v1/meta/health`
- Version: `GET /api/v1/meta/version`
- Metrics: `GET /api/v1/meta/metrics` (authenticated)

### Logs

Logs are written to stdout in JSON format and can be viewed with:

```bash
docker-compose logs -f api-gateway
```

## Troubleshooting

### Service won't start

1. Check logs: `docker-compose logs api-gateway`
2. Verify environment variables in `.env`
3. Ensure MongoDB and Redis are running
4. Check port availability (8080, 8081)

### Authentication failures

1. Verify `JWT_SECRET_KEY` is set and consistent
2. Check token expiration settings
3. Review auth service logs

### Rate limiting issues

1. Check Redis connectivity
2. Verify `RATE_LIMIT_ENABLED` setting
3. Review rate limit configuration

## Support

For issues and questions:
- GitHub Issues: [HamiGames/Lucid](https://github.com/HamiGames/Lucid)
- Documentation: `plan/API_plans/01-api-gateway-cluster/`

## License

MIT License - See LICENSE file for details

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-14  
**Build Host**: Windows 11 console  
**Target Host**: Raspberry Pi

