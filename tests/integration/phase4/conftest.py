"""
Phase 4 Integration Test Configuration

This module provides pytest fixtures and configuration for Phase 4 integration tests,
including admin interface, TRON payment, and full system integration testing.
"""

import pytest
import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from tests.utils.fixtures import (
    admin_user_fixture,
    tron_payment_fixture,
    system_health_fixture
)
from tests.utils.helpers import (
    wait_for_service,
    get_service_url,
    create_test_session,
    cleanup_test_data
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def admin_interface_url():
    """Get admin interface service URL."""
    url = get_service_url("admin-interface", 8096)
    await wait_for_service(url, timeout=60)
    return url


@pytest.fixture(scope="session")
async def tron_payment_url():
    """Get TRON payment service URL."""
    url = get_service_url("tron-payment", 8085)
    await wait_for_service(url, timeout=60)
    return url


@pytest.fixture(scope="session")
async def api_gateway_url():
    """Get API gateway service URL."""
    url = get_service_url("api-gateway", 8080)
    await wait_for_service(url, timeout=60)
    return url


@pytest.fixture(scope="session")
async def blockchain_core_url():
    """Get blockchain core service URL."""
    url = get_service_url("blockchain-core", 8084)
    await wait_for_service(url, timeout=60)
    return url


@pytest.fixture(scope="session")
async def session_management_url():
    """Get session management service URL."""
    url = get_service_url("session-management", 8087)
    await wait_for_service(url, timeout=60)
    return url


@pytest.fixture(scope="session")
async def node_management_url():
    """Get node management service URL."""
    url = get_service_url("node-management", 8095)
    await wait_for_service(url, timeout=60)
    return url


@pytest.fixture(scope="session")
async def auth_service_url():
    """Get authentication service URL."""
    url = get_service_url("auth-service", 8089)
    await wait_for_service(url, timeout=60)
    return url


@pytest.fixture(scope="session")
async def database_url():
    """Get database service URL."""
    url = get_service_url("database", 8088)
    await wait_for_service(url, timeout=60)
    return url


@pytest.fixture(scope="session")
async def service_mesh_url():
    """Get service mesh URL."""
    url = get_service_url("service-mesh", 8500)
    await wait_for_service(url, timeout=60)
    return url


@pytest.fixture
async def admin_session(admin_interface_url, auth_service_url):
    """Create authenticated admin session."""
    async with aiohttp.ClientSession() as session:
        # Login as admin user
        login_data = {
            "username": "admin",
            "password": "admin_password",
            "tron_signature": "mock_tron_signature"
        }
        
        async with session.post(
            f"{auth_service_url}/auth/login",
            json=login_data
        ) as response:
            if response.status == 200:
                auth_data = await response.json()
                return {
                    "session": session,
                    "token": auth_data["access_token"],
                    "admin_interface_url": admin_interface_url
                }
            else:
                pytest.skip("Admin authentication failed")


@pytest.fixture
async def tron_payment_session(tron_payment_url, auth_service_url):
    """Create authenticated TRON payment session."""
    async with aiohttp.ClientSession() as session:
        # Login as payment user
        login_data = {
            "username": "payment_user",
            "password": "payment_password",
            "tron_signature": "mock_tron_signature"
        }
        
        async with session.post(
            f"{auth_service_url}/auth/login",
            json=login_data
        ) as response:
            if response.status == 200:
                auth_data = await response.json()
                return {
                    "session": session,
                    "token": auth_data["access_token"],
                    "tron_payment_url": tron_payment_url
                }
            else:
                pytest.skip("TRON payment authentication failed")


@pytest.fixture
async def system_health_check(admin_interface_url, tron_payment_url, api_gateway_url):
    """Check system health before running tests."""
    health_status = {}
    
    async with aiohttp.ClientSession() as session:
        # Check admin interface health
        try:
            async with session.get(f"{admin_interface_url}/admin/health") as response:
                health_status["admin_interface"] = response.status == 200
        except Exception:
            health_status["admin_interface"] = False
        
        # Check TRON payment health
        try:
            async with session.get(f"{tron_payment_url}/api/v1/tron/network/status") as response:
                health_status["tron_payment"] = response.status == 200
        except Exception:
            health_status["tron_payment"] = False
        
        # Check API gateway health
        try:
            async with session.get(f"{api_gateway_url}/health") as response:
                health_status["api_gateway"] = response.status == 200
        except Exception:
            health_status["api_gateway"] = False
    
    return health_status


@pytest.fixture
async def test_data_cleanup():
    """Cleanup test data after tests."""
    yield
    # Cleanup logic will be implemented here
    await cleanup_test_data()


@pytest.fixture
async def mock_tron_network():
    """Mock TRON network for testing."""
    return {
        "network_id": "mainnet",
        "chain_id": "0x2b6653dc",
        "block_height": 50000000,
        "network_status": "healthy",
        "node_url": "https://api.trongrid.io"
    }


@pytest.fixture
async def mock_admin_dashboard_data():
    """Mock admin dashboard data for testing."""
    return {
        "system_stats": {
            "total_sessions": 150,
            "active_sessions": 25,
            "total_nodes": 50,
            "active_nodes": 45,
            "blockchain_height": 1000,
            "total_payouts": 5000
        },
        "recent_activities": [
            {
                "timestamp": datetime.now().isoformat(),
                "action": "session_created",
                "user_id": "user_123",
                "details": "New session started"
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "action": "payout_processed",
                "user_id": "user_456",
                "details": "Payout of 100 USDT processed"
            }
        ],
        "system_alerts": [
            {
                "level": "warning",
                "message": "High CPU usage on node-03",
                "timestamp": datetime.now().isoformat()
            }
        ]
    }


@pytest.fixture
async def mock_emergency_controls():
    """Mock emergency controls for testing."""
    return {
        "system_lockdown": {
            "enabled": False,
            "reason": None,
            "timestamp": None
        },
        "emergency_stop": {
            "enabled": False,
            "reason": None,
            "timestamp": None
        },
        "maintenance_mode": {
            "enabled": False,
            "reason": None,
            "timestamp": None
        }
    }


@pytest.fixture
async def mock_tron_payout_data():
    """Mock TRON payout data for testing."""
    return {
        "payout_id": "payout_123456",
        "user_id": "user_789",
        "amount": "100.50",
        "currency": "USDT",
        "status": "pending",
        "transaction_hash": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


# Test configuration
pytest_plugins = ["tests.utils.fixtures"]

# Test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.phase4,
    pytest.mark.asyncio
]
