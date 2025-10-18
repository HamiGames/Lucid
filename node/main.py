# Path: node/main.py
# Lucid Node Management Core - Main entry point
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# Import node management components
from .config import NodeConfig, load_config
from .worker.node_worker import NodeWorker
from .worker.node_service import NodeService
from .pools.pool_service import PoolService
from .resources.resource_monitor import ResourceMonitor
from .poot.poot_validator import PoOTValidator
from .poot.poot_calculator import PoOTCalculator
from .payouts.payout_processor import PayoutProcessor
from .payouts.tron_client import TronClient
from .database_adapter import get_database_adapter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('node.log')
    ]
)

logger = logging.getLogger(__name__)

# Global node management instance
_node_manager: Optional[NodeManager] = None


class NodeManager:
    """
    Main node management system for Lucid RDP.
    
    Coordinates:
    - Worker node registration and lifecycle
    - Pool management and coordination
    - Resource monitoring and allocation
    - PoOT score calculation and validation
    - Payout processing and TRON integration
    """
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self.running = False
        
        # Core components
        self.db = None
        self.node_worker = None
        self.node_service = None
        self.pool_service = None
        self.resource_monitor = None
        self.poot_validator = None
        self.poot_calculator = None
        self.payout_processor = None
        self.tron_client = None
        
        # Background tasks
        self._tasks: list[asyncio.Task] = []
        
        logger.info(f"Node manager initialized: {config.node_id}")
    
    async def start(self):
        """Start node management system"""
        try:
            logger.info(f"Starting node manager {self.config.node_id}...")
            self.running = True
            
            # Initialize database
            self.db = await get_database_adapter()
            
            # Initialize core components
            self.node_worker = NodeWorker(
                node_address=self.config.node_address,
                private_key=self.config.private_key
            )
            
            self.node_service = NodeService(
                db=self.db,
                node_id=self.config.node_id,
                node_address=self.config.node_address
            )
            
            self.pool_service = PoolService(
                db=self.db,
                node_id=self.config.node_id
            )
            
            self.resource_monitor = ResourceMonitor(
                node_id=self.config.node_id,
                monitoring_interval=self.config.resource_monitoring_interval
            )
            
            self.poot_validator = PoOTValidator(
                db=self.db,
                node_id=self.config.node_id
            )
            
            self.poot_calculator = PoOTCalculator(
                db=self.db,
                node_id=self.config.node_id
            )
            
            self.tron_client = TronClient(
                network=self.config.tron_network,
                private_key=self.config.private_key
            )
            
            self.payout_processor = PayoutProcessor(
                db=self.db,
                tron_client=self.tron_client,
                node_id=self.config.node_id
            )
            
            # Start components
            await self.node_worker.start()
            await self.node_service.start()
            await self.pool_service.start()
            await self.resource_monitor.start()
            await self.poot_validator.start()
            await self.poot_calculator.start()
            await self.payout_processor.start()
            
            # Start background tasks
            self._tasks.append(asyncio.create_task(self._monitoring_loop()))
            self._tasks.append(asyncio.create_task(self._poot_validation_loop()))
            self._tasks.append(asyncio.create_task(self._payout_processing_loop()))
            
            logger.info(f"Node manager {self.config.node_id} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start node manager: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop node management system"""
        try:
            logger.info(f"Stopping node manager {self.config.node_id}...")
            self.running = False
            
            # Cancel background tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            # Stop components
            if self.payout_processor:
                await self.payout_processor.stop()
            if self.poot_calculator:
                await self.poot_calculator.stop()
            if self.poot_validator:
                await self.poot_validator.stop()
            if self.resource_monitor:
                await self.resource_monitor.stop()
            if self.pool_service:
                await self.pool_service.stop()
            if self.node_service:
                await self.node_service.stop()
            if self.node_worker:
                await self.node_worker.stop()
            
            logger.info(f"Node manager {self.config.node_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping node manager: {e}")
    
    async def get_node_status(self) -> Dict[str, Any]:
        """Get comprehensive node status"""
        try:
            # Get status from all components
            worker_status = await self.node_worker.get_node_status() if self.node_worker else {}
            service_status = await self.node_service.get_status() if self.node_service else {}
            pool_status = await self.pool_service.get_status() if self.pool_service else {}
            resource_status = await self.resource_monitor.get_status() if self.resource_monitor else {}
            poot_status = await self.poot_calculator.get_status() if self.poot_calculator else {}
            payout_status = await self.payout_processor.get_status() if self.payout_processor else {}
            
            return {
                "node_id": self.config.node_id,
                "node_address": self.config.node_address,
                "running": self.running,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "worker": worker_status,
                "service": service_status,
                "pool": pool_status,
                "resources": resource_status,
                "poot": poot_status,
                "payouts": payout_status
            }
            
        except Exception as e:
            logger.error(f"Failed to get node status: {e}")
            return {"error": str(e)}
    
    async def _monitoring_loop(self):
        """Continuous monitoring loop"""
        while self.running:
            try:
                # Update resource metrics
                if self.resource_monitor:
                    await self.resource_monitor.update_metrics()
                
                # Update node service status
                if self.node_service:
                    await self.node_service.update_status()
                
                # Check pool health
                if self.pool_service:
                    await self.pool_service.check_health()
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _poot_validation_loop(self):
        """Periodic PoOT validation loop"""
        while self.running:
            try:
                if self.poot_validator and self.poot_calculator:
                    # Calculate PoOT scores
                    scores = await self.poot_calculator.calculate_scores()
                    
                    # Validate PoOT scores
                    validation_results = await self.poot_validator.validate_scores(scores)
                    
                    # Update node service with validation results
                    if self.node_service:
                        await self.node_service.update_poot_scores(validation_results)
                
                await asyncio.sleep(300)  # Validate every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"PoOT validation loop error: {e}")
                await asyncio.sleep(60)
    
    async def _payout_processing_loop(self):
        """Periodic payout processing loop"""
        while self.running:
            try:
                if self.payout_processor:
                    # Process pending payouts
                    await self.payout_processor.process_pending_payouts()
                
                await asyncio.sleep(3600)  # Process payouts every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Payout processing loop error: {e}")
                await asyncio.sleep(300)


def get_node_manager() -> Optional[NodeManager]:
    """Get global node manager instance"""
    global _node_manager
    return _node_manager


def create_node_manager(config: NodeConfig) -> NodeManager:
    """Create node manager instance"""
    global _node_manager
    _node_manager = NodeManager(config)
    return _node_manager


async def cleanup_node_manager():
    """Cleanup node manager"""
    global _node_manager
    if _node_manager:
        await _node_manager.stop()
        _node_manager = None


async def main():
    """Main entry point"""
    try:
        # Load configuration
        config = load_config()
        
        # Create node manager
        node_manager = create_node_manager(config)
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            asyncio.create_task(node_manager.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start node manager
        await node_manager.start()
        
        # Keep running until stopped
        while node_manager.running:
            await asyncio.sleep(1)
        
        logger.info("Node manager shutdown complete")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
