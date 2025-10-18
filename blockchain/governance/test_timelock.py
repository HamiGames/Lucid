#!/usr/bin/env python3
"""
Timelock Governance Test Script

This script tests the timelock governance functionality to ensure
proper operation of the governance system.

Usage:
    python test_timelock.py

Author: Lucid RDP Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient
from timelock import (
    TimelockGovernance,
    TimelockConfig,
    TimelockProposal,
    TimelockStatus,
    ProposalType,
    ExecutionLevel,
    create_timelock_governance,
    cleanup_timelock_governance
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class TimelockTester:
    """Timelock governance system tester"""
    
    def __init__(self, mongo_uri: str = "mongodb://lucid:lucid@mongo-distroless:27019/lucid?authSource=admin"):
        self.mongo_uri = mongo_uri
        self.client: AsyncIOMotorClient = None
        self.timelock: TimelockGovernance = None
        self.test_results = []
    
    async def setup(self) -> bool:
        """Setup test environment"""
        try:
            # Connect to MongoDB
            self.client = AsyncIOMotorClient(self.mongo_uri)
            db = self.client.lucid
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")
            
            # Create test configuration
            config = TimelockConfig(
                min_delay_seconds=1,  # Short delays for testing
                max_delay_seconds=3600,
                default_grace_period=300,  # 5 minutes for testing
                max_grace_period=3600,
                admin_addresses={"TTestAdmin1", "TTestAdmin2"},
                emergency_addresses={"TTestEmergency1"}
            )
            
            # Create timelock governance
            self.timelock = create_timelock_governance(
                db=db,
                config=config,
                output_dir="/tmp/timelock_test"
            )
            
            # Start timelock system
            success = await self.timelock.start()
            if not success:
                logger.error("Failed to start timelock governance system")
                return False
            
            logger.info("Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup test environment: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Cleanup test environment"""
        try:
            if self.timelock:
                await self.timelock.stop()
                logger.info("Timelock governance system stopped")
            
            if self.client:
                self.client.close()
                logger.info("MongoDB connection closed")
            
            logger.info("Test environment cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def test_proposal_creation(self) -> bool:
        """Test proposal creation"""
        try:
            logger.info("Testing proposal creation...")
            
            # Create test proposal
            proposal_id = await self.timelock.create_proposal(
                proposal_type=ProposalType.PARAMETER_CHANGE,
                title="Test Parameter Change",
                description="Test proposal for parameter change",
                proposer="TTestProposer1",
                execution_level=ExecutionLevel.NORMAL,
                delay_seconds=5  # 5 seconds for testing
            )
            
            if not proposal_id:
                logger.error("Failed to create proposal")
                return False
            
            # Verify proposal exists
            proposal = await self.timelock.get_proposal(proposal_id)
            if not proposal:
                logger.error("Created proposal not found")
                return False
            
            if proposal.status != TimelockStatus.PENDING:
                logger.error(f"Proposal status incorrect: {proposal.status}")
                return False
            
            logger.info(f"Proposal created successfully: {proposal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Proposal creation test failed: {e}")
            return False
    
    async def test_proposal_queueing(self) -> bool:
        """Test proposal queueing"""
        try:
            logger.info("Testing proposal queueing...")
            
            # Create test proposal
            proposal_id = await self.timelock.create_proposal(
                proposal_type=ProposalType.CONTRACT_UPGRADE,
                title="Test Contract Upgrade",
                description="Test proposal for contract upgrade",
                proposer="TTestProposer2",
                execution_level=ExecutionLevel.URGENT,
                delay_seconds=3  # 3 seconds for testing
            )
            
            # Queue proposal
            success = await self.timelock.queue_proposal(proposal_id, "TTestExecutor1")
            if not success:
                logger.error("Failed to queue proposal")
                return False
            
            # Verify proposal is queued
            proposal = await self.timelock.get_proposal(proposal_id)
            if proposal.status != TimelockStatus.QUEUED:
                logger.error(f"Proposal not queued: {proposal.status}")
                return False
            
            if not proposal.executable_at:
                logger.error("Executable time not set")
                return False
            
            logger.info(f"Proposal queued successfully: {proposal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Proposal queueing test failed: {e}")
            return False
    
    async def test_proposal_execution(self) -> bool:
        """Test proposal execution"""
        try:
            logger.info("Testing proposal execution...")
            
            # Create and queue test proposal
            proposal_id = await self.timelock.create_proposal(
                proposal_type=ProposalType.POLICY_UPDATE,
                title="Test Policy Update",
                description="Test proposal for policy update",
                proposer="TTestProposer3",
                execution_level=ExecutionLevel.EMERGENCY,
                delay_seconds=2  # 2 seconds for testing
            )
            
            await self.timelock.queue_proposal(proposal_id, "TTestExecutor2")
            
            # Wait for proposal to become executable
            await asyncio.sleep(3)
            
            # Execute proposal
            success = await self.timelock.execute_proposal(
                proposal_id, 
                "TTestExecutor2", 
                "0x1234567890abcdef"
            )
            
            if not success:
                logger.error("Failed to execute proposal")
                return False
            
            # Verify proposal is executed
            proposal = await self.timelock.get_proposal(proposal_id)
            if proposal.status != TimelockStatus.EXECUTED:
                logger.error(f"Proposal not executed: {proposal.status}")
                return False
            
            if not proposal.executed_at:
                logger.error("Execution time not set")
                return False
            
            logger.info(f"Proposal executed successfully: {proposal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Proposal execution test failed: {e}")
            return False
    
    async def test_proposal_cancellation(self) -> bool:
        """Test proposal cancellation"""
        try:
            logger.info("Testing proposal cancellation...")
            
            # Create test proposal
            proposal_id = await self.timelock.create_proposal(
                proposal_type=ProposalType.FEE_ADJUSTMENT,
                title="Test Fee Adjustment",
                description="Test proposal for fee adjustment",
                proposer="TTestProposer4",
                execution_level=ExecutionLevel.NORMAL,
                delay_seconds=10  # 10 seconds for testing
            )
            
            # Cancel proposal
            success = await self.timelock.cancel_proposal(proposal_id, "TTestCanceller1")
            if not success:
                logger.error("Failed to cancel proposal")
                return False
            
            # Verify proposal is cancelled
            proposal = await self.timelock.get_proposal(proposal_id)
            if proposal.status != TimelockStatus.CANCELLED:
                logger.error(f"Proposal not cancelled: {proposal.status}")
                return False
            
            if not proposal.cancelled_at:
                logger.error("Cancellation time not set")
                return False
            
            logger.info(f"Proposal cancelled successfully: {proposal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Proposal cancellation test failed: {e}")
            return False
    
    async def test_system_stats(self) -> bool:
        """Test system statistics"""
        try:
            logger.info("Testing system statistics...")
            
            stats = await self.timelock.get_system_stats()
            
            required_keys = [
                "active_proposals",
                "execution_queue",
                "executable_proposals",
                "proposals_by_status",
                "proposals_by_type"
            ]
            
            for key in required_keys:
                if key not in stats:
                    logger.error(f"Missing stat key: {key}")
                    return False
            
            logger.info(f"System stats: {json.dumps(stats, indent=2)}")
            return True
            
        except Exception as e:
            logger.error(f"System stats test failed: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all tests"""
        logger.info("Starting timelock governance tests...")
        
        tests = [
            ("Proposal Creation", self.test_proposal_creation),
            ("Proposal Queueing", self.test_proposal_queueing),
            ("Proposal Execution", self.test_proposal_execution),
            ("Proposal Cancellation", self.test_proposal_cancellation),
            ("System Statistics", self.test_system_stats)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                if result:
                    logger.info(f"✓ {test_name} test passed")
                    passed += 1
                else:
                    logger.error(f"✗ {test_name} test failed")
            except Exception as e:
                logger.error(f"✗ {test_name} test error: {e}")
        
        logger.info(f"Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("All tests passed! ✓")
            return True
        else:
            logger.error("Some tests failed! ✗")
            return False


async def main():
    """Main test entry point"""
    tester = TimelockTester()
    
    try:
        # Setup test environment
        if not await tester.setup():
            logger.error("Failed to setup test environment")
            return False
        
        # Run tests
        success = await tester.run_all_tests()
        
        return success
        
    finally:
        # Cleanup
        await tester.cleanup()


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)
