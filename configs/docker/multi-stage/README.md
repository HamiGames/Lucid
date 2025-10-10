# Lucid Multi-Stage Docker Configurations

This directory contains Docker Compose configurations specifically designed for multi-stage containers in the Lucid project. These configurations are optimized for development, testing, and flexible deployment scenarios.

## Overview

Multi-stage configurations provide:
- **Development Flexibility**: Multiple build stages for different environments
- **Build Optimization**: Layer caching and optimization for faster builds
- **Testing Support**: Comprehensive testing environments and tools
- **Development Tools**: Built-in development and debugging capabilities
- **Performance Monitoring**: Advanced monitoring and performance analysis

## Configuration Files

### Core Configurations

#### `multi-stage-config.yml`
- **Purpose**: Main multi-stage configuration for base images
- **Use Case**: Standard multi-stage deployment scenarios
- **Features**: Runtime, development, and builder stage configurations

#### `multi-stage-build-config.yml`
- **Purpose**: Build-time configuration for multi-stage images
- **Use Case**: CI/CD pipeline builds with layer optimization
- **Features**: Build orchestrator, layer analyzer, cache optimizer

#### `multi-stage-runtime-config.yml`
- **Purpose**: Runtime configuration for production multi-stage containers
- **Use Case**: Production deployment with monitoring and resource management
- **Features**: Production runtime, development runtime, monitoring runtime

#### `multi-stage-development-config.yml`
- **Purpose**: Development-friendly configuration for multi-stage containers
- **Use Case**: Development environments with debugging capabilities
- **Features**: Development environment, builder tools, development database

#### `multi-stage-testing-config.yml`
- **Purpose**: Testing configuration for multi-stage containers
- **Use Case**: Comprehensive testing environments
- **Features**: Test environment, build testing, test database, result aggregation

### Environment Configuration

#### `multi-stage.env`
- **Purpose**: Environment variables for all multi-stage configurations
- **Use Case**: Centralized configuration management
- **Features**: Build settings, stage configurations, development options

## Usage Examples

### Production Deployment
```bash
# Deploy production multi-stage configuration
docker-compose -f multi-stage-runtime-config.yml --env-file multi-stage.env up -d

# With custom environment
BUILD_ENVIRONMENT=production VERSION=v1.0.0 docker-compose -f multi-stage-runtime-config.yml up -d
```

### Development Environment
```bash
# Start development environment
docker-compose -f multi-stage-development-config.yml up -d

# With debugging enabled
DEBUG_MODE=true HOT_RELOAD=true docker-compose -f multi-stage-development-config.yml up -d
```

### Testing Environment
```bash
# Run comprehensive tests
docker-compose -f multi-stage-testing-config.yml up -d

# With coverage enabled
COVERAGE_ENABLED=true docker-compose -f multi-stage-testing-config.yml up -d
```

### Build Process
```bash
# Build multi-stage images with optimization
docker-compose -f multi-stage-build-config.yml up -d

# With aggressive optimization
OPTIMIZE_LAYERS=true PARALLEL_BUILDS=8 docker-compose -f multi-stage-build-config.yml up -d
```

## Multi-Stage Features

### Build Stages

#### Builder Stage
- **Purpose**: Compilation and build environment
- **Features**: Build tools, compilers, dependencies
- **Use Case**: Initial build and compilation phase

#### Development Stage
- **Purpose**: Development and debugging environment
- **Features**: Debug tools, hot reload, development dependencies
- **Use Case**: Active development and testing

#### Runtime Stage
- **Purpose**: Production runtime environment
- **Features**: Minimal runtime, production dependencies
- **Use Case**: Production deployment

### Layer Optimization
- **Layer Caching**: Intelligent caching for faster builds
- **Layer Analysis**: Detailed analysis of layer composition
- **Cache Optimization**: Aggressive cache optimization strategies
- **Build Validation**: Comprehensive build validation and testing

## Development Features

### Development Tools
- **Hot Reload**: Automatic code reloading during development
- **Debug Support**: Built-in debugging capabilities with SYS_PTRACE
- **Development Database**: Integrated MongoDB for development
- **Code Coverage**: Comprehensive code coverage analysis

### Testing Capabilities
- **Unit Testing**: Automated unit test execution
- **Integration Testing**: Full integration test suites
- **Build Testing**: Multi-stage build validation
- **Performance Testing**: Performance benchmarking and analysis

### Monitoring and Analytics
- **Build Monitoring**: Real-time build process monitoring
- **Performance Analytics**: Detailed performance metrics
- **Resource Monitoring**: Resource usage tracking and optimization
- **Test Result Aggregation**: Comprehensive test result analysis

## Performance Optimizations

### Build Performance
- **Parallel Builds**: Configurable parallel build execution
- **Layer Caching**: Intelligent layer caching strategies
- **Build Cache**: Persistent build cache management
- **Artifact Management**: Efficient artifact storage and retrieval

### Runtime Performance
- **Resource Limits**: Configurable memory and CPU limits
- **Resource Reservations**: Guaranteed resource allocations
- **Performance Monitoring**: Real-time performance monitoring
- **Optimization Reports**: Detailed optimization analysis

### Development Performance
- **Fast Builds**: Optimized development build processes
- **Debug Builds**: Specialized debug build configurations
- **Hot Reload**: Efficient code reloading mechanisms
- **Development Tools**: Optimized development tooling

## Security Considerations

### Container Security
- **Non-root execution**: Containers run as non-root user
- **Security options**: Configurable security options
- **Capability management**: Controlled capability dropping and adding
- **Network isolation**: Isolated network configurations

### Development Security
- **Debug permissions**: Controlled debug permissions
- **Development isolation**: Isolated development environments
- **Secure testing**: Secure testing environment configurations
- **Access control**: Controlled access to development tools

## Troubleshooting

### Common Issues

#### Build Failures
```bash
# Check build logs
docker-compose -f multi-stage-build-config.yml logs build-orchestrator

# Verify build cache
docker system df
docker builder prune
```

#### Development Issues
```bash
# Check development container
docker-compose -f multi-stage-development-config.yml logs dev-multi-stage

# Verify development database
docker-compose -f multi-stage-development-config.yml exec dev-database mongosh
```

#### Testing Issues
```bash
# Check test results
docker-compose -f multi-stage-testing-config.yml logs test-aggregator

# Verify test database
docker-compose -f multi-stage-testing-config.yml exec test-database mongosh
```

### Debug Mode
```bash
# Enable comprehensive debugging
DEBUG_MODE=true LOG_LEVEL=DEBUG BUILD_VALIDATION=true docker-compose -f multi-stage-development-config.yml up -d
```

## Maintenance

### Regular Maintenance
1. Update base images and dependencies
2. Clean up build caches and artifacts
3. Review and optimize layer configurations
4. Update development and testing tools

### Performance Maintenance
1. Monitor build performance and optimize
2. Review and update resource limits
3. Analyze and optimize layer composition
4. Update caching strategies

### Security Maintenance
1. Regular security updates for development tools
2. Review and update security configurations
3. Monitor development environment security
4. Update testing security configurations

## Best Practices

### Development Workflow
1. Use development configuration for active development
2. Leverage hot reload for faster iteration
3. Use testing configuration for comprehensive testing
4. Use production configuration for deployment validation

### Build Optimization
1. Enable layer caching for faster builds
2. Use parallel builds for multi-service projects
3. Optimize layer composition regularly
4. Clean up build artifacts periodically

### Testing Strategy
1. Run unit tests during development
2. Use integration tests for service validation
3. Perform build testing for deployment readiness
4. Use performance testing for optimization validation

## Contributing

When adding new multi-stage configurations:
1. Follow multi-stage best practices
2. Include comprehensive testing capabilities
3. Document build stage purposes
4. Test on multiple environments
5. Update this README with new features

## References

- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker Layer Optimization](https://docs.docker.com/build/cache/)
- [Docker Development Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-Stage Build Patterns](https://docs.docker.com/build/building/multi-stage/#use-cases)
