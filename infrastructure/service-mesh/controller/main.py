"""
Lucid Service Mesh Controller - Main Entry Point
Service mesh controller for cross-cluster integration.

File: infrastructure/service-mesh/controller/main.py
Lines: ~200
Purpose: Service mesh controller entry point
Dependencies: asyncio, logging, config_manager, policy_engine, health_checker
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any
from datetime import datetime

from .config_manager import ConfigManager
from .policy_engine import PolicyEngine
from .health_checker import HealthChecker

logger = logging.getLogger(__name__)


class ServiceMeshController:
    """
    Main service mesh controller.
    
    Responsibilities:
    - Service discovery coordination
    - Policy enforcement
    - Health monitoring
    - Configuration management
    - Service mesh orchestration
    """
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.policy_engine = PolicyEngine()
        self.health_checker = HealthChecker()
        
        self.running = False
        self.tasks: Dict[str, asyncio.Task] = {}
        
    async def initialize(self):
        """Initialize service mesh controller components."""
        try:
            logger.info("Initializing Service Mesh Controller...")
            
            # Load configuration
            await self.config_manager.load_config()
            logger.info("Configuration loaded")
            
            # Initialize policy engine
            await self.policy_engine.initialize()
            logger.info("Policy engine initialized")
            
            # Initialize health checker
            await self.health_checker.initialize()
            logger.info("Health checker initialized")
            
            logger.info("Service Mesh Controller initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Service Mesh Controller: {e}")
            raise
            
    async def start(self):
        """Start the service mesh controller."""
        try:
            self.running = True
            logger.info("Starting Service Mesh Controller...")
            
            # Start background tasks
            self.tasks["policy_enforcement"] = asyncio.create_task(
                self._policy_enforcement_loop()
            )
            self.tasks["health_monitoring"] = asyncio.create_task(
                self._health_monitoring_loop()
            )
            self.tasks["config_watcher"] = asyncio.create_task(
                self._config_watcher_loop()
            )
            
            logger.info("Service Mesh Controller started")
            
            # Keep running until shutdown
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in Service Mesh Controller: {e}")
            raise
        finally:
            await self.shutdown()
            
    async def shutdown(self):
        """Shutdown the service mesh controller."""
        logger.info("Shutting down Service Mesh Controller...")
        
        self.running = False
        
        # Cancel all tasks
        for task_name, task in self.tasks.items():
            if not task.done():
                logger.info(f"Cancelling task: {task_name}")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        # Cleanup components
        await self.health_checker.cleanup()
        await self.policy_engine.cleanup()
        await self.config_manager.cleanup()
        
        logger.info("Service Mesh Controller shutdown complete")
        
    async def _policy_enforcement_loop(self):
        """Background task for policy enforcement."""
        while self.running:
            try:
                await self.policy_engine.enforce_policies()
                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Policy enforcement error: {e}")
                await asyncio.sleep(10)  # Wait longer on error
                
    async def _health_monitoring_loop(self):
        """Background task for health monitoring."""
        while self.running:
            try:
                await self.health_checker.check_all_services()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
                
    async def _config_watcher_loop(self):
        """Background task for configuration watching."""
        while self.running:
            try:
                await self.config_manager.watch_for_changes()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Config watcher error: {e}")
                await asyncio.sleep(30)  # Wait longer on error
                
    def get_status(self) -> Dict[str, Any]:
        """Get controller status."""
        return {
            "status": "running" if self.running else "stopped",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "config_manager": self.config_manager.get_status(),
                "policy_engine": self.policy_engine.get_status(),
                "health_checker": self.health_checker.get_status(),
            },
            "tasks": {
                name: "running" if not task.done() else "stopped"
                for name, task in self.tasks.items()
            }
        }


async def main():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create controller
    controller = ServiceMeshController()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(controller.shutdown())
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize and start
        await controller.initialize()
        await controller.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
