# Phase 3 Integration Tests

This directory contains the Phase 3 Integration Tests as specified in Step 38 of the Build Requirements Guide. These tests validate the complete integration between all major components of the Lucid system.

## Test Structure

### Core Test Files

- **`conftest.py`** - Common fixtures and test configuration
- **`test_session_lifecycle.py`** - Full session lifecycle testing
- **`test_rdp_creation.py`** - RDP server dynamic creation testing
- **`test_node_registration.py`** - Node registration and pool assignment testing
- **`test_poot_calculation.py`** - PoOT score calculation testing

### Test Categories

#### 1. Session Lifecycle Tests (`test_session_lifecycle.py`)
- **Full Session Workflow**: Create → Record → Process → Anchor
- **Session State Management**: State transitions and validation
- **Pipeline Integration**: Recording pipeline and chunk processing
- **Error Handling**: Session failures and recovery
- **Concurrent Sessions**: Multiple simultaneous sessions
- **Session Statistics**: Performance metrics and reporting

#### 2. RDP Server Creation Tests (`test_rdp_creation.py`)
- **Dynamic RDP Creation**: On-demand server provisioning
- **RDP Lifecycle Management**: Start, stop, and delete operations
- **Resource Management**: CPU, memory, and storage allocation
- **Connection Testing**: RDP connectivity and authentication
- **Concurrent RDP Servers**: Multiple simultaneous servers
- **RDP Statistics**: Resource usage and performance metrics

#### 3. Node Registration Tests (`test_node_registration.py`)
- **Node Registration**: Hardware validation and registration
- **Pool Assignment**: Node-to-pool assignment and management
- **Resource Monitoring**: CPU, memory, and network monitoring
- **Concurrent Registration**: Multiple simultaneous node registrations
- **Hardware Validation**: Hardware requirements and validation
- **Node Statistics**: Pool statistics and reporting

#### 4. PoOT Calculation Tests (`test_poot_calculation.py`)
- **PoOT Score Calculation**: Score calculation algorithms
- **PoOT Validation**: Data validation and scoring
- **Batch Processing**: Batch PoOT validation and processing
- **Payout Processing**: PoOT payout calculation and processing
- **Integration with Sessions**: Session-based PoOT generation
- **PoOT Statistics**: Performance metrics and reporting

## Test Configuration

### Environment Setup

The tests use the following configuration:

```python
# Test database configuration
TEST_DATABASE_URL = "mongodb://localhost:27017/lucid_test_db"
TEST_REDIS_URL = "redis://localhost:6379/1"

# Test API endpoints
SESSION_API_BASE_URL = "http://localhost:8000/api/v1/sessions"
RDP_API_BASE_URL = "http://localhost:8000/api/v1/rdp"
NODE_API_BASE_URL = "http://localhost:8000/api/v1/nodes"
POOT_API_BASE_URL = "http://localhost:8000/api/v1/poot"
```

### Fixtures

The tests use the following key fixtures:

- **`test_db`** - MongoDB test database connection
- **`test_redis`** - Redis test connection
- **`session_client`** - Session Management API client
- **`rdp_client`** - RDP Services API client
- **`node_client`** - Node Management API client
- **`auth_headers`** - Authentication headers
- **`sample_session_data`** - Sample session data
- **`sample_rdp_server_request`** - Sample RDP server data
- **`sample_node_data`** - Sample node registration data
- **`sample_poot_data`** - Sample PoOT data

## Running the Tests

### Prerequisites

1. **MongoDB**: Running on localhost:27017
2. **Redis**: Running on localhost:6379
3. **API Services**: All Lucid services running and accessible
4. **Test Data**: Sample data and test fixtures available

### Test Execution

```bash
# Run all Phase 3 integration tests
pytest tests/integration/phase3/ -v

# Run specific test categories
pytest tests/integration/phase3/test_session_lifecycle.py -v
pytest tests/integration/phase3/test_rdp_creation.py -v
pytest tests/integration/phase3/test_node_registration.py -v
pytest tests/integration/phase3/test_poot_calculation.py -v

# Run with specific markers
pytest tests/integration/phase3/ -m "session_lifecycle" -v
pytest tests/integration/phase3/ -m "rdp_creation" -v
pytest tests/integration/phase3/ -m "node_registration" -v
pytest tests/integration/phase3/ -m "poot_calculation" -v

# Run with coverage
pytest tests/integration/phase3/ --cov=app --cov-report=html
```

### Test Markers

The tests use the following markers for categorization:

- `@pytest.mark.phase3_integration` - Phase 3 integration tests
- `@pytest.mark.session_lifecycle` - Session lifecycle tests
- `@pytest.mark.rdp_creation` - RDP creation tests
- `@pytest.mark.node_registration` - Node registration tests
- `@pytest.mark.poot_calculation` - PoOT calculation tests

## Test Data

### Sample Session Data

```python
sample_session_data = {
    "name": "Test Session",
    "description": "Test session description",
    "rdp_config": {
        "host": "192.168.1.100",
        "port": 3389,
        "username": "testuser",
        "domain": "TESTDOMAIN",
        "use_tls": True,
        "ignore_cert": False
    },
    "recording_config": {
        "frame_rate": 30,
        "resolution": "1920x1080",
        "quality": "high",
        "compression": "zstd",
        "audio_enabled": True,
        "cursor_enabled": True
    },
    "storage_config": {
        "retention_days": 30,
        "max_size_gb": 10,
        "encryption_enabled": True,
        "compression_enabled": True,
        "backup_enabled": False,
        "archive_enabled": False
    },
    "metadata": {
        "project": "lucid-rdp",
        "environment": "test",
        "tags": ["test", "automated"],
        "owner": "test-user-123",
        "priority": "normal"
    }
}
```

### Sample RDP Server Data

```python
sample_rdp_server_request = {
    "name": "Test RDP Server",
    "description": "A dynamically created RDP server for testing.",
    "user_id": "test-user-123",
    "configuration": {
        "desktop_environment": "xfce",
        "resolution": "1920x1080",
        "color_depth": 24
    },
    "resources": {
        "cpu_limit": 2.0,
        "memory_limit": 4096,
        "disk_limit": 20480,
        "network_bandwidth": 1000
    }
}
```

### Sample Node Data

```python
sample_node_data = {
    "name": "test-node-001",
    "node_type": "worker",
    "hardware_info": {
        "cpu": {"cores": 8, "frequency_mhz": 3200, "architecture": "x86_64"},
        "memory": {"total_bytes": 17179869184, "type": "DDR4"},
        "storage": {"total_bytes": 1099511627776, "type": "SSD"},
        "gpu": {"model": "NVIDIA RTX 3080", "memory_bytes": 10737418240},
        "network": [{"interface": "eth0", "speed_mbps": 1000}]
    },
    "location": {"country": "US", "region": "CA"},
    "initial_pool_id": "pool_workers",
    "configuration": {"max_sessions": 10}
}
```

### Sample PoOT Data

```python
sample_poot_data = {
    "node_id": "test-node-001",
    "output_data": "base64_encoded_output_data_for_poot",
    "timestamp": "2024-01-01T00:00:00Z",
    "nonce": "unique_nonce_for_poot_validation"
}
```

## Test Scenarios

### 1. Full Session Lifecycle

1. **Create Session**: Create a new session with configuration
2. **Start Recording**: Begin session recording
3. **Process Chunks**: Simulate chunk processing
4. **Stop Recording**: End session recording
5. **Verify Statistics**: Check session statistics and metrics

### 2. RDP Server Dynamic Creation

1. **Create RDP Server**: Dynamically create RDP server
2. **Start Server**: Start the RDP server
3. **Test Connection**: Verify RDP connectivity
4. **Stop Server**: Stop the RDP server
5. **Delete Server**: Remove the RDP server

### 3. Node Registration and Pool Assignment

1. **Register Node**: Register node with hardware validation
2. **Assign to Pool**: Assign node to resource pool
3. **Start Node**: Activate the node
4. **Monitor Resources**: Track resource usage
5. **Stop Node**: Deactivate the node

### 4. PoOT Score Calculation

1. **Submit PoOT**: Submit PoOT data for validation
2. **Validate PoOT**: Run PoOT validation algorithm
3. **Calculate Score**: Compute PoOT score
4. **Process Payout**: Calculate and process payout
5. **Verify Results**: Confirm payout processing

## Integration Points

### Session Management ↔ RDP Services

- Session creation triggers RDP server provisioning
- RDP server status affects session recording
- Session statistics include RDP resource usage

### Session Management ↔ Node Management

- Session processing requires node resources
- Node status affects session availability
- Session statistics include node performance

### Node Management ↔ PoOT Calculation

- Node operations generate PoOT data
- PoOT scores affect node reputation
- PoOT payouts reward node operators

### RDP Services ↔ Node Management

- RDP servers run on registered nodes
- Node resources limit RDP server capacity
- RDP performance affects node PoOT scores

## Error Handling

The tests validate error handling for:

- **Network Failures**: API connectivity issues
- **Database Errors**: MongoDB and Redis failures
- **Authentication Errors**: Invalid or expired tokens
- **Resource Limits**: CPU, memory, and storage limits
- **Concurrent Access**: Race conditions and locking
- **Invalid Data**: Malformed requests and responses

## Performance Testing

The tests include performance validation for:

- **Response Times**: API endpoint response times
- **Throughput**: Concurrent request handling
- **Resource Usage**: CPU, memory, and network usage
- **Scalability**: System behavior under load
- **Latency**: End-to-end processing times

## Security Testing

The tests validate security aspects:

- **Authentication**: Token validation and expiration
- **Authorization**: Role-based access control
- **Data Validation**: Input sanitization and validation
- **Encryption**: Data encryption in transit and at rest
- **Audit Logging**: Security event logging

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

- **Automated Execution**: Run on code changes
- **Environment Isolation**: Separate test environments
- **Data Cleanup**: Automatic test data cleanup
- **Parallel Execution**: Concurrent test execution
- **Reporting**: Test results and coverage reporting

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure MongoDB and Redis are running
2. **API Services**: Verify all Lucid services are accessible
3. **Authentication**: Check token validity and permissions
4. **Resource Limits**: Monitor system resources during tests
5. **Network Issues**: Verify network connectivity between services

### Debug Mode

Run tests with debug output:

```bash
pytest tests/integration/phase3/ -v -s --log-cli-level=DEBUG
```

### Test Isolation

Ensure test isolation by:

- Using unique test data for each test
- Cleaning up test data after each test
- Using separate test databases
- Mocking external dependencies

## Future Enhancements

Planned improvements include:

- **Load Testing**: High-volume performance testing
- **Chaos Engineering**: Failure scenario testing
- **Security Testing**: Penetration testing scenarios
- **Monitoring Integration**: Test result monitoring
- **Automated Reporting**: Test result analysis and reporting
