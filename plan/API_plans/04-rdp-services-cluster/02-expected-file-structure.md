# RDP Services Cluster - Expected File Structure

## Overview
This document outlines the expected file names and structure for implementing the RDP Services Cluster API functions based on the API specification.

## Service Architecture
The RDP Services Cluster consists of four main services:
- **RDP Server Manager** (Port 8090)
- **XRDP Integration** (Port 8091) 
- **Session Controller** (Port 8092)
- **Resource Monitor** (Port 8093)

## File Structure by Service

### 1. RDP Server Manager Service (Port 8090)
**Base Path**: `/api/v1/rdp`

#### Core Service Files
```
services/rdp-server-manager/
├── main.py                          # Service entry point
├── config.py                        # Configuration management
├── app.py                           # FastAPI application setup
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Container configuration
└── docker-compose.yml              # Local development setup
```

#### API Endpoint Files
```
services/rdp-server-manager/api/
├── __init__.py
├── dependencies.py                  # Authentication, rate limiting
├── middleware.py                    # Request/response middleware
├── v1/
│   ├── __init__.py
│   ├── rdp_servers.py              # /rdp/servers endpoints
│   ├── server_actions.py           # /rdp/servers/{id}/start|stop|restart
│   └── server_status.py            # /rdp/servers/{id}/status
```

#### Business Logic Files
```
services/rdp-server-manager/core/
├── __init__.py
├── models.py                       # Pydantic models
├── schemas.py                      # Database schemas
├── database.py                     # Database connection
├── rdp_server_manager.py          # Main business logic
├── port_manager.py                 # Port allocation logic
├── server_lifecycle.py             # Server start/stop/restart
├── health_checker.py               # Server health monitoring
└── configuration_manager.py        # Server configuration
```

#### Database Files
```
services/rdp-server-manager/database/
├── __init__.py
├── connection.py                   # Database connection setup
├── models.py                       # SQLAlchemy models
├── migrations/
│   ├── versions/
│   └── env.py
└── repositories/
    ├── __init__.py
    ├── rdp_server_repository.py    # Server CRUD operations
    └── configuration_repository.py # Configuration management
```

### 2. XRDP Integration Service (Port 8091)
**Base Path**: `/api/v1/xrdp`

#### Core Service Files
```
services/xrdp-integration/
├── main.py
├── config.py
├── app.py
├── requirements.txt
└── Dockerfile
```

#### API Endpoint Files
```
services/xrdp-integration/api/
├── __init__.py
├── dependencies.py
├── middleware.py
└── v1/
    ├── __init__.py
    ├── xrdp_config.py             # /xrdp/config endpoints
    └── xrdp_service.py            # /xrdp/service endpoints
```

#### Business Logic Files
```
services/xrdp-integration/core/
├── __init__.py
├── models.py
├── schemas.py
├── xrdp_manager.py                # XRDP service management
├── config_manager.py              # Configuration management
├── service_controller.py          # Service start/stop/restart
├── ssl_manager.py                 # SSL certificate management
└── connection_router.py           # Connection routing
```

#### System Integration Files
```
services/xrdp-integration/system/
├── __init__.py
├── xrdp_controller.py             # System-level XRDP control
├── config_generator.py            # XRDP config file generation
├── service_monitor.py             # XRDP service monitoring
└── log_parser.py                  # XRDP log parsing
```

### 3. Session Controller Service (Port 8092)
**Base Path**: `/api/v1/sessions`

#### Core Service Files
```
services/rdp-session-controller/
├── main.py
├── config.py
├── app.py
├── requirements.txt
└── Dockerfile
```

#### API Endpoint Files
```
services/rdp-session-controller/api/
├── __init__.py
├── dependencies.py
├── middleware.py
└── v1/
    ├── __init__.py
    ├── sessions.py                 # /sessions endpoints
    ├── session_connection.py       # /sessions/{id}/connect
    └── session_disconnect.py       # /sessions/{id}/disconnect
```

#### Business Logic Files
```
services/rdp-session-controller/core/
├── __init__.py
├── models.py
├── schemas.py
├── session_manager.py             # Session lifecycle management
├── connection_manager.py          # Connection handling
├── authentication.py              # Session authentication
├── session_persistence.py         # Session data persistence
├── cleanup_manager.py             # Session cleanup
└── health_monitor.py              # Session health monitoring
```

#### Database Files
```
services/rdp-session-controller/database/
├── __init__.py
├── connection.py
├── models.py
├── migrations/
└── repositories/
    ├── __init__.py
    ├── session_repository.py       # Session CRUD operations
    └── connection_repository.py    # Connection data management
```

### 4. Resource Monitor Service (Port 8093)
**Base Path**: `/api/v1/resources`

#### Core Service Files
```
services/rdp-resource-monitor/
├── main.py
├── config.py
├── app.py
├── requirements.txt
└── Dockerfile
```

#### API Endpoint Files
```
services/rdp-resource-monitor/api/
├── __init__.py
├── dependencies.py
├── middleware.py
└── v1/
    ├── __init__.py
    ├── resource_usage.py          # /resources/usage endpoints
    ├── resource_limits.py         # /resources/limits endpoints
    └── resource_alerts.py         # /resources/alerts endpoints
```

#### Business Logic Files
```
services/rdp-resource-monitor/core/
├── __init__.py
├── models.py
├── schemas.py
├── resource_monitor.py            # Main monitoring logic
├── metrics_collector.py           # System metrics collection
├── usage_analyzer.py              # Usage analysis
├── alert_manager.py               # Alert generation and management
├── limit_enforcer.py              # Resource limit enforcement
└── performance_optimizer.py       # Performance optimization
```

#### Monitoring Files
```
services/rdp-resource-monitor/monitoring/
├── __init__.py
├── cpu_monitor.py                 # CPU usage monitoring
├── memory_monitor.py              # Memory usage monitoring
├── disk_monitor.py                # Disk usage monitoring
├── network_monitor.py             # Network usage monitoring
├── session_monitor.py             # Session-specific monitoring
└── system_monitor.py              # System-wide monitoring
```

## Shared Components

### Common Libraries
```
shared/
├── __init__.py
├── auth/
│   ├── __init__.py
│   ├── authentication.py          # JWT authentication
│   ├── authorization.py           # Role-based access control
│   └── middleware.py              # Auth middleware
├── database/
│   ├── __init__.py
│   ├── connection.py              # Database connection pool
│   ├── base_repository.py         # Base repository class
│   └── migrations.py              # Migration utilities
├── monitoring/
│   ├── __init__.py
│   ├── metrics.py                 # Prometheus metrics
│   ├── health_checks.py           # Health check utilities
│   └── logging.py                 # Structured logging
├── utils/
│   ├── __init__.py
│   ├── validators.py              # Input validation
│   ├── serializers.py             # Data serialization
│   ├── exceptions.py              # Custom exceptions
│   └── helpers.py                 # Utility functions
└── schemas/
    ├── __init__.py
    ├── common.py                  # Common schemas
    ├── rdp_server.py              # RDP server schemas
    ├── session.py                 # Session schemas
    └── resource.py                # Resource schemas
```

### Configuration Files
```
config/
├── base.py                        # Base configuration
├── development.py                 # Development settings
├── production.py                  # Production settings
├── testing.py                     # Testing settings
└── docker/
    ├── docker-compose.yml         # Local development
    ├── docker-compose.prod.yml    # Production deployment
    └── nginx/
        └── nginx.conf             # Load balancer configuration
```

### Documentation Files
```
docs/
├── api/
│   ├── rdp-server-manager.md     # RDP Server Manager API docs
│   ├── xrdp-integration.md       # XRDP Integration API docs
│   ├── session-controller.md     # Session Controller API docs
│   └── resource-monitor.md       # Resource Monitor API docs
├── deployment/
│   ├── installation.md           # Installation guide
│   ├── configuration.md          # Configuration guide
│   └── troubleshooting.md        # Troubleshooting guide
└── development/
    ├── setup.md                  # Development setup
    ├── testing.md                # Testing guidelines
    └── contributing.md           # Contribution guidelines
```

### Testing Files
```
tests/
├── __init__.py
├── conftest.py                    # Pytest configuration
├── unit/
│   ├── test_rdp_server_manager.py
│   ├── test_xrdp_integration.py
│   ├── test_session_controller.py
│   └── test_resource_monitor.py
├── integration/
│   ├── test_api_endpoints.py
│   ├── test_database_integration.py
│   └── test_service_integration.py
└── e2e/
    ├── test_rdp_workflow.py       # End-to-end RDP workflow
    └── test_resource_monitoring.py
```

## Deployment Files

### Kubernetes Manifests
```
k8s/
├── namespace.yaml                 # Kubernetes namespace
├── configmap.yaml                # Configuration
├── secrets.yaml                  # Secrets management
├── services/
│   ├── rdp-server-manager.yaml
│   ├── xrdp-integration.yaml
│   ├── session-controller.yaml
│   └── resource-monitor.yaml
├── deployments/
│   ├── rdp-server-manager.yaml
│   ├── xrdp-integration.yaml
│   ├── session-controller.yaml
│   └── resource-monitor.yaml
└── ingress/
    └── rdp-services-ingress.yaml
```

### Helm Charts
```
helm/
├── rdp-services/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   ├── values-prod.yaml
│   └── templates/
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── configmap.yaml
│       └── ingress.yaml
```

## Scripts and Utilities

### Deployment Scripts
```
scripts/
├── deploy.sh                      # Deployment script
├── build.sh                       # Build script
├── test.sh                        # Test runner
├── backup.sh                      # Backup script
└── restore.sh                     # Restore script
```

### Monitoring Scripts
```
scripts/monitoring/
├── health_check.sh                # Health check script
├── metrics_collector.sh           # Metrics collection
├── log_analyzer.sh                # Log analysis
└── alert_handler.sh               # Alert handling
```

## Environment Files
```
.env.example                       # Environment variables template
.env.development                   # Development environment
.env.production                    # Production environment
.env.testing                       # Testing environment
```

## Summary

The RDP Services Cluster implementation will consist of approximately **150+ files** across four main services, shared components, configuration, documentation, testing, and deployment infrastructure. Each service follows a consistent structure with clear separation of concerns:

- **API Layer**: FastAPI endpoints and middleware
- **Business Logic Layer**: Core functionality and business rules
- **Data Layer**: Database models and repositories
- **Integration Layer**: External system integration (XRDP, system services)
- **Monitoring Layer**: Health checks, metrics, and alerting

This structure ensures maintainability, scalability, and clear separation of responsibilities across the RDP Services Cluster.

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
