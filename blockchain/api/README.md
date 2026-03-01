# Blockchain API

This is the API layer for the `lucid_blocks` blockchain system, implementing the OpenAPI 3.0 specification with PoOT (Proof of Observation Time) consensus.

## Features

- **FastAPI Application**: Modern, fast web framework with automatic OpenAPI documentation
- **Authentication & Authorization**: JWT-based authentication with role-based access control
- **Rate Limiting**: Configurable rate limiting for different API endpoint categories
- **Request Logging**: Comprehensive request/response logging
- **Service Layer**: Clean separation of business logic from API endpoints
- **Pydantic Models**: Type-safe request/response validation
- **Distroless Docker**: Secure containerized deployment

## API Endpoints

### Blockchain Information
- `GET /api/v1/chain/info` - Get blockchain network information
- `GET /api/v1/chain/status` - Get blockchain status and health
- `GET /api/v1/chain/height` - Get current block height
- `GET /api/v1/chain/network` - Get network topology and peers

### Block Management
- `GET /api/v1/blocks/` - List blocks with pagination
- `GET /api/v1/blocks/{block_id}` - Get block by ID or hash
- `GET /api/v1/blocks/height/{height}` - Get block by height
- `GET /api/v1/blocks/latest` - Get latest block
- `POST /api/v1/blocks/validate` - Validate block structure

### Transaction Processing
- `POST /api/v1/transactions/` - Submit transaction
- `GET /api/v1/transactions/{tx_id}` - Get transaction details
- `GET /api/v1/transactions/pending` - List pending transactions
- `POST /api/v1/transactions/batch` - Submit batch transactions

### Session Anchoring
- `POST /api/v1/anchoring/session` - Anchor session manifest
- `GET /api/v1/anchoring/session/{session_id}` - Get anchoring status
- `POST /api/v1/anchoring/verify` - Verify session anchoring
- `GET /api/v1/anchoring/status` - Get anchoring service status

### Consensus Mechanism
- `GET /api/v1/consensus/status` - Get consensus status
- `GET /api/v1/consensus/participants` - List consensus participants
- `POST /api/v1/consensus/vote` - Submit consensus vote
- `GET /api/v1/consensus/history` - Get consensus history

### Merkle Tree Operations
- `POST /api/v1/merkle/build` - Build Merkle tree
- `GET /api/v1/merkle/{root_hash}` - Get Merkle tree details
- `POST /api/v1/merkle/verify` - Verify Merkle proof
- `GET /api/v1/merkle/validation/{session_id}` - Get validation status

## Quick Start

### Prerequisites
- Python 3.11+
- MongoDB
- Redis (optional, for rate limiting)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```bash
   export DATABASE_URL="mongodb://localhost:27017/lucid_blockchain"
   export REDIS_URL="redis://localhost:6379/0"
   export SECRET_KEY="your-secret-key-here"
   ```

4. Run the application:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8084 --reload
   ```

### Docker Deployment

1. Build the image:
   ```bash
   docker build -t lucid-blockchain-api .
   ```

2. Run the container:
   ```bash
   docker run -p 8084:8084 \
     -e DATABASE_URL="mongodb://mongodb:27017/lucid_blockchain" \
     -e REDIS_URL="redis://redis:6379/0" \
     lucid-blockchain-api
   ```

## API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8084/api/v1/docs
- **ReDoc**: http://localhost:8084/api/v1/redoc
- **OpenAPI Spec**: http://localhost:8084/api/v1/openapi.json

## Configuration

The application uses environment variables for configuration. See `app/config.py` for all available settings.

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
isort .
```

### Type Checking
```bash
mypy app/
```

## Architecture

The API follows a clean architecture pattern:

```
app/
├── main.py              # FastAPI application entry point
├── config.py            # Configuration settings
├── dependencies.py      # FastAPI dependencies
├── routes.py            # Route registration
├── middleware/          # Custom middleware
│   ├── auth.py         # Authentication middleware
│   ├── rate_limit.py   # Rate limiting middleware
│   └── logging.py      # Request logging middleware
├── routers/             # API route handlers
│   ├── blockchain.py   # Blockchain information endpoints
│   ├── blocks.py       # Block management endpoints
│   ├── transactions.py # Transaction processing endpoints
│   ├── anchoring.py    # Session anchoring endpoints
│   ├── consensus.py    # Consensus mechanism endpoints
│   └── merkle.py       # Merkle tree operation endpoints
├── schemas/             # Pydantic models
│   ├── blockchain.py   # Blockchain information models
│   ├── block.py        # Block management models
│   ├── transaction.py  # Transaction processing models
│   ├── anchoring.py    # Session anchoring models
│   ├── consensus.py    # Consensus mechanism models
│   └── merkle.py       # Merkle tree operation models
└── services/            # Business logic layer
    ├── blockchain_service.py # Blockchain information service
    ├── block_service.py      # Block management service
    ├── transaction_service.py # Transaction processing service
    ├── anchoring_service.py   # Session anchoring service
    ├── consensus_service.py   # Consensus mechanism service
    └── merkle_service.py      # Merkle tree operation service
```

## Security

- **Authentication**: JWT-based authentication with configurable expiration
- **Authorization**: Role-based access control with permission checking
- **Rate Limiting**: Configurable rate limits per endpoint category
- **CORS**: Configurable Cross-Origin Resource Sharing
- **Input Validation**: Pydantic models for request/response validation
- **Error Handling**: Comprehensive error handling with proper HTTP status codes

## Monitoring

The application includes:
- Request/response logging
- Health check endpoints
- Prometheus metrics (optional)
- Error tracking and reporting

## License

This project is part of the Lucid Blockchain system.
