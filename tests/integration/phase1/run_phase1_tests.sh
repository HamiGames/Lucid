#!/bin/bash
# tests/integration/phase1/run_phase1_tests.sh
# Run Phase 1 integration tests

set -e

echo "Running Phase 1 integration tests..."

# Install test dependencies
pip install pytest pytest-asyncio requests pymongo redis elasticsearch

# Run tests
python -m pytest tests/integration/phase1/test_phase1_integration.py -v --tb=short

echo "Phase 1 integration tests completed"
