# RDP Resource Monitor Configuration

## Environment Variables Template

This directory contains the environment variables template for the rdp-monitor container.

### Usage

1. **Copy the template file to the environment configuration directory:**
   ```bash
   cp RDP/resource-monitor/config/env.rdp-monitor.template configs/environment/.env.rdp-monitor
   ```

2. **Customize the values in `.env.rdp-monitor`:**
   - Replace `{MONGODB_PASSWORD}` and `{REDIS_PASSWORD}` placeholders with actual values from `.env.secrets`
   - Adjust monitoring intervals based on your requirements (lower = more frequent but higher CPU usage)
   - Tune alert thresholds (CPU, memory, disk, network) based on your resource constraints
   - Update service URLs if your service names differ
   - Configure metrics and performance settings

3. **The docker-compose file will automatically load this file:**
   The `docker-compose.application.yml` includes `.env.rdp-monitor` in the `env_file` list for the rdp-monitor service.

### Key Configuration Areas

- **Service Settings**: Host, port, and URL configuration
- **Database Configuration**: MongoDB and Redis (optional - service can operate without them)
- **Monitoring Configuration**: Intervals, history limits, and cleanup settings
- **Alert Thresholds**: CPU, memory, disk, and network bandwidth thresholds
- **Metrics Configuration**: Prometheus export, metrics collection settings
- **Performance Configuration**: Concurrent session limits and cache sizes
- **Integration Services**: URLs for RDP services (server-manager, xrdp, controller)
- **Health Check**: Interval, timeout, and retry configuration

### Notes

- **MongoDB and Redis are optional**: The rdp-monitor service can operate without database connections, but some features (persistent metrics, caching) will be limited
- All service URLs must use Docker service names (not `localhost`) for proper networking
- Monitoring intervals should be tuned based on system load (recommended: 30-60 seconds)
- Alert thresholds are configurable based on your infrastructure constraints
- METRICS_PORT (9216) is separate from the main service port (8093) for metrics export

