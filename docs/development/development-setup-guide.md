# Lucid Development Setup Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | LUCID-DEV-001 |
| Version | 1.0.0 |
| Status | ACTIVE |
| Last Updated | 2025-01-14 |
| Based On | Master Build Plan v1.0.0 |

---

## Overview

This guide provides comprehensive instructions for setting up a development environment for the Lucid blockchain system. It covers local development, testing, debugging, and contribution workflows.

### Development Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Development Environment                   │
│  Local Development + Testing + Debugging + CI/CD           │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Development Tools Layer                    │
│  IDE + Debugger + Testing + Linting + Formatting         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Service Development Layer                  │
│  API Gateway + Blockchain + Auth + Session + RDP         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Database Development Layer                 │
│  MongoDB + Redis + Elasticsearch + Local Storage          │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04+ / Windows 10+ / macOS 10.15+
- **Memory**: 8GB RAM minimum, 16GB recommended
- **Storage**: 50GB free space
- **CPU**: 4 cores minimum, 8 cores recommended

### Required Software

#### Core Dependencies

```bash
# Python 3.11+
python3 --version

# Node.js 18+
node --version

# Docker & Docker Compose
docker --version
docker-compose --version

# Git
git --version
```

#### Development Tools

```bash
# Code Editor (VS Code recommended)
code --version

# Python Development
pip install --upgrade pip
pip install virtualenv poetry

# Node.js Development
npm install -g yarn pnpm

# Database Tools
# MongoDB Compass, Redis Desktop Manager, Elasticsearch Head
```

---

## Local Development Setup

### 1. Repository Setup

#### Clone Repository

```bash
# Clone the repository
git clone https://github.com/HamiGames/Lucid.git
cd Lucid

# Create development branch
git checkout -b feature/your-feature-name

# Install git hooks
cp scripts/git/hooks/* .git/hooks/
chmod +x .git/hooks/*
```

#### Environment Configuration

```bash
# Copy environment template
cp .env.template .env.development

# Generate development secrets
./scripts/development/generate-dev-secrets.sh

# Set development environment variables
export NODE_ENV=development
export DEBUG=true
export LOG_LEVEL=debug
```

### 2. Python Development Environment

#### Virtual Environment Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements.dev.txt
```

#### Poetry Setup (Alternative)

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
poetry shell
```

### 3. Node.js Development Environment

#### Package Management

```bash
# Install dependencies
npm install
# or
yarn install
# or
pnpm install

# Install development dependencies
npm install --save-dev
```

### 4. Database Setup

#### Local Database Services

```bash
# Start local databases
docker-compose -f docker-compose.dev.yml up -d

# Wait for services to be ready
./scripts/development/wait-for-services.sh

# Initialize databases
./scripts/development/init-databases.sh
```

#### Database Configuration

```bash
# MongoDB setup
docker exec lucid-mongodb-dev mongosh --eval "
  use lucid_dev;
  db.createUser({
    user: 'lucid_dev',
    pwd: 'lucid_dev_password',
    roles: [{ role: 'readWrite', db: 'lucid_dev' }]
  });
"

# Redis setup
docker exec lucid-redis-dev redis-cli --no-auth-warning -a lucid_dev_password ping

# Elasticsearch setup
curl -X PUT "localhost:9200/lucid_dev" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  }
}'
```

---

## Service Development

### API Gateway Development

#### Local Development Server

```bash
# Navigate to API Gateway directory
cd 03-api-gateway

# Install dependencies
pip install -r requirements.txt

# Start development server
python main.py --debug --reload

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8080 --reload --log-level debug
```

#### API Gateway Testing

```bash
# Run unit tests
pytest tests/ -v

# Run integration tests
pytest tests/integration/ -v

# Run API tests
pytest tests/api/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

#### API Gateway Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG=true

# Start with debugger
python -m pdb main.py

# Or using VS Code debugger
# Set breakpoints in VS Code and run "Python: Current File"
```

### Blockchain Development

#### Blockchain Engine Development

```bash
# Navigate to blockchain directory
cd blockchain

# Install dependencies
pip install -r requirements.txt

# Start blockchain engine
python main.py --debug --network=testnet

# Start with specific configuration
python main.py --config=config/testnet.yaml --debug
```

#### Blockchain Testing

```bash
# Run blockchain tests
pytest tests/blockchain/ -v

# Run consensus tests
pytest tests/consensus/ -v

# Run transaction tests
pytest tests/transaction/ -v

# Run with blockchain network
pytest tests/blockchain/ --network=testnet
```

#### Blockchain Debugging

```bash
# Enable blockchain debugging
export BLOCKCHAIN_DEBUG=true
export CONSENSUS_DEBUG=true

# Start with debugger
python -m pdb main.py

# Monitor blockchain state
python scripts/monitor-blockchain.py
```

### Authentication Development

#### Auth Service Development

```bash
# Navigate to auth directory
cd auth

# Install dependencies
pip install -r requirements.txt

# Start auth service
python main.py --debug --port=8089

# Start with JWT debugging
export JWT_DEBUG=true
python main.py --debug
```

#### Auth Testing

```bash
# Run auth tests
pytest tests/auth/ -v

# Run JWT tests
pytest tests/jwt/ -v

# Run session tests
pytest tests/session/ -v

# Test with different algorithms
pytest tests/auth/ --algorithm=RS256
```

### Session Management Development

#### Session Service Development

```bash
# Navigate to session directory
cd sessions

# Install dependencies
pip install -r requirements.txt

# Start session service
python main.py --debug --port=8090

# Start with session debugging
export SESSION_DEBUG=true
python main.py --debug
```

#### Session Testing

```bash
# Run session tests
pytest tests/session/ -v

# Run chunking tests
pytest tests/chunking/ -v

# Run storage tests
pytest tests/storage/ -v

# Test with different chunk sizes
pytest tests/session/ --chunk-size=1024
```

---

## Development Tools

### Code Quality Tools

#### Linting and Formatting

```bash
# Python linting
flake8 . --max-line-length=120 --exclude=venv,__pycache__
black . --line-length=120
isort . --profile=black

# Type checking
mypy . --ignore-missing-imports

# Security scanning
bandit -r . -f json -o security-report.json
safety check --json --output safety-report.json
```

#### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

#### Code Coverage

```bash
# Run tests with coverage
pytest tests/ --cov=. --cov-report=html --cov-report=term

# Generate coverage report
coverage html
coverage report

# View coverage report
open htmlcov/index.html
```

### Testing Tools

#### Unit Testing

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_api_gateway.py -v

# Run with specific markers
pytest tests/ -m "not slow" -v

# Run with parallel execution
pytest tests/ -n auto
```

#### Integration Testing

```bash
# Run integration tests
pytest tests/integration/ -v

# Run with test database
pytest tests/integration/ --database=test

# Run with specific services
pytest tests/integration/ --services=api-gateway,blockchain
```

#### End-to-End Testing

```bash
# Run E2E tests
pytest tests/e2e/ -v

# Run with browser
pytest tests/e2e/ --browser=chrome

# Run with specific environment
pytest tests/e2e/ --env=staging
```

### Debugging Tools

#### Application Debugging

```bash
# Python debugging
python -m pdb main.py

# VS Code debugging
# Create .vscode/launch.json with debug configurations

# Remote debugging
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client main.py
```

#### Database Debugging

```bash
# MongoDB debugging
mongosh --eval "db.setProfilingLevel(2)"
mongosh --eval "db.system.profile.find().limit(5).sort({ts: -1}).pretty()"

# Redis debugging
redis-cli monitor

# Elasticsearch debugging
curl -X GET "localhost:9200/_cluster/health?pretty"
```

#### Network Debugging

```bash
# Network monitoring
netstat -tuln
ss -tuln

# Traffic analysis
tcpdump -i any port 8080
wireshark

# API testing
curl -v http://localhost:8080/health
```

---

## Development Workflows

### Feature Development

#### Feature Branch Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
# ... implement feature ...

# Run tests
pytest tests/ -v

# Run linting
flake8 . --max-line-length=120
black . --check

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push branch
git push origin feature/new-feature

# Create pull request
gh pr create --title "Add new feature" --body "Description of changes"
```

#### Code Review Process

```bash
# Review checklist
- [ ] Code follows style guidelines
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Security considerations addressed
- [ ] Performance impact assessed
```

### Bug Fixing

#### Bug Report Workflow

```bash
# Create bug branch
git checkout -b bugfix/issue-123

# Reproduce bug
# ... steps to reproduce ...

# Write failing test
# ... test that reproduces bug ...

# Fix bug
# ... implement fix ...

# Verify fix
pytest tests/ -v

# Commit fix
git add .
git commit -m "fix: resolve issue #123"
```

### Performance Optimization

#### Profiling and Optimization

```bash
# Python profiling
python -m cProfile -o profile.prof main.py
python -c "import pstats; pstats.Stats('profile.prof').sort_stats('cumulative').print_stats(10)"

# Memory profiling
python -m memory_profiler main.py

# Line-by-line profiling
kernprof -l -v main.py

# Performance testing
pytest tests/performance/ -v
```

---

## Development Scripts

### Development Utilities

#### Service Management

```bash
#!/bin/bash
# scripts/development/dev-services.sh

# Start all development services
./scripts/development/start-dev-services.sh

# Stop all development services
./scripts/development/stop-dev-services.sh

# Restart specific service
./scripts/development/restart-service.sh api-gateway

# Check service status
./scripts/development/check-services.sh
```

#### Database Management

```bash
#!/bin/bash
# scripts/development/dev-database.sh

# Reset development database
./scripts/development/reset-database.sh

# Seed development data
./scripts/development/seed-data.sh

# Backup development database
./scripts/development/backup-database.sh

# Restore development database
./scripts/development/restore-database.sh
```

#### Testing Utilities

```bash
#!/bin/bash
# scripts/development/dev-testing.sh

# Run all tests
./scripts/development/run-tests.sh

# Run specific test suite
./scripts/development/run-tests.sh unit

# Generate test report
./scripts/development/generate-test-report.sh

# Run performance tests
./scripts/development/run-performance-tests.sh
```

---

## Development Environment Configuration

### VS Code Configuration

#### Workspace Settings

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.pylintEnabled": false,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/venv": true,
    "**/node_modules": true
  }
}
```

#### Debug Configuration

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: API Gateway",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/03-api-gateway/main.py",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "DEBUG": "true"
      }
    },
    {
      "name": "Python: Blockchain Engine",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/blockchain/main.py",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "DEBUG": "true"
      }
    }
  ]
}
```

### Docker Development

#### Development Docker Compose

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  lucid-api-gateway-dev:
    build:
      context: .
      dockerfile: Dockerfile.api-gateway.dev
    container_name: lucid-api-gateway-dev
    ports:
      - "8080:8080"
    volumes:
      - .:/app
      - /app/venv
    environment:
      - NODE_ENV=development
      - DEBUG=true
    command: python main.py --debug --reload

  lucid-blockchain-dev:
    build:
      context: .
      dockerfile: Dockerfile.blockchain.dev
    container_name: lucid-blockchain-dev
    ports:
      - "8081:8081"
    volumes:
      - .:/app
      - /app/venv
    environment:
      - NODE_ENV=development
      - DEBUG=true
    command: python main.py --debug --reload
```

---

## Troubleshooting Development Issues

### Common Development Problems

#### Service Connection Issues

```bash
# Check service status
docker ps
docker logs lucid-api-gateway-dev

# Check network connectivity
docker network ls
docker network inspect lucid-dev-network

# Restart services
docker-compose -f docker-compose.dev.yml restart
```

#### Database Connection Issues

```bash
# Check database status
docker exec lucid-mongodb-dev mongosh --eval "db.runCommand({ping: 1})"
docker exec lucid-redis-dev redis-cli ping

# Check database logs
docker logs lucid-mongodb-dev
docker logs lucid-redis-dev

# Reset database
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

#### Test Failures

```bash
# Check test environment
pytest --collect-only tests/

# Run tests with verbose output
pytest tests/ -v -s

# Run specific test with debugging
pytest tests/test_specific.py::test_function -v -s --pdb
```

---

## Development Best Practices

### Code Organization

- **Modular Design**: Keep services independent and loosely coupled
- **Clear Interfaces**: Define clear APIs between services
- **Error Handling**: Implement comprehensive error handling
- **Logging**: Use structured logging throughout the application

### Testing Strategy

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test service interactions
- **End-to-End Tests**: Test complete user workflows
- **Performance Tests**: Test system performance under load

### Documentation

- **Code Comments**: Document complex logic and algorithms
- **API Documentation**: Document all API endpoints
- **README Files**: Provide setup and usage instructions
- **Architecture Diagrams**: Document system architecture

---

## References

- [Deployment Guide](../deployment/deployment-guide.md)
- [Troubleshooting Guide](../deployment/troubleshooting-guide.md)
- [Coding Standards](./coding-standards.md)
- [Master Build Plan](../../plan/API_plans/00-master-architecture/01-MASTER_BUILD_PLAN.md)

---

**Document Version**: 1.0.0  
**Status**: ACTIVE  
**Last Updated**: 2025-01-14
