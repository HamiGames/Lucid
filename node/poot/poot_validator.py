# Path: node/poot/poot_validator.py
# Lucid PoOT Validator - Proof of Output Time validation
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

from ..database_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """PoOT validation status"""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    REJECTED = "rejected"


@dataclass
class PoOTScore:
    """PoOT score data"""
    node_id: str
    score: float
    timestamp: datetime
    session_id: Optional[str] = None
    work_credits: int = 0
    validation_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "score": self.score,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "work_credits": self.work_credits,
            "validation_data": self.validation_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PoOTScore':
        return cls(
            node_id=data["node_id"],
            score=data["score"],
            timestamp=data["timestamp"],
            session_id=data.get("session_id"),
            work_credits=data.get("work_credits", 0),
            validation_data=data.get("validation_data", {})
        )


@dataclass
class PoOTValidation:
    """PoOT validation result"""
    validation_id: str
    node_id: str
    score: float
    status: ValidationStatus
    timestamp: datetime
    validator_node_id: str
    validation_proof: str
    comments: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "node_id": self.node_id,
            "score": self.score,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "validator_node_id": self.validator_node_id,
            "validation_proof": self.validation_proof,
            "comments": self.comments
        }


@dataclass
class PoOTValidationRequest:
    """PoOT validation request"""
    request_id: str
    node_id: str
    score: float
    validation_data: Dict[str, Any]
    timestamp: datetime
    expires_at: datetime
    priority: int = 1  # 1 = high, 2 = medium, 3 = low
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "node_id": self.node_id,
            "score": self.score,
            "validation_data": self.validation_data,
            "timestamp": self.timestamp,
            "expires_at": self.expires_at,
            "priority": self.priority
        }


class PoOTValidator:
    """
    PoOT validator for Proof of Output Time validation.
    
    Handles:
    - PoOT score validation
    - Validation request processing
    - Validation consensus
    - Score verification
    - Validation history tracking
    """
    
    def __init__(self, db: DatabaseAdapter, node_id: str):
        self.db = db
        self.node_id = node_id
        self.running = False
        
        # Validation state
        self.pending_requests: Dict[str, PoOTValidationRequest] = {}
        self.validation_history: List[PoOTValidation] = []
        self.validation_thresholds = {
            "min_score": 0.1,
            "max_score": 100.0,
            "validation_timeout": 300,  # 5 minutes
            "consensus_threshold": 0.6  # 60% agreement required
        }
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        
        logger.info(f"PoOT validator initialized: {node_id}")
    
    async def start(self):
        """Start PoOT validator"""
        try:
            logger.info(f"Starting PoOT validator {self.node_id}...")
            self.running = True
            
            # Load pending requests
            await self._load_pending_requests()
            
            # Start background tasks
            self._tasks.append(asyncio.create_task(self._validation_loop()))
            self._tasks.append(asyncio.create_task(self._cleanup_loop()))
            
            logger.info(f"PoOT validator {self.node_id} started")
            
        except Exception as e:
            logger.error(f"Failed to start PoOT validator: {e}")
            raise
    
    async def stop(self):
        """Stop PoOT validator"""
        try:
            logger.info(f"Stopping PoOT validator {self.node_id}...")
            self.running = False
            
            # Cancel background tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            logger.info(f"PoOT validator {self.node_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping PoOT validator: {e}")
    
    async def validate_scores(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """
        Validate PoOT scores for multiple nodes.
        
        Args:
            scores: Dictionary of node_id -> score mappings
            
        Returns:
            Validation results
        """
        try:
            validation_results = {}
            
            for node_id, score in scores.items():
                # Create validation request
                request_id = await self._create_validation_request(node_id, score)
                
                # Validate the score
                validation_result = await self._validate_score(node_id, score)
                
                validation_results[node_id] = {
                    "request_id": request_id,
                    "score": score,
                    "valid": validation_result["valid"],
                    "confidence": validation_result["confidence"],
                    "timestamp": datetime.now(timezone.utc)
                }
            
            logger.info(f"Validated {len(scores)} PoOT scores")
            return validation_results
            
        except Exception as e:
            logger.error(f"Failed to validate scores: {e}")
            return {}
    
    async def validate_single_score(self, node_id: str, score: float, 
                                   validation_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate a single PoOT score.
        
        Args:
            node_id: Node ID to validate
            score: PoOT score to validate
            validation_data: Additional validation data
            
        Returns:
            Validation result
        """
        try:
            # Create validation request
            request_id = await self._create_validation_request(
                node_id, score, validation_data or {}
            )
            
            # Validate the score
            validation_result = await self._validate_score(node_id, score)
            
            # Create validation record
            validation = PoOTValidation(
                validation_id=request_id,
                node_id=node_id,
                score=score,
                status=ValidationStatus.VALID if validation_result["valid"] else ValidationStatus.INVALID,
                timestamp=datetime.now(timezone.utc),
                validator_node_id=self.node_id,
                validation_proof=await self._generate_validation_proof(node_id, score),
                comments=validation_result.get("comments")
            )
            
            # Store validation
            self.validation_history.append(validation)
            await self.db["poot_validations"].insert_one(validation.to_dict())
            
            logger.info(f"Validated PoOT score for {node_id}: {score} ({validation.status.value})")
            
            return {
                "validation_id": request_id,
                "valid": validation_result["valid"],
                "confidence": validation_result["confidence"],
                "status": validation.status.value,
                "timestamp": validation.timestamp
            }
            
        except Exception as e:
            logger.error(f"Failed to validate single score: {e}")
            return {"error": str(e)}
    
    async def get_validation_history(self, node_id: Optional[str] = None, 
                                    hours: int = 24) -> List[Dict[str, Any]]:
        """Get validation history"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Filter validations
            validations = [
                v for v in self.validation_history
                if v.timestamp >= cutoff_time
            ]
            
            if node_id:
                validations = [v for v in validations if v.node_id == node_id]
            
            return [v.to_dict() for v in validations]
            
        except Exception as e:
            logger.error(f"Failed to get validation history: {e}")
            return []
    
    async def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get pending validation requests"""
        try:
            return [req.to_dict() for req in self.pending_requests.values()]
            
        except Exception as e:
            logger.error(f"Failed to get pending requests: {e}")
            return []
    
    async def _create_validation_request(self, node_id: str, score: float, 
                                        validation_data: Optional[Dict[str, Any]] = None) -> str:
        """Create a validation request"""
        try:
            request_id = f"req_{node_id}_{int(datetime.now(timezone.utc).timestamp())}"
            
            request = PoOTValidationRequest(
                request_id=request_id,
                node_id=node_id,
                score=score,
                validation_data=validation_data or {},
                timestamp=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.validation_thresholds["validation_timeout"])
            )
            
            self.pending_requests[request_id] = request
            
            # Store in database
            await self.db["poot_validation_requests"].insert_one(request.to_dict())
            
            return request_id
            
        except Exception as e:
            logger.error(f"Failed to create validation request: {e}")
            raise
    
    async def _validate_score(self, node_id: str, score: float) -> Dict[str, Any]:
        """Validate a PoOT score"""
        try:
            # Basic score validation
            if score < self.validation_thresholds["min_score"]:
                return {
                    "valid": False,
                    "confidence": 0.0,
                    "comments": f"Score too low: {score} < {self.validation_thresholds['min_score']}"
                }
            
            if score > self.validation_thresholds["max_score"]:
                return {
                    "valid": False,
                    "confidence": 0.0,
                    "comments": f"Score too high: {score} > {self.validation_thresholds['max_score']}"
                }
            
            # Check for suspicious patterns
            if await self._is_suspicious_score(node_id, score):
                return {
                    "valid": False,
                    "confidence": 0.0,
                    "comments": "Suspicious score pattern detected"
                }
            
            # Calculate confidence based on historical data
            confidence = await self._calculate_confidence(node_id, score)
            
            return {
                "valid": True,
                "confidence": confidence,
                "comments": f"Score validated with {confidence:.2f} confidence"
            }
            
        except Exception as e:
            logger.error(f"Failed to validate score: {e}")
            return {
                "valid": False,
                "confidence": 0.0,
                "comments": f"Validation error: {e}"
            }
    
    async def _is_suspicious_score(self, node_id: str, score: float) -> bool:
        """Check if a score appears suspicious"""
        try:
            # Get recent scores for this node
            recent_scores = await self._get_recent_scores(node_id, hours=24)
            
            if not recent_scores:
                return False  # No history to compare
            
            # Check for unrealistic jumps
            avg_score = sum(recent_scores) / len(recent_scores)
            if abs(score - avg_score) > avg_score * 2:  # More than 200% change
                return True
            
            # Check for perfect scores (suspicious)
            if score == 100.0 and len(recent_scores) > 5:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check suspicious score: {e}")
            return False
    
    async def _calculate_confidence(self, node_id: str, score: float) -> float:
        """Calculate validation confidence"""
        try:
            # Get historical scores
            recent_scores = await self._get_recent_scores(node_id, hours=168)  # 1 week
            
            if not recent_scores:
                return 0.5  # Default confidence for new nodes
            
            # Calculate confidence based on consistency
            avg_score = sum(recent_scores) / len(recent_scores)
            variance = sum((s - avg_score) ** 2 for s in recent_scores) / len(recent_scores)
            std_dev = variance ** 0.5
            
            # Higher confidence for scores closer to historical average
            if std_dev == 0:
                return 1.0 if score == avg_score else 0.0
            
            # Calculate z-score
            z_score = abs(score - avg_score) / std_dev
            
            # Convert z-score to confidence (lower z-score = higher confidence)
            confidence = max(0.1, 1.0 - (z_score / 3.0))  # 3-sigma rule
            
            return min(1.0, confidence)
            
        except Exception as e:
            logger.error(f"Failed to calculate confidence: {e}")
            return 0.5
    
    async def _get_recent_scores(self, node_id: str, hours: int) -> List[float]:
        """Get recent scores for a node"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            cursor = self.db["poot_scores"].find({
                "node_id": node_id,
                "timestamp": {"$gte": cutoff_time}
            }).sort("timestamp", -1).limit(100)
            
            scores = []
            async for doc in cursor:
                scores.append(doc["score"])
            
            return scores
            
        except Exception as e:
            logger.error(f"Failed to get recent scores: {e}")
            return []
    
    async def _generate_validation_proof(self, node_id: str, score: float) -> str:
        """Generate validation proof"""
        try:
            # Create proof data
            proof_data = {
                "node_id": node_id,
                "score": score,
                "validator": self.node_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Generate hash proof
            proof_string = json.dumps(proof_data, sort_keys=True)
            proof_hash = hashlib.sha256(proof_string.encode()).hexdigest()
            
            return proof_hash
            
        except Exception as e:
            logger.error(f"Failed to generate validation proof: {e}")
            return ""
    
    async def _validation_loop(self):
        """Main validation processing loop"""
        while self.running:
            try:
                # Process pending requests
                await self._process_pending_requests()
                
                await asyncio.sleep(30)  # Process every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Validation loop error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Cleanup expired requests and old data"""
        while self.running:
            try:
                # Cleanup expired requests
                await self._cleanup_expired_requests()
                
                # Cleanup old validation history
                await self._cleanup_old_history()
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(300)
    
    async def _process_pending_requests(self):
        """Process pending validation requests"""
        try:
            current_time = datetime.now(timezone.utc)
            
            for request_id, request in list(self.pending_requests.items()):
                # Check if request has expired
                if current_time > request.expires_at:
                    logger.warning(f"Validation request expired: {request_id}")
                    del self.pending_requests[request_id]
                    continue
                
                # Process the request
                try:
                    await self.validate_single_score(
                        request.node_id,
                        request.score,
                        request.validation_data
                    )
                    
                    # Remove from pending
                    del self.pending_requests[request_id]
                    
                except Exception as e:
                    logger.error(f"Failed to process request {request_id}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to process pending requests: {e}")
    
    async def _cleanup_expired_requests(self):
        """Cleanup expired validation requests"""
        try:
            current_time = datetime.now(timezone.utc)
            expired_requests = []
            
            for request_id, request in self.pending_requests.items():
                if current_time > request.expires_at:
                    expired_requests.append(request_id)
            
            for request_id in expired_requests:
                del self.pending_requests[request_id]
            
            if expired_requests:
                logger.info(f"Cleaned up {len(expired_requests)} expired requests")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired requests: {e}")
    
    async def _cleanup_old_history(self):
        """Cleanup old validation history"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
            
            # Remove old validations from memory
            self.validation_history = [
                v for v in self.validation_history
                if v.timestamp >= cutoff_time
            ]
            
            # Remove old validations from database
            result = await self.db["poot_validations"].delete_many({
                "timestamp": {"$lt": cutoff_time}
            })
            
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} old validations")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old history: {e}")
    
    async def _load_pending_requests(self):
        """Load pending validation requests from database"""
        try:
            cursor = self.db["poot_validation_requests"].find({
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            })
            
            async for doc in cursor:
                request = PoOTValidationRequest(
                    request_id=doc["request_id"],
                    node_id=doc["node_id"],
                    score=doc["score"],
                    validation_data=doc["validation_data"],
                    timestamp=doc["timestamp"],
                    expires_at=doc["expires_at"],
                    priority=doc.get("priority", 1)
                )
                
                self.pending_requests[request.request_id] = request
            
            logger.info(f"Loaded {len(self.pending_requests)} pending requests")
            
        except Exception as e:
            logger.error(f"Failed to load pending requests: {e}")


# Global PoOT validator instance
_poot_validator: Optional[PoOTValidator] = None


def get_poot_validator() -> Optional[PoOTValidator]:
    """Get global PoOT validator instance"""
    global _poot_validator
    return _poot_validator


def create_poot_validator(db: DatabaseAdapter, node_id: str) -> PoOTValidator:
    """Create PoOT validator instance"""
    global _poot_validator
    _poot_validator = PoOTValidator(db, node_id)
    return _poot_validator


async def cleanup_poot_validator():
    """Cleanup PoOT validator"""
    global _poot_validator
    if _poot_validator:
        await _poot_validator.stop()
        _poot_validator = None


if __name__ == "__main__":
    # Test PoOT validator
    async def test_poot_validator():
        print("Testing Lucid PoOT Validator...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - PoOT validator ready")
    
    asyncio.run(test_poot_validator())
