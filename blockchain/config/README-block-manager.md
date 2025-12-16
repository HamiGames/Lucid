# Block Manager Configuration Files

This directory contains comprehensive configuration files for the block-manager container, centralizing operational settings and aligning with docker-compose.core.yml.

## Configuration Files

### Core Configuration

1. **block-manager-config.yaml** - Main configuration file
   - Service settings (host, port, URL)
   - Dependencies (MongoDB, Redis, blockchain-engine)
   - Storage paths and permissions
   - Logging configuration
   - Synchronization settings
   - API endpoints
   - Rate limiting
   - Security settings
   - Monitoring configuration

2. **block-manager-config.json** - JSON version for tooling/UI
   - Same structure as YAML
   - Useful for JavaScript/TypeScript tooling
   - Environment variable substitution supported

### Supporting Configuration

3. **block-manager-logging.yaml** - Logging configuration
   - Formatters (standard, detailed, JSON)
   - Handlers (console, file, error_file)
   - Logger levels and propagation
   - Log rotation settings
   - Aligns with `/app/logs` volume mount

4. **block-manager-errors.yaml** - Error handling configuration
   - Retry policies
   - MongoDB connection error handling
   - Blockchain engine communication errors
   - Block storage error handling
   - Synchronization error recovery
   - Validation error policies
   - Error codes and severity levels

### Python Modules

5. **block_manager_config.py** - Configuration loader
   - `load_block_manager_config()` - Load configuration from YAML
   - `get_block_manager_config()` - Get global config instance
   - `BlockManagerConfig` - Dataclass with all config sections
   - Type-safe configuration access

6. **block_manager_runtime.py** - Runtime utilities
   - `setup_block_manager_runtime()` - Initialize runtime from config
   - `get_error_config()` - Load error handling config
   - `get_runtime_env()` - Get environment variables from config
   - `validate_config()` - Validate configuration

## Usage

### Basic Usage

```python
from blockchain.config.block_manager_config import get_block_manager_config

# Get configuration
config = get_block_manager_config()

# Access service settings
print(f"Service: {config.service.host}:{config.service.port}")
print(f"Storage: {config.storage.blocks_path}")

# Access dependencies
print(f"MongoDB: {config.dependencies.mongodb_url}")
print(f"Engine: {config.dependencies.blockchain_engine_url}")
```

### Runtime Setup

```python
from blockchain.config.block_manager_runtime import setup_block_manager_runtime

# Set up runtime (configures logging and storage)
config = setup_block_manager_runtime()

# Configuration is now applied
```

### Integration with BlockManagerService

```python
from blockchain.config.block_manager_config import get_block_manager_config
from blockchain.manager.service import BlockManagerService

# Load configuration
config = get_block_manager_config()

# Use config values
storage_path = Path(config.storage.blocks_path)
engine_url = config.synchronization.engine_url

# Initialize service with config
service = BlockManagerService()
# Service will use environment variables, which can be set from config
```

## Docker Compose Alignment

All configuration files align with `docker-compose.core.yml`:

- **Port**: 8086 (BLOCK_MANAGER_PORT)
- **Host**: block-manager (BLOCK_MANAGER_HOST)
- **Volumes**:
  - `/app/data` → `/mnt/myssd/Lucid/Lucid/data/block-manager`
  - `/app/logs` → `/mnt/myssd/Lucid/Lucid/logs/block-manager`
  - `/tmp/blocks` → named volume `block-manager-cache`
- **User**: 65532:65532
- **Dependencies**: MongoDB, Redis, blockchain-engine

## Environment Variable Substitution

Configuration files support environment variable substitution:

```yaml
service:
  host: "${BLOCK_MANAGER_HOST:-block-manager}"
  port: ${BLOCK_MANAGER_PORT:-8086}
```

- `${VAR_NAME}` - Required variable
- `${VAR_NAME:-default}` - Optional with default value

## Configuration Validation

```python
from blockchain.config.block_manager_runtime import validate_config

# Validate configuration
if not validate_config():
    raise RuntimeError("Invalid block manager configuration")
```

## Error Handling

Error configuration is loaded separately:

```python
from blockchain.config.block_manager_runtime import get_error_config

error_config = get_error_config()
retry_config = error_config.get("error_handling", {}).get("retry", {})
max_retries = retry_config.get("max_retries", 3)
```

## Logging Configuration

Logging is automatically configured when using `setup_block_manager_runtime()`:

```python
from blockchain.config.block_manager_runtime import setup_block_manager_runtime

# This automatically sets up logging from block-manager-logging.yaml
config = setup_block_manager_runtime(apply_logging=True)
```

## File Locations

All configuration files are in `blockchain/config/`:

- `block-manager-config.yaml` - Main config
- `block-manager-config.json` - JSON version
- `block-manager-logging.yaml` - Logging config
- `block-manager-errors.yaml` - Error handling config
- `block_manager_config.py` - Python loader
- `block_manager_runtime.py` - Runtime utilities

## Integration with BlockchainConfig

The block-manager configuration is also available through the main `BlockchainConfig`:

```python
from blockchain.config.config import get_blockchain_config

config = get_blockchain_config()
block_manager_config = config.get_block_manager_config()
```

## Notes

- All paths align with docker-compose volume mounts
- Configuration supports environment variable substitution
- Type-safe access through dataclasses
- Validation ensures required fields are present
- Runtime setup handles logging and storage initialization
- Error handling configuration is separate for flexibility

