#!/usr/bin/env python3
"""
Fixed comprehensive test script to start up and validate all main node systems.
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

# Configure logging for Windows compatibility
from node.peer_discovery import PeerDiscovery
from node.work_credits import WorkCreditsCalculator
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('node_systems_test.log', encoding='utf-8')
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
            from node.database_adapter import get_database_adapter
            
            # Create instance with correct parameters
            db = get_database_adapter(motor_db=None)  # Uses mock database
            peer_discovery = PeerDiscovery(
                db=db,
                node_id="test_node_001",
                onion_address="test1234567890123456.onion",
                port=9001
            )
            
            # Test basic functionality
            await peer_discovery.start()
            
            # Test peer methods
            active_peers = await peer_discovery.get_active_peers()
            logger.info(f"Active peers: {len(active_peers)}")
            
            # Test peers by role
            server_peers = await peer_discovery.get_peers_by_role("server")
            logger.info(f"Server peers: {len(server_peers)}")
            
            await peer_discovery.stop()
            
            self.test_results['peer_discovery'] = 'PASSED'
            logger.info("+ Peer discovery test passed")
            
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
            from node.database_adapter import get_database_adapter
            
            # Create instance with correct parameters
            db = get_database_adapter(motor_db=None)  # Uses mock database
            work_credits = WorkCreditsCalculator(
                db=db,
                slot_duration_sec=120
            )
            
            # Test credit calculation
            credits = await work_credits.calculate_work_credits("test_entity", window_days=7)
            logger.info(f"Calculated credits: {credits}")
            
            # Test entity ranking
            rank = await work_credits.get_entity_rank("test_entity")
            logger.info(f"Entity rank: {rank}")
            
            # Test bandwidth recording
            await work_credits.record_relay_bandwidth("test_entity", 1024)
            
            self.test_results['work_credits'] = 'PASSED'
            logger.info("+ Work credits test passed")
            
        except Exception as e:
            error_msg = f"Work credits test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['work_credits'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def test_node_flag_system(self):
        """Test node flag system"""
        try:
            logger.info("Testing node flag system...")
            from node.flags.node_flag_systems import NodeFlagSystem  # Correct singular name
            from node.database_adapter import get_database_adapter
            
            # Create instance with required dependencies
            db = get_database_adapter(motor_db=None)  # Uses mock database
            peer_discovery = PeerDiscovery(
                db=db,
                node_id="test_node_001",
                onion_address="test1234567890123456.onion",
                port=9001
            )
            work_credits = WorkCreditsCalculator(db=db, slot_duration_sec=120)
            
            flag_system = NodeFlagSystem(
                db=db,
                peer_discovery=peer_discovery,
                work_credits=work_credits
            )
            
            # Test basic functionality
            await flag_system.start()
            
            # Test flag operations (create flag instead of set_flag)
            from node.flags.node_flag_systems import FlagType, FlagSeverity, FlagSource
            flag_id = await flag_system.create_flag(
                "test_node_001", FlagType.OPERATIONAL, FlagSeverity.INFO,
                "Test Flag", "Test flag description", FlagSource.SYSTEM
            )
            logger.info(f"Created flag ID: {flag_id}")
            
            await flag_system.stop()
            
            self.test_results['node_flag_system'] = 'PASSED'
            logger.info("+ Node flag system test passed")
            
        except Exception as e:
            error_msg = f"Node flag system test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['node_flag_system'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def test_node_vote_system(self):
        """Test node vote system"""
        try:
            logger.info("Testing node vote system...")
            from node.governance.node_vote_systems import NodeVoteSystem  # Correct singular name
            from node.database_adapter import get_database_adapter
            
            # Create instance with required dependencies
            db = get_database_adapter(motor_db=None)  # Uses mock database
            peer_discovery = PeerDiscovery(
                db=db,
                node_id="test_node_002",
                onion_address="test2345678901234567.onion",
                port=9002
            )
            work_credits = WorkCreditsCalculator(db=db, slot_duration_sec=120)
            
            vote_system = NodeVoteSystem(
                db=db,
                peer_discovery=peer_discovery,
                work_credits=work_credits
            )
            
            # Test basic functionality
            await vote_system.start()
            
            # Test vote operations
            from node.governance.node_vote_systems import ProposalType, VoteWeight
            proposal_id = await vote_system.create_proposal(
                "test_node_002", "Test Proposal", "Test proposal description",
                ProposalType.PARAMETER_CHANGE, VoteWeight.EQUAL
            )
            logger.info(f"Created proposal ID: {proposal_id}")
            
            await vote_system.stop()
            
            self.test_results['node_vote_system'] = 'PASSED'
            logger.info("+ Node vote system test passed")
            
        except Exception as e:
            error_msg = f"Node vote system test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['node_vote_system'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def test_node_poot_validation(self):
        """Test node pOot validations"""
        try:
            logger.info("Testing node pOot validations...")
            from node.validation.node_poot_validations import NodePootValidation  # Correct singular name
            from node.database_adapter import get_database_adapter
            
            # Create instance with required dependencies
            db = get_database_adapter(motor_db=None)  # Uses mock database
            peer_discovery = PeerDiscovery(
                db=db,
                node_id="test_node_003",
                onion_address="test3456789012345678.onion",
                port=9003
            )
            work_credits = WorkCreditsCalculator(db=db, slot_duration_sec=120)
            
            poot_validation = NodePootValidation(
                db=db,
                peer_discovery=peer_discovery,
                work_credits=work_credits
            )
            
            # Test basic functionality
            await poot_validation.start()
            
            # Test challenge generation
            from node.validation.node_poot_validations import ProofType
            challenge_id = await poot_validation.generate_ownership_challenge(
                "test_node_003", ProofType.STAKE_PROOF
            )
            logger.info(f"Generated challenge ID: {challenge_id}")
            
            await poot_validation.stop()
            
            self.test_results['node_poot_validation'] = 'PASSED'
            logger.info("+ Node pOot validation test passed")
            
        except Exception as e:
            error_msg = f"Node pOot validation test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['node_poot_validation'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def test_node_operator_sync_system(self):
        """Test node operator sync system"""
        try:
            logger.info("Testing node operator sync system...")
            from node.sync.node_operator_sync_systems import NodeOperatorSyncSystem  # Correct singular name
            from node.database_adapter import get_database_adapter
            
            # Create instance with required dependencies
            db = get_database_adapter(motor_db=None)  # Uses mock database
            peer_discovery = PeerDiscovery(
                db=db,
                node_id="test_node_004",
                onion_address="test4567890123456789.onion",
                port=9004
            )
            work_credits = WorkCreditsCalculator(db=db, slot_duration_sec=120)
            
            sync_system = NodeOperatorSyncSystem(
                db=db,
                peer_discovery=peer_discovery,
                work_credits=work_credits,
                operator_id="test_operator_001",
                node_id="test_node_004"
            )
            
            # Test basic functionality
            await sync_system.start()
            
            # Test operator registration
            from node.sync.node_operator_sync_systems import OperatorRole
            await sync_system.register_operator(
                "127.0.0.1:9004", "test_public_key", OperatorRole.SECONDARY
            )
            logger.info("Operator registered successfully")
            
            await sync_system.stop()
            
            self.test_results['node_operator_sync_system'] = 'PASSED'
            logger.info("+ Node operator sync system test passed")
            
        except Exception as e:
            error_msg = f"Node operator sync system test failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.test_results['node_operator_sync_system'] = f'FAILED: {str(e)}'
            self.errors.append(error_msg)
    
    async def test_node_manager(self):
        """Test node manager (main orchestrator)"""
        try:
            logger.info("Testing node manager...")
            from node.node_manager import NodeManager, NodeConfig
            from node.database_adapter import get_database_adapter
            
            # Create config and database
            config = NodeConfig(
                node_id="test_node_001",
                role="worker",
                onion_address="test1234567890123456.onion",
                port=9001
            )
            
            db = get_database_adapter(motor_db=None)  # Uses mock database
            
            # Create instance with correct parameters
            node_manager = NodeManager(config=config, db=db)
            
            # Test initialization
            await node_manager.start()
            logger.info("Node manager initialized successfully")
            
            # Test status
            status = await node_manager.get_node_status()
            logger.info(f"Node manager status: {status['running']}")
            
            await node_manager.stop()
            
            self.test_results['node_manager'] = 'PASSED'
            logger.info("+ Node manager test passed")
            
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
            self.test_node_flag_system,
            self.test_node_vote_system,
            self.test_node_poot_validation,
            self.test_node_operator_sync_system,
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
                logger.info(f"[PASS] {test_name}: {result}")
                passed += 1
            else:
                logger.error(f"[FAIL] {test_name}: {result}")
                failed += 1
        
        logger.info("=" * 60)
        logger.info(f"TOTAL: {passed} passed, {failed} failed")
        
        if self.errors:
            logger.error("\nERRORS ENCOUNTERED:")
            for i, error in enumerate(self.errors, 1):
                logger.error(f"{i}. {error}")
        
        if failed == 0:
            logger.info("All tests passed! Node systems are ready for deployment.")
        else:
            logger.warning(f"{failed} tests failed. Review errors above.")

async def main():
    """Main function"""
    logger.info("Node Systems Integration Test Suite")
    logger.info(f"Started at: {datetime.now()}")
    
    tester = NodeSystemTester()
    await tester.run_all_tests()
    
    logger.info(f"Completed at: {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())