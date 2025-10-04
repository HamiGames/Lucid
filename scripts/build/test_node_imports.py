#!/usr/bin/env python3
"""
Standalone test for node system imports and spin-up analysis.
This test checks if the node modules can be imported without external dependencies.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_core_imports():
    """Test core node system imports"""
    print("Testing core node system imports...")
    
    try:
        # Test basic Python imports first
        import asyncio
        import logging
        import json
        import uuid
        from datetime import datetime, timezone
        from dataclasses import dataclass
        from enum import Enum
        print("✓ Standard library imports successful")
        
        # Test optional dependencies
        try:
            import aiohttp
            print("✓ aiohttp available")
        except ImportError:
            print("⚠ aiohttp not available - HTTP functionality will be limited")
        
        try:
            from motor.motor_asyncio import AsyncIOMotorDatabase
            print("✓ motor available")
        except ImportError:
            print("⚠ motor not available - database functionality will be limited")
        
        try:
            import pymongo
            print("✓ pymongo available")
        except ImportError:
            print("⚠ pymongo not available - database functionality will be limited")
            
        return True
        
    except Exception as e:
        print(f"✗ Core imports failed: {e}")
        return False

def test_node_module_structure():
    """Test if node modules can be imported individually"""
    print("\nTesting individual node module imports...")
    
    # Test modules that should work without external dependencies
    modules_to_test = [
        ("node.flags.node_flag_systems", "NodeFlagSystem"),
        ("node.governance.node_vote_systems", "NodeVoteSystem"),
        ("node.validation.node_poot_validations", "NodePootValidation"),
        ("node.sync.node_operator_sync_systems", "NodeOperatorSyncSystem"),
        ("node.pools.node_pool_systems", "NodePoolSystem"),
        ("node.registration.node_registration_protocol", "NodeRegistrationProtocol"),
        ("node.shards.shard_host_creation", "ShardHostCreation"),
        ("node.shards.shard_host_management", "ShardHostManagement"),
    ]
    
    results = {}
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✓ {module_name}.{class_name}")
            results[module_name] = True
        except Exception as e:
            print(f"✗ {module_name}.{class_name}: {e}")
            results[module_name] = False
    
    return results

def test_node_init():
    """Test node package initialization"""
    print("\nTesting node package initialization...")
    
    try:
        # Import node package components safely
        from node.peer_discovery import PeerInfo, PeerDiscovery
        from node.work_credits import WorkProof, WorkTally, WorkCreditsCalculator  
        from node.node_manager import NodeConfig, NodeManager
        print("✓ Core node components imported successfully")
        
        # Test if classes can be instantiated (without external dependencies)
        from datetime import datetime, timezone
        peer_info = PeerInfo(
            node_id="test-node",
            onion_address="test.onion",
            port=5050,
            last_seen=datetime.now(timezone.utc)
        )
        print(f"✓ PeerInfo instantiated: {peer_info.node_id}")
        
        work_proof = WorkProof(
            node_id="test-node",
            pool_id=None,
            slot=1,
            task_type="uptime_beacon",
            value=1.0,
            signature="test-sig",
            timestamp=datetime.now(timezone.utc)
        )
        print(f"✓ WorkProof instantiated: {work_proof.task_type}")
        
        node_config = NodeConfig(
            node_id="test-node",
            role="worker",
            onion_address="test.onion",
            port=5050
        )
        print(f"✓ NodeConfig instantiated: {node_config.role}")
        
        return True
        
    except Exception as e:
        print(f"✗ Node initialization failed: {e}")
        return False

def test_mock_functionality():
    """Test mock functionality without external dependencies"""
    print("\nTesting mock functionality...")
    
    try:
        # Use the database adapter system
        from node.database_adapter import get_database_adapter
        mock_db = get_database_adapter()
        
        # Test core classes with mock database
        from node.peer_discovery import PeerDiscovery
        peer_discovery = PeerDiscovery(
            db=mock_db,
            node_id="test-node",
            onion_address="test.onion",
            port=5050
        )
        print("✓ PeerDiscovery with database adapter")
        
        from node.work_credits import WorkCreditsCalculator
        work_credits = WorkCreditsCalculator(db=mock_db)
        print("✓ WorkCreditsCalculator with database adapter")
        
        from node.node_manager import NodeManager, NodeConfig
        node_config = NodeConfig(
            node_id="test-node",
            role="worker",
            onion_address="test.onion",
            port=5050
        )
        node_manager = NodeManager(config=node_config, db=mock_db)
        print("✓ NodeManager with database adapter")
        
        print("✓ Mock functionality working")
        return True
        
    except Exception as e:
        print(f"✗ Mock functionality failed: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("LUCID RDP NODE SYSTEM SPIN-UP ANALYSIS")
    print("=" * 60)
    
    # Test results
    results = {}
    
    # Run tests
    results['core_imports'] = test_core_imports()
    results['module_structure'] = test_node_module_structure()
    results['node_init'] = test_node_init()
    results['mock_functionality'] = test_mock_functionality()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name.upper():.<50} {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Node system is ready for spin-up.")
        return 0
    else:
        print(f"⚠ {total_tests - passed_tests} test(s) failed. Review issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())