#!/usr/bin/env python3
"""
Timelock Governance Spin-Up Script

This script performs a complete spin-up of the timelock governance system,
including all dependencies, configuration, and integration with the Lucid RDP
blockchain system.

Author: Lucid RDP Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/data/timelock/spin_up.log')
    ]
)

logger = logging.getLogger(__name__)


class TimelockSpinUp:
    """Complete timelock governance system spin-up"""
    
    def __init__(self):
        self.config = self._load_config()
        self.steps_completed = []
        self.start_time = time.time()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load spin-up configuration"""
        default_config = {
            "mongo_uri": "mongodb://lucid:lucid@mongo-distroless:27019/lucid?authSource=admin",
            "output_dir": "/data/timelock",
            "config_file": "timelock_config.json",
            "create_sample_data": True,
            "run_tests": True,
            "verify_integration": True
        }
        
        # Override with environment variables
        if os.getenv("MONGO_URI"):
            default_config["mongo_uri"] = os.getenv("MONGO_URI")
        
        if os.getenv("LUCID_TIMELOCK_OUTPUT_DIR"):
            default_config["output_dir"] = os.getenv("LUCID_TIMELOCK_OUTPUT_DIR")
        
        return default_config
    
    async def step_1_create_directories(self) -> bool:
        """Step 1: Create necessary directories"""
        try:
            logger.info("Step 1: Creating directories...")
            
            output_dir = Path(self.config["output_dir"])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            (output_dir / "logs").mkdir(exist_ok=True)
            (output_dir / "data").mkdir(exist_ok=True)
            (output_dir / "backups").mkdir(exist_ok=True)
            
            logger.info(f"Created directories in: {output_dir}")
            self.steps_completed.append("create_directories")
            return True
            
        except Exception as e:
            logger.error(f"Step 1 failed: {e}")
            return False
    
    async def step_2_install_dependencies(self) -> bool:
        """Step 2: Install Python dependencies"""
        try:
            logger.info("Step 2: Installing dependencies...")
            
            requirements_file = Path("requirements.timelock.txt")
            if requirements_file.exists():
                import subprocess
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"Failed to install dependencies: {result.stderr}")
                    return False
                
                logger.info("Dependencies installed successfully")
            else:
                logger.warning("Requirements file not found, skipping dependency installation")
            
            self.steps_completed.append("install_dependencies")
            return True
            
        except Exception as e:
            logger.error(f"Step 2 failed: {e}")
            return False
    
    async def step_3_verify_mongodb(self) -> bool:
        """Step 3: Verify MongoDB connection"""
        try:
            logger.info("Step 3: Verifying MongoDB connection...")
            
            from motor.motor_asyncio import AsyncIOMotorClient
            
            client = AsyncIOMotorClient(self.config["mongo_uri"])
            
            # Test connection
            await client.admin.command('ping')
            logger.info("MongoDB connection verified")
            
            # Check database
            db = client.lucid
            collections = await db.list_collection_names()
            logger.info(f"Found {len(collections)} existing collections")
            
            client.close()
            self.steps_completed.append("verify_mongodb")
            return True
            
        except Exception as e:
            logger.error(f"Step 3 failed: {e}")
            return False
    
    async def step_4_initialize_timelock(self) -> bool:
        """Step 4: Initialize timelock governance system"""
        try:
            logger.info("Step 4: Initializing timelock governance system...")
            
            from motor.motor_asyncio import AsyncIOMotorClient
            from timelock import (
                TimelockGovernance,
                TimelockConfig,
                create_timelock_governance
            )
            
            # Connect to MongoDB
            client = AsyncIOMotorClient(self.config["mongo_uri"])
            db = client.lucid
            
            # Create configuration
            config = TimelockConfig(
                min_delay_seconds=3600,
                max_delay_seconds=2592000,
                default_grace_period=604800,
                max_grace_period=2592000,
                admin_addresses={
                    "TAdminAddress1",
                    "TAdminAddress2"
                },
                emergency_addresses={
                    "TEmergencyAddress1"
                }
            )
            
            # Create and start timelock
            timelock = create_timelock_governance(
                db=db,
                config=config,
                output_dir=self.config["output_dir"]
            )
            
            success = await timelock.start()
            if not success:
                logger.error("Failed to start timelock governance system")
                return False
            
            # Store reference for later steps
            self.timelock = timelock
            self.client = client
            
            logger.info("Timelock governance system initialized")
            self.steps_completed.append("initialize_timelock")
            return True
            
        except Exception as e:
            logger.error(f"Step 4 failed: {e}")
            return False
    
    async def step_5_create_sample_data(self) -> bool:
        """Step 5: Create sample governance data"""
        try:
            if not self.config.get("create_sample_data", True):
                logger.info("Step 5: Skipping sample data creation")
                self.steps_completed.append("create_sample_data")
                return True
            
            logger.info("Step 5: Creating sample governance data...")
            
            # Create sample proposals
            sample_proposals = [
                {
                    "type": "parameter_change",
                    "title": "Increase Block Gas Limit",
                    "description": "Increase maximum gas per block from 10M to 15M",
                    "proposer": "TTestProposer1",
                    "level": "normal",
                    "delay": 86400
                },
                {
                    "type": "contract_upgrade",
                    "title": "Upgrade Payment Router",
                    "description": "Deploy new payment router with improved efficiency",
                    "proposer": "TTestProposer2",
                    "level": "urgent",
                    "delay": 14400
                },
                {
                    "type": "policy_update",
                    "title": "Update Node Requirements",
                    "description": "Update minimum node specifications",
                    "proposer": "TTestProposer3",
                    "level": "normal",
                    "delay": 86400
                }
            ]
            
            created_proposals = []
            for proposal_data in sample_proposals:
                proposal_id = await self.timelock.create_proposal(
                    proposal_type=proposal_data["type"],
                    title=proposal_data["title"],
                    description=proposal_data["description"],
                    proposer=proposal_data["proposer"],
                    execution_level=proposal_data["level"],
                    delay_seconds=proposal_data["delay"]
                )
                created_proposals.append(proposal_id)
                logger.info(f"Created proposal: {proposal_id}")
            
            # Queue one proposal for demonstration
            if created_proposals:
                await self.timelock.queue_proposal(created_proposals[0], "TTestExecutor1")
                logger.info(f"Queued proposal: {created_proposals[0]}")
            
            logger.info(f"Created {len(created_proposals)} sample proposals")
            self.steps_completed.append("create_sample_data")
            return True
            
        except Exception as e:
            logger.error(f"Step 5 failed: {e}")
            return False
    
    async def step_6_run_tests(self) -> bool:
        """Step 6: Run system tests"""
        try:
            if not self.config.get("run_tests", True):
                logger.info("Step 6: Skipping tests")
                self.steps_completed.append("run_tests")
                return True
            
            logger.info("Step 6: Running system tests...")
            
            # Import and run test suite
            import subprocess
            result = subprocess.run([
                sys.executable, "test_timelock.py"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Tests failed: {result.stderr}")
                return False
            
            logger.info("All tests passed successfully")
            self.steps_completed.append("run_tests")
            return True
            
        except Exception as e:
            logger.error(f"Step 6 failed: {e}")
            return False
    
    async def step_7_verify_integration(self) -> bool:
        """Step 7: Verify system integration"""
        try:
            if not self.config.get("verify_integration", True):
                logger.info("Step 7: Skipping integration verification")
                self.steps_completed.append("verify_integration")
                return True
            
            logger.info("Step 7: Verifying system integration...")
            
            # Get system statistics
            stats = await self.timelock.get_system_stats()
            logger.info(f"System statistics: {json.dumps(stats, indent=2)}")
            
            # Verify database collections
            collections = await self.timelock.db.list_collection_names()
            required_collections = ["timelock_proposals", "timelock_events"]
            
            for collection in required_collections:
                if collection not in collections:
                    logger.error(f"Missing required collection: {collection}")
                    return False
            
            # Verify proposal data
            proposals = await self.timelock.list_proposals(limit=5)
            logger.info(f"Found {len(proposals)} proposals in system")
            
            logger.info("System integration verified successfully")
            self.steps_completed.append("verify_integration")
            return True
            
        except Exception as e:
            logger.error(f"Step 7 failed: {e}")
            return False
    
    async def step_8_generate_report(self) -> bool:
        """Step 8: Generate spin-up report"""
        try:
            logger.info("Step 8: Generating spin-up report...")
            
            end_time = time.time()
            duration = end_time - self.start_time
            
            report = {
                "spin_up_completed": True,
                "duration_seconds": duration,
                "steps_completed": self.steps_completed,
                "configuration": self.config,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "system_stats": await self.timelock.get_system_stats() if self.timelock else None
            }
            
            # Save report
            report_file = Path(self.config["output_dir"]) / "spin_up_report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Spin-up report saved to: {report_file}")
            logger.info(f"Spin-up completed in {duration:.2f} seconds")
            logger.info(f"Completed steps: {', '.join(self.steps_completed)}")
            
            self.steps_completed.append("generate_report")
            return True
            
        except Exception as e:
            logger.error(f"Step 8 failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if hasattr(self, 'timelock') and self.timelock:
                await self.timelock.stop()
                logger.info("Timelock system stopped")
            
            if hasattr(self, 'client') and self.client:
                self.client.close()
                logger.info("MongoDB connection closed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    async def run_spin_up(self) -> bool:
        """Run complete spin-up process"""
        logger.info("Starting Timelock Governance System Spin-Up...")
        
        steps = [
            ("Create Directories", self.step_1_create_directories),
            ("Install Dependencies", self.step_2_install_dependencies),
            ("Verify MongoDB", self.step_3_verify_mongodb),
            ("Initialize Timelock", self.step_4_initialize_timelock),
            ("Create Sample Data", self.step_5_create_sample_data),
            ("Run Tests", self.step_6_run_tests),
            ("Verify Integration", self.step_7_verify_integration),
            ("Generate Report", self.step_8_generate_report)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"Executing: {step_name}")
            success = await step_func()
            
            if not success:
                logger.error(f"Spin-up failed at step: {step_name}")
                return False
            
            logger.info(f"Completed: {step_name}")
        
        logger.info("Timelock Governance System Spin-Up Completed Successfully!")
        return True


async def main():
    """Main spin-up entry point"""
    spin_up = TimelockSpinUp()
    
    try:
        success = await spin_up.run_spin_up()
        return success
        
    finally:
        await spin_up.cleanup()


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Spin-up interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Spin-up failed: {e}")
        sys.exit(1)
