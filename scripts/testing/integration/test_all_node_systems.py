#!/usr/bin/env python3
"""
Comprehensive test script to start up and validate all main node systems.
This will detect runtime errors and integration issues.
"""

import asyncio
import logging
import traceback
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('node_systems_test.log')
    ]
)

logger = logging.getLogger(__name__)

class NodeSystemTester:
    """Test all node systems for runtime errors and integration issues"""
    
    def __init__(self):
        self.test_results = {}
        self.errors = []
        
    async def test_peer_discovery(self):
        """Test peer discovery system"""
        try:
            logger.info("Testing peer discovery system...")
            from node.peer_discovery import PeerDiscovery
            
            # Create instance
            peer_discovery = PeerDiscovery(
                db=None,  # Will use mock database
                node_id="test_node_001",
                port=9001
            )
            
            # Test basic functionality
            await peer_discovery.initialize()
            
            # Test peer methods
            peers = await peer_discovery.get_connected_peers()
            logger.info(f"Connected peers: {len(peers)}")
            
            # Test ping functionality (should handle missing aiohttp gracefully)
            result = await peer_discovery.ping_peer("127.0.0.1", 9001)
            logger.info(f"Ping result: {result}")
            
            await peer_discovery.shutdown()
            
            self.test_results['peer_discovery'] = 'PASSED'
            logger.info("✓ Peer discovery test passed")
            
        except Exception as e:
            error_msg = f"Peer discovery test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['peer_discovery'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def test_work_credits(self):
        """Test work credits system"""
        try:
            logger.info("Testing work credits system...")
            from node.work_credits import WorkCreditsCalculator
            
            # Create instance
            work_credits = WorkCreditsCalculator(
                db=None,  # Will use mock database
                node_id="test_node_001"
            )
            
            # Test basic functionality
            await work_credits.initialize()
            
            # Test credit calculation
            credits = await work_credits.calculate_work_credits("test_entity", {"computation": 10})
            logger.info(f"Calculated credits: {credits}")
            
            # Test entity ranking
            rank = await work_credits.get_entity_rank("test_entity")
            logger.info(f"Entity rank: {rank}")
            
            # Test bandwidth recording
            await work_credits.record_relay_bandwidth("test_entity", 1024)
            
            await work_credits.shutdown()
            
            self.test_results['work_credits'] = 'PASSED'
            logger.info("✓ Work credits test passed")
            
        except Exception as e:
            error_msg = f"Work credits test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['work_credits'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def test_node_flag_systems(self):
        """Test node flag system"""
        try:
            logger.info("Testing node flag systems...")
            from node.flags.node_flag_systems import NodeFlagSystems
            
            # Create instance
            flag_systems = NodeFlagSystems(
                db=None,  # Will use mock database
                node_id="test_node_001"
            )
            
            # Test basic functionality
            await flag_systems.initialize()
            
            # Test flag operations
            await flag_systems.set_flag("test_flag", True)
            flag_value = await flag_systems.get_flag("test_flag")
            logger.info(f"Flag value: {flag_value}")
            
            await flag_systems.shutdown()
            
            self.test_results['node_flag_systems'] = 'PASSED'
            logger.info("✓ Node flag systems test passed")
            
        except Exception as e:
            error_msg = f"Node flag systems test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['node_flag_systems'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def test_node_vote_systems(self):
        """Test node vote system"""
        try:
            logger.info("Testing node vote systems...")
            from node.governance.node_vote_systems import NodeVoteSystems
            
            # Create instance
            vote_systems = NodeVoteSystems(
                db=None,  # Will use mock database
                node_id="test_node_001"
            )
            
            # Test basic functionality
            await vote_systems.initialize()
            
            # Test vote operations
            await vote_systems.create_proposal("test_proposal", "Test proposal description")
            proposals = await vote_systems.get_active_proposals()
            logger.info(f"Active proposals: {len(proposals)}")
            
            await vote_systems.shutdown()
            
            self.test_results['node_vote_systems'] = 'PASSED'
            logger.info("✓ Node vote systems test passed")
            
        except Exception as e:
            error_msg = f"Node vote systems test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['node_vote_systems'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def test_node_poot_validations(self):
        """Test node pOot validations"""
        try:
            logger.info("Testing node pOot validations...")
            from node.validation.node_poot_validations import NodePootValidations
            
            # Create instance
            poot_validations = NodePootValidations(
                db=None,  # Will use mock database
                node_id="test_node_001"
            )
            
            # Test basic functionality
            await poot_validations.initialize()
            
            # Test validation
            test_poot_data = {"timestamp": datetime.utcnow().isoformat(), "data": "test"}
            is_valid = await poot_validations.validate_poot(test_poot_data)
            logger.info(f"pOot validation result: {is_valid}")
            
            await poot_validations.shutdown()
            
            self.test_results['node_poot_validations'] = 'PASSED'
            logger.info("✓ Node pOot validations test passed")
            
        except Exception as e:
            error_msg = f"Node pOot validations test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['node_poot_validations'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def test_node_operator_sync_systems(self):
        """Test node operator sync system"""
        try:
            logger.info("Testing node operator sync systems...")
            from node.sync.node_operator_sync_systems import NodeOperatorSyncSystems
            
            # Create instance
            sync_systems = NodeOperatorSyncSystems(
                db=None,  # Will use mock database
                node_id="test_node_001"
            )
            
            # Test basic functionality
            await sync_systems.initialize()
            
            # Test sync operations
            await sync_systems.sync_node_state()
            sync_status = await sync_systems.get_sync_status()
            logger.info(f"Sync status: {sync_status}")
            
            await sync_systems.shutdown()
            
            self.test_results['node_operator_sync_systems'] = 'PASSED'
            logger.info("✓ Node operator sync systems test passed")
            
        except Exception as e:
            error_msg = f"Node operator sync systems test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['node_operator_sync_systems'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def test_node_manager(self):
        """Test node manager (main orchestrator)"""
        try:
            logger.info("Testing node manager...")
            from node.node_manager import NodeManager
            
            # Create instance
            node_manager = NodeManager(
                node_id="test_node_001",
                port=9001,
                use_mock_db=True  # Use mock database for testing
            )
            
            # Test initialization
            await node_manager.initialize()
            logger.info("Node manager initialized successfully")
            
            # Test status
            status = await node_manager.get_status()
            logger.info(f"Node manager status: {status}")
            
            await node_manager.shutdown()
            
            self.test_results['node_manager'] = 'PASSED'
            logger.info("✓ Node manager test passed")
            
        except Exception as e:
            error_msg = f"Node manager test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['node_manager'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def run_all_tests(self):
        """Run all node system tests"""
        logger.info("Starting comprehensive node systems tests...")
        logger.info("=" * 60)
        
        # List of all tests to run
        tests = [
            self.test_peer_discovery,
            self.test_work_credits,
            self.test_node_flag_systems,
            self.test_node_vote_systems,
            self.test_node_poot_validations,
            self.test_node_operator_sync_systems,
            self.test_node_manager
        ]
        
        # Run tests with timeout
        for test in tests:
            try:
                await asyncio.wait_for(test(), timeout=30.0)
            except asyncio.TimeoutError:
                test_name = test.__name__.replace('test_', '')
                error_msg = f"{test_name} test timed out after 30 seconds"
                logger.error(error_msg)
                self.test_results[test_name] = 'TIMEOUT'
                self.errors.append(error_msg)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        logger.info("=" * 60)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        
        passed = 0
        failed = 0
        
        for test_name, result in self.test_results.items():
            if result == 'PASSED':
                logger.info(f"✓ {test_name}: {result}")
                passed += 1
            else:
                logger.error(f"✗ {test_name}: {result}")
                failed += 1
        
        logger.info("=" * 60)
        logger.info(f"TOTAL: {passed} passed, {failed} failed")
        
        if self.errors:
            logger.error("\nERRORS ENCOUNTERED:")
            for i, error in enumerate(self.errors, 1):
                logger.error(f"{i}. {error}")
        
        if failed == 0:
            logger.info("🎉 All tests passed! Node systems are ready for deployment.")
        else:
            logger.warning(f"⚠️  {failed} tests failed. Review errors above.")

async def main():
    """Main function"""
    logger.info("Node Systems Integration Test Suite")
    logger.info(f"Started at: {datetime.now()}")
    
    tester = NodeSystemTester()
    await tester.run_all_tests()
    
    logger.info(f"Completed at: {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())