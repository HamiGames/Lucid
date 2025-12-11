#!/usr/bin/env python3
"""
Timelock Governance Integration Script

This script integrates the timelock governance system with the existing
Lucid RDP blockchain components and ensures proper spin-up.

Author: Lucid RDP Team
Version: 1.0.0
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from timelock import (
    TimelockGovernance,
    TimelockConfig,
    create_timelock_governance,
    cleanup_timelock_governance
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class TimelockIntegrator:
    """Timelock governance system integrator"""
    
    def __init__(self, mongo_uri: Optional[str] = None):
        import os
        self.mongo_uri = mongo_uri or os.getenv("MONGO_URL") or os.getenv("MONGODB_URL")
        if not self.mongo_uri:
            raise RuntimeError("mongo_uri must be provided or MONGO_URL/MONGODB_URL environment variable must be set")
        self.client: AsyncIOMotorClient = None
        self.timelock: TimelockGovernance = None
    
    async def integrate_with_blockchain(self) -> bool:
        """Integrate timelock with blockchain system"""
        try:
            logger.info("Integrating timelock with blockchain system...")
            
            # Connect to MongoDB
            self.client = AsyncIOMotorClient(self.mongo_uri)
            db = self.client.lucid
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")
            
            # Create timelock configuration
            config = TimelockConfig(
                min_delay_seconds=3600,  # 1 hour minimum
                max_delay_seconds=2592000,  # 30 days maximum
                default_grace_period=604800,  # 7 days
                max_grace_period=2592000,  # 30 days
                admin_addresses={
                    "TAdminAddress1",
                    "TAdminAddress2"
                },
                emergency_addresses={
                    "TEmergencyAddress1"
                },
                required_signatures={
                    "parameter_change": 1,
                    "contract_upgrade": 2,
                    "emergency_shutdown": 3,
                    "key_rotation": 2,
                    "node_provisioning": 1,
                    "policy_update": 1,
                    "fee_adjustment": 1,
                    "consensus_change": 3
                }
            )
            
            # Create and start timelock governance
            self.timelock = create_timelock_governance(
                db=db,
                config=config,
                output_dir="/data/timelock"
            )
            
            success = await self.timelock.start()
            if not success:
                logger.error("Failed to start timelock governance system")
                return False
            
            logger.info("Timelock governance system started successfully")
            
            # Verify integration
            stats = await self.timelock.get_system_stats()
            logger.info(f"Timelock system stats: {stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"Integration failed: {e}")
            return False
    
    async def create_sample_proposals(self) -> bool:
        """Create sample proposals for testing"""
        try:
            logger.info("Creating sample proposals...")
            
            # Sample proposal 1: Parameter change
            proposal1_id = await self.timelock.create_proposal(
                proposal_type="parameter_change",
                title="Increase Block Size Limit",
                description="Increase maximum block size from 1MB to 2MB",
                proposer="TTestProposer1",
                execution_level="normal",
                delay_seconds=86400  # 24 hours
            )
            logger.info(f"Created parameter change proposal: {proposal1_id}")
            
            # Sample proposal 2: Contract upgrade
            proposal2_id = await self.timelock.create_proposal(
                proposal_type="contract_upgrade",
                title="Upgrade Payment Router Contract",
                description="Deploy new version of payment router with improved gas efficiency",
                proposer="TTestProposer2",
                target_contract="TPaymentRouterContract",
                target_function="upgrade",
                execution_level="urgent",
                delay_seconds=14400  # 4 hours
            )
            logger.info(f"Created contract upgrade proposal: {proposal2_id}")
            
            # Sample proposal 3: Policy update
            proposal3_id = await self.timelock.create_proposal(
                proposal_type="policy_update",
                title="Update Node Requirements",
                description="Update minimum node requirements for network participation",
                proposer="TTestProposer3",
                execution_level="normal",
                delay_seconds=86400  # 24 hours
            )
            logger.info(f"Created policy update proposal: {proposal3_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create sample proposals: {e}")
            return False
    
    async def verify_system_health(self) -> bool:
        """Verify system health and integration"""
        try:
            logger.info("Verifying system health...")
            
            # Check timelock system
            if not self.timelock:
                logger.error("Timelock system not initialized")
                return False
            
            # Get system stats
            stats = await self.timelock.get_system_stats()
            logger.info(f"System stats: {stats}")
            
            # List all proposals
            proposals = await self.timelock.list_proposals(limit=10)
            logger.info(f"Found {len(proposals)} proposals")
            
            # Check database collections
            collections = await self.timelock.db.list_collection_names()
            required_collections = ["timelock_proposals", "timelock_events"]
            
            for collection in required_collections:
                if collection not in collections:
                    logger.error(f"Missing required collection: {collection}")
                    return False
            
            logger.info("System health verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Health verification failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.timelock:
                await self.timelock.stop()
                logger.info("Timelock system stopped")
            
            if self.client:
                self.client.close()
                logger.info("MongoDB connection closed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def main():
    """Main integration entry point"""
    integrator = TimelockIntegrator()
    
    try:
        # Integrate with blockchain system
        if not await integrator.integrate_with_blockchain():
            logger.error("Integration failed")
            return False
        
        # Create sample proposals
        if not await integrator.create_sample_proposals():
            logger.error("Failed to create sample proposals")
            return False
        
        # Verify system health
        if not await integrator.verify_system_health():
            logger.error("System health verification failed")
            return False
        
        logger.info("Timelock governance integration completed successfully!")
        return True
        
    finally:
        await integrator.cleanup()


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Integration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Integration failed: {e}")
        sys.exit(1)
