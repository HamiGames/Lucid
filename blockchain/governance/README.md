# Lucid RDP Blockchain Governance - Timelock System

This module implements a comprehensive timelock governance system for the Lucid RDP blockchain, providing secure, time-delayed execution of governance proposals.

## Overview

The timelock governance system ensures that critical blockchain changes go through a proper review and delay period before execution, preventing immediate changes that could compromise system security.

## Features

- **Time-delayed Execution**: All proposals must wait for a specified delay period before execution
- **Multiple Execution Levels**: Normal, Urgent, Emergency, and Immediate execution levels
- **Proposal Types**: Support for various governance actions (parameter changes, contract upgrades, etc.)
- **Signature Requirements**: Configurable signature requirements per proposal type
- **Grace Periods**: Proposals expire after a grace period if not executed
- **Comprehensive Logging**: Full audit trail of all governance actions
- **MongoDB Integration**: Persistent storage of proposals and events

## Components

### Core Files

- `timelock.py` - Main timelock governance implementation
- `start_timelock.py` - Service startup script
- `test_timelock.py` - Comprehensive test suite
- `requirements.timelock.txt` - Python dependencies
- `timelock_config.json` - Configuration template

### Docker Files

- `Dockerfile.timelock` - Standard Docker image
- `Dockerfile.timelock.distroless` - Security-focused distroless image

### Deployment Scripts

- `deploy_timelock.ps1` - Windows PowerShell deployment script
- `deploy_timelock.sh` - Linux/Pi shell deployment script

## Proposal Types

| Type | Description | Default Signatures |
|------|-------------|-------------------|
| `PARAMETER_CHANGE` | Change system parameters | 1 |
| `CONTRACT_UPGRADE` | Upgrade smart contracts | 2 |
| `EMERGENCY_SHUTDOWN` | Emergency system shutdown | 3 |
| `KEY_ROTATION` | Rotate cryptographic keys | 2 |
| `NODE_PROVISIONING` | Add/remove nodes | 1 |
| `POLICY_UPDATE` | Update system policies | 1 |
| `FEE_ADJUSTMENT` | Adjust transaction fees | 1 |
| `CONSENSUS_CHANGE` | Change consensus mechanism | 3 |

## Execution Levels

| Level | Delay | Use Case |
|-------|-------|----------|
| `NORMAL` | 24 hours | Standard governance changes |
| `URGENT` | 4 hours | Important but not critical changes |
| `EMERGENCY` | 1 hour | Critical security fixes |
| `IMMEDIATE` | 0 seconds | Admin-only immediate changes |

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.timelock.txt
```

### 2. Configure MongoDB

Ensure MongoDB is running and accessible:

```bash
# Default connection
mongodb://lucid:lucid@127.0.0.1:27019/lucid?authSource=admin
```

### 3. Start the Service

```bash
# Using Python directly
python start_timelock.py

# Using deployment script (Linux/Pi)
./deploy_timelock.sh --test

# Using deployment script (Windows)
.\deploy_timelock.ps1 -Test
```

### 4. Run Tests

```bash
python test_timelock.py
```

## Configuration

### Environment Variables

- `MONGO_URI` - MongoDB connection string
- `LUCID_TIMELOCK_OUTPUT_DIR` - Output directory for data
- `LUCID_TIMELOCK_CONFIG_FILE` - Path to configuration file

### Configuration File

Create a `timelock_config.json` file:

```json
{
  "min_delay_seconds": 3600,
  "max_delay_seconds": 2592000,
  "default_grace_period": 604800,
  "max_grace_period": 2592000,
  "admin_addresses": [
    "TAdminAddress1",
    "TAdminAddress2"
  ],
  "emergency_addresses": [
    "TEmergencyAddress1"
  ],
  "required_signatures": {
    "parameter_change": 1,
    "contract_upgrade": 2,
    "emergency_shutdown": 3
  }
}
```

## API Usage

### Create a Proposal

```python
from timelock import TimelockGovernance, ProposalType, ExecutionLevel

# Create proposal
proposal_id = await timelock.create_proposal(
    proposal_type=ProposalType.PARAMETER_CHANGE,
    title="Increase Block Size",
    description="Increase maximum block size to 2MB",
    proposer="TProposerAddress",
    execution_level=ExecutionLevel.NORMAL,
    delay_seconds=86400  # 24 hours
)
```

### Queue a Proposal

```python
# Queue for execution
await timelock.queue_proposal(proposal_id, "TExecutorAddress")
```

### Execute a Proposal

```python
# Execute after delay period
await timelock.execute_proposal(
    proposal_id, 
    "TExecutorAddress", 
    "0x1234567890abcdef"  # Transaction hash
)
```

### Cancel a Proposal

```python
# Cancel before execution
await timelock.cancel_proposal(proposal_id, "TCancellerAddress")
```

## Docker Deployment

### Build Image

```bash
# Standard image
docker build -f Dockerfile.timelock -t lucid-timelock:latest .

# Distroless image (recommended for production)
docker build -f Dockerfile.timelock.distroless -t lucid-timelock:distroless .
```

### Run Container

```bash
docker run -d \
  --name lucid-timelock \
  -p 8085:8085 \
  -v /data/timelock:/data/timelock \
  -e MONGO_URI="mongodb://lucid:lucid@127.0.0.1:27019/lucid?authSource=admin" \
  lucid-timelock:latest
```

## Integration with Lucid RDP

The timelock governance system integrates with other Lucid RDP components:

- **Blockchain Engine**: Executes approved proposals
- **Admin Controller**: Manages governance permissions
- **User Manager**: Handles proposer authentication
- **Payment Systems**: Processes governance-related transactions

## Security Considerations

1. **Access Control**: Only authorized addresses can create/execute proposals
2. **Time Delays**: All proposals have mandatory delay periods
3. **Signature Requirements**: Multi-signature requirements for critical changes
4. **Audit Trail**: Complete logging of all governance actions
5. **Grace Periods**: Proposals expire if not executed within grace period

## Monitoring

### System Statistics

```python
stats = await timelock.get_system_stats()
print(f"Active proposals: {stats['active_proposals']}")
print(f"Executable proposals: {stats['executable_proposals']}")
```

### Event Logging

All governance events are logged to MongoDB in the `timelock_events` collection:

- `proposal_created`
- `proposal_queued`
- `proposal_executed`
- `proposal_cancelled`
- `proposal_expired`

## Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Check MongoDB is running
   - Verify connection string
   - Check network connectivity

2. **Proposal Not Executable**
   - Verify delay period has passed
   - Check proposal hasn't expired
   - Ensure proper signatures

3. **Permission Denied**
   - Verify proposer/executor addresses
   - Check admin/emergency address lists
   - Review signature requirements

### Logs

Check logs in:
- Console output
- `/data/timelock/timelock.log`
- MongoDB `timelock_events` collection

## Development

### Running Tests

```bash
# Run all tests
python test_timelock.py

# Run specific test
python -m pytest test_timelock.py::TimelockTester::test_proposal_creation
```

### Code Style

```bash
# Format code
black timelock.py

# Sort imports
isort timelock.py

# Type checking
mypy timelock.py
```

## Contributing

1. Follow the existing code style
2. Add tests for new functionality
3. Update documentation
4. Ensure all tests pass
5. Submit pull request

## License

This module is part of the Lucid RDP project and follows the same licensing terms.

## Support

For issues and questions:
- Check the logs for error messages
- Review the configuration
- Run the test suite
- Contact the Lucid RDP team
