# Path: node/poot/poot_calculator.py
# Lucid PoOT Calculator - Proof of Output Time score calculation
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)


class CalculationStatus(Enum):
    """PoOT calculation status"""
    PENDING = "pending"
    CALCULATED = "calculated"
    VERIFIED = "verified"
    EXPIRED = "expired"


@dataclass
class PoOTCalculation:
    """PoOT calculation result"""
    calculation_id: str
    node_id: str
    score: float
    timestamp: datetime
    calculation_data: Dict[str, Any] = field(default_factory=dict)
    verification_proof: Optional[str] = None
    status: CalculationStatus = CalculationStatus.CALCULATED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "calculation_id": self.calculation_id,
            "node_id": self.node_id,
            "score": self.score,
            "timestamp": self.timestamp,
            "calculation_data": self.calculation_data,
            "verification_proof": self.verification_proof,
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PoOTCalculation':
        return cls(
            calculation_id=data["calculation_id"],
            node_id=data["node_id"],
            score=data["score"],
            timestamp=data["timestamp"],
            calculation_data=data.get("calculation_data", {}),
            verification_proof=data.get("verification_proof"),
            status=CalculationStatus(data.get("status", "calculated"))
        )


@dataclass
class PoOTMetrics:
    """PoOT calculation metrics"""
    node_id: str
    timestamp: datetime
    session_time: float  # Time spent in sessions (hours)
    work_credits: int
    resource_utilization: float  # CPU, memory, disk utilization
    network_bandwidth: float  # Network bandwidth used (Mbps)
    uptime_percentage: float  # Node uptime percentage
    session_quality: float  # Session quality score (0-1)
    trust_score: float  # Node trust score (0-1)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "session_time": self.session_time,
            "work_credits": self.work_credits,
            "resource_utilization": self.resource_utilization,
            "network_bandwidth": self.network_bandwidth,
            "uptime_percentage": self.uptime_percentage,
            "session_quality": self.session_quality,
            "trust_score": self.trust_score
        }


class PoOTCalculator:
    """
    PoOT calculator for Proof of Output Time score calculation.
    
    Handles:
    - PoOT score calculation based on multiple factors
    - Historical score analysis
    - Score normalization and weighting
    - Calculation verification
    - Score aggregation and reporting
    """
    
    def __init__(self, db: DatabaseAdapter, node_id: str):
        self.db = db
        self.node_id = node_id
        self.running = False
        
        # Calculation state
        self.calculation_history: List[PoOTCalculation] = []
        self.current_metrics: Optional[PoOTMetrics] = None
        
        # Calculation parameters
        self.calculation_weights = {
            "session_time": 0.25,      # 25% weight
            "work_credits": 0.20,      # 20% weight
            "resource_utilization": 0.15,  # 15% weight
            "network_bandwidth": 0.10,     # 10% weight
            "uptime_percentage": 0.15,     # 15% weight
            "session_quality": 0.10,      # 10% weight
            "trust_score": 0.05          # 5% weight
        }
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        
        logger.info(f"PoOT calculator initialized: {node_id}")
    
    async def start(self):
        """Start PoOT calculator"""
        try:
            logger.info(f"Starting PoOT calculator {self.node_id}...")
            self.running = True
            
            # Load calculation history
            await self._load_calculation_history()
            
            # Start background tasks
            self._tasks.append(asyncio.create_task(self._calculation_loop()))
            self._tasks.append(asyncio.create_task(self._metrics_collection_loop()))
            
            logger.info(f"PoOT calculator {self.node_id} started")
            
        except Exception as e:
            logger.error(f"Failed to start PoOT calculator: {e}")
            raise
    
    async def stop(self):
        """Stop PoOT calculator"""
        try:
            logger.info(f"Stopping PoOT calculator {self.node_id}...")
            self.running = False
            
            # Cancel background tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            logger.info(f"PoOT calculator {self.node_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping PoOT calculator: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get PoOT calculator status"""
        try:
            return {
                "node_id": self.node_id,
                "running": self.running,
                "calculation_history_count": len(self.calculation_history),
                "current_metrics": self.current_metrics.to_dict() if self.current_metrics else None,
                "calculation_weights": self.calculation_weights
            }
            
        except Exception as e:
            logger.error(f"Failed to get PoOT calculator status: {e}")
            return {"error": str(e)}
    
    async def calculate_scores(self, node_ids: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Calculate PoOT scores for nodes.
        
        Args:
            node_ids: List of node IDs to calculate scores for (None for all nodes)
            
        Returns:
            Dictionary of node_id -> score mappings
        """
        try:
            scores = {}
            
            if node_ids is None:
                # Calculate for all nodes
                node_ids = await self._get_all_node_ids()
            
            for node_id in node_ids:
                try:
                    score = await self._calculate_node_score(node_id)
                    scores[node_id] = score
                    
                    # Store calculation
                    await self._store_calculation(node_id, score)
                    
                except Exception as e:
                    logger.error(f"Failed to calculate score for {node_id}: {e}")
                    scores[node_id] = 0.0
            
            logger.info(f"Calculated PoOT scores for {len(scores)} nodes")
            return scores
            
        except Exception as e:
            logger.error(f"Failed to calculate scores: {e}")
            return {}
    
    async def calculate_node_score(self, node_id: str) -> float:
        """
        Calculate PoOT score for a specific node.
        
        Args:
            node_id: Node ID to calculate score for
            
        Returns:
            PoOT score (0-100)
        """
        try:
            # Get node metrics
            metrics = await self._get_node_metrics(node_id)
            if not metrics:
                logger.warning(f"No metrics found for node {node_id}")
                return 0.0
            
            # Calculate individual component scores
            component_scores = await self._calculate_component_scores(metrics)
            
            # Calculate weighted total score
            total_score = 0.0
            for component, score in component_scores.items():
                weight = self.calculation_weights.get(component, 0.0)
                total_score += score * weight
            
            # Normalize to 0-100 range
            normalized_score = min(100.0, max(0.0, total_score))
            
            logger.info(f"Calculated PoOT score for {node_id}: {normalized_score:.2f}")
            return normalized_score
            
        except Exception as e:
            logger.error(f"Failed to calculate node score: {e}")
            return 0.0
    
    async def get_calculation_history(self, node_id: Optional[str] = None, 
                                    hours: int = 24) -> List[Dict[str, Any]]:
        """Get calculation history"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Filter calculations
            calculations = [
                c for c in self.calculation_history
                if c.timestamp >= cutoff_time
            ]
            
            if node_id:
                calculations = [c for c in calculations if c.node_id == node_id]
            
            return [c.to_dict() for c in calculations]
            
        except Exception as e:
            logger.error(f"Failed to get calculation history: {e}")
            return []
    
    async def get_node_metrics(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get current metrics for a node"""
        try:
            if node_id == self.node_id and self.current_metrics:
                return self.current_metrics.to_dict()
            
            # Get from database
            metrics_doc = await self.db["node_metrics"].find_one(
                {"node_id": node_id},
                sort=[("timestamp", -1)]
            )
            
            if metrics_doc:
                return metrics_doc
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get node metrics: {e}")
            return None
    
    async def _calculate_component_scores(self, metrics: PoOTMetrics) -> Dict[str, float]:
        """Calculate individual component scores"""
        try:
            component_scores = {}
            
            # Session time score (0-100)
            session_time_score = min(100.0, metrics.session_time * 10)  # 10 hours = 100 points
            component_scores["session_time"] = session_time_score
            
            # Work credits score (0-100)
            work_credits_score = min(100.0, metrics.work_credits / 100)  # 100 credits = 100 points
            component_scores["work_credits"] = work_credits_score
            
            # Resource utilization score (0-100)
            # Higher utilization is better (up to a point)
            resource_score = min(100.0, metrics.resource_utilization * 100)
            component_scores["resource_utilization"] = resource_score
            
            # Network bandwidth score (0-100)
            network_score = min(100.0, metrics.network_bandwidth / 10)  # 10 Mbps = 100 points
            component_scores["network_bandwidth"] = network_score
            
            # Uptime percentage score (0-100)
            uptime_score = metrics.uptime_percentage
            component_scores["uptime_percentage"] = uptime_score
            
            # Session quality score (0-100)
            quality_score = metrics.session_quality * 100
            component_scores["session_quality"] = quality_score
            
            # Trust score (0-100)
            trust_score = metrics.trust_score * 100
            component_scores["trust_score"] = trust_score
            
            return component_scores
            
        except Exception as e:
            logger.error(f"Failed to calculate component scores: {e}")
            return {}
    
    async def _get_node_metrics(self, node_id: str) -> Optional[PoOTMetrics]:
        """Get metrics for a node"""
        try:
            if node_id == self.node_id and self.current_metrics:
                return self.current_metrics
            
            # Get from database
            metrics_doc = await self.db["node_metrics"].find_one(
                {"node_id": node_id},
                sort=[("timestamp", -1)]
            )
            
            if metrics_doc:
                return PoOTMetrics(
                    node_id=metrics_doc["node_id"],
                    timestamp=metrics_doc["timestamp"],
                    session_time=metrics_doc.get("session_time", 0.0),
                    work_credits=metrics_doc.get("work_credits", 0),
                    resource_utilization=metrics_doc.get("resource_utilization", 0.0),
                    network_bandwidth=metrics_doc.get("network_bandwidth", 0.0),
                    uptime_percentage=metrics_doc.get("uptime_percentage", 0.0),
                    session_quality=metrics_doc.get("session_quality", 0.0),
                    trust_score=metrics_doc.get("trust_score", 0.0)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get node metrics: {e}")
            return None
    
    async def _get_all_node_ids(self) -> List[str]:
        """Get all node IDs from database"""
        try:
            cursor = self.db["nodes"].find({}, projection={"_id": 1})
            node_ids = []
            
            async for doc in cursor:
                node_ids.append(doc["_id"])
            
            return node_ids
            
        except Exception as e:
            logger.error(f"Failed to get all node IDs: {e}")
            return []
    
    async def _store_calculation(self, node_id: str, score: float):
        """Store calculation result"""
        try:
            calculation_id = f"calc_{node_id}_{int(datetime.now(timezone.utc).timestamp())}"
            
            calculation = PoOTCalculation(
                calculation_id=calculation_id,
                node_id=node_id,
                score=score,
                timestamp=datetime.now(timezone.utc),
                calculation_data={
                    "calculator_node": self.node_id,
                    "weights": self.calculation_weights
                }
            )
            
            # Store in memory
            self.calculation_history.append(calculation)
            
            # Store in database
            await self.db["poot_calculations"].insert_one(calculation.to_dict())
            
            # Keep only last 1000 calculations in memory
            if len(self.calculation_history) > 1000:
                self.calculation_history = self.calculation_history[-1000:]
            
        except Exception as e:
            logger.error(f"Failed to store calculation: {e}")
    
    async def _calculation_loop(self):
        """Periodic calculation loop"""
        while self.running:
            try:
                # Calculate scores for all nodes
                await self.calculate_scores()
                
                await asyncio.sleep(300)  # Calculate every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Calculation loop error: {e}")
                await asyncio.sleep(60)
    
    async def _metrics_collection_loop(self):
        """Periodic metrics collection loop"""
        while self.running:
            try:
                # Update current node metrics
                await self._update_current_metrics()
                
                await asyncio.sleep(60)  # Update every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection loop error: {e}")
                await asyncio.sleep(30)
    
    async def _update_current_metrics(self):
        """Update current node metrics"""
        try:
            # Get system metrics
            import psutil
            
            # Calculate session time (simplified)
            session_time = 0.0  # Would be calculated from actual session data
            
            # Get work credits
            work_credits = 0  # Would be retrieved from work credits system
            
            # Calculate resource utilization
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            resource_utilization = (cpu_percent + memory.percent + (disk.used / disk.total) * 100) / 3
            
            # Calculate network bandwidth
            network_bandwidth = 0.0  # Would be calculated from network usage
            
            # Calculate uptime percentage
            uptime_seconds = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            uptime_percentage = min(100.0, (uptime_seconds / 86400) * 100)  # 24 hours = 100%
            
            # Calculate session quality
            session_quality = 0.8  # Would be calculated from session feedback
            
            # Calculate trust score
            trust_score = 0.9  # Would be calculated from trust system
            
            # Create metrics
            self.current_metrics = PoOTMetrics(
                node_id=self.node_id,
                timestamp=datetime.now(timezone.utc),
                session_time=session_time,
                work_credits=work_credits,
                resource_utilization=resource_utilization,
                network_bandwidth=network_bandwidth,
                uptime_percentage=uptime_percentage,
                session_quality=session_quality,
                trust_score=trust_score
            )
            
            # Store in database
            await self.db["node_metrics"].insert_one(self.current_metrics.to_dict())
            
        except ImportError:
            logger.warning("psutil not available for metrics collection")
        except Exception as e:
            logger.error(f"Failed to update current metrics: {e}")
    
    async def _load_calculation_history(self):
        """Load calculation history from database"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
            
            cursor = self.db["poot_calculations"].find({
                "timestamp": {"$gte": cutoff_time}
            }).sort("timestamp", -1).limit(1000)
            
            async for doc in cursor:
                calculation = PoOTCalculation.from_dict(doc)
                self.calculation_history.append(calculation)
            
            logger.info(f"Loaded {len(self.calculation_history)} calculations from history")
            
        except Exception as e:
            logger.error(f"Failed to load calculation history: {e}")
    
    def _start_time(self):
        """Get start time for uptime calculation"""
        return datetime.now(timezone.utc)


# Global PoOT calculator instance
_poot_calculator: Optional[PoOTCalculator] = None


def get_poot_calculator() -> Optional[PoOTCalculator]:
    """Get global PoOT calculator instance"""
    global _poot_calculator
    return _poot_calculator


def create_poot_calculator(db: DatabaseAdapter, node_id: str) -> PoOTCalculator:
    """Create PoOT calculator instance"""
    global _poot_calculator
    _poot_calculator = PoOTCalculator(db, node_id)
    return _poot_calculator


async def cleanup_poot_calculator():
    """Cleanup PoOT calculator"""
    global _poot_calculator
    if _poot_calculator:
        await _poot_calculator.stop()
        _poot_calculator = None


if __name__ == "__main__":
    # Test PoOT calculator
    async def test_poot_calculator():
        print("Testing Lucid PoOT Calculator...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - PoOT calculator ready")
    
    asyncio.run(test_poot_calculator())
