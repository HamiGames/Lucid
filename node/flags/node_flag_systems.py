# Path: node/flags/node_flag_systems.py
# Lucid RDP Node Flag Systems - Comprehensive node status flags and operational state management
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json

# Database adapter handles compatibility
from ..database_adapter import DatabaseAdapter, get_database_adapter

# Import existing components using relative imports
from ..peer_discovery import PeerDiscovery
from ..work_credits import WorkCreditsCalculator

logger = logging.getLogger(__name__)

# Flag System Constants
FLAG_RETENTION_DAYS = int(os.getenv("FLAG_RETENTION_DAYS", "30"))  # 30 days
FLAG_SYNC_INTERVAL_SEC = int(os.getenv("FLAG_SYNC_INTERVAL_SEC", "60"))  # 1 minute
MAX_FLAGS_PER_NODE = int(os.getenv("MAX_FLAGS_PER_NODE", "100"))  # Maximum flags per node
FLAG_ESCALATION_THRESHOLD = int(os.getenv("FLAG_ESCALATION_THRESHOLD", "5"))  # Auto-escalate after 5 flags


class FlagType(Enum):
    """Types of node flags"""
    OPERATIONAL = "operational"  # Operational status flags
    PERFORMANCE = "performance"  # Performance-related flags
    SECURITY = "security"        # Security-related flags
    GOVERNANCE = "governance"    # Governance/voting flags
    COMPLIANCE = "compliance"    # Compliance and audit flags
    MAINTENANCE = "maintenance"  # Maintenance-related flags
    NETWORK = "network"         # Network connectivity flags
    RESOURCE = "resource"       # Resource availability flags


class FlagSeverity(Enum):
    """Flag severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FlagStatus(Enum):
    """Flag status states"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class FlagSource(Enum):
    """Source of flag generation"""
    SYSTEM = "system"
    PEER = "peer"
    OPERATOR = "operator"
    MONITOR = "monitor"
    GOVERNANCE = "governance"


@dataclass
class NodeFlag:
    """Node flag representation"""
    flag_id: str
    node_id: str
    flag_type: FlagType
    severity: FlagSeverity
    status: FlagStatus
    source: FlagSource
    title: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    escalation_count: int = 0
    related_flags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.flag_id,
            "node_id": self.node_id,
            "flag_type": self.flag_type.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "source": self.source.value,
            "title": self.title,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "acknowledged_at": self.acknowledged_at,
            "resolved_at": self.resolved_at,
            "expires_at": self.expires_at,
            "acknowledged_by": self.acknowledged_by,
            "resolved_by": self.resolved_by,
            "escalation_count": self.escalation_count,
            "related_flags": self.related_flags
        }


@dataclass
class FlagRule:
    """Flag generation rule"""
    rule_id: str
    name: str
    description: str
    flag_type: FlagType
    severity: FlagSeverity
    condition: str  # JSON-encoded condition
    auto_resolve: bool = False
    auto_escalate: bool = False
    expiry_hours: Optional[int] = None
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "flag_type": self.flag_type.value,
            "severity": self.severity.value,
            "condition": self.condition,
            "auto_resolve": self.auto_resolve,
            "auto_escalate": self.auto_escalate,
            "expiry_hours": self.expiry_hours,
            "enabled": self.enabled
        }


@dataclass
class FlagEvent:
    """Flag lifecycle event"""
    event_id: str
    flag_id: str
    event_type: str  # created, acknowledged, resolved, escalated, expired
    actor: str  # Who performed the action
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.event_id,
            "flag_id": self.flag_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "details": self.details,
            "timestamp": self.timestamp
        }


@dataclass
class NodeFlagSummary:
    """Summary of flags for a node"""
    node_id: str
    total_flags: int
    active_flags: int
    critical_flags: int
    high_flags: int
    medium_flags: int
    low_flags: int
    info_flags: int
    last_flag_at: Optional[datetime] = None
    flag_score: float = 0.0  # Calculated flag severity score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "total_flags": self.total_flags,
            "active_flags": self.active_flags,
            "critical_flags": self.critical_flags,
            "high_flags": self.high_flags,
            "medium_flags": self.medium_flags,
            "low_flags": self.low_flags,
            "info_flags": self.info_flags,
            "last_flag_at": self.last_flag_at,
            "flag_score": self.flag_score
        }


class NodeFlagSystem:
    """
    Node Flag System for comprehensive operational state management.
    
    Handles:
    - Flag creation, acknowledgment, and resolution
    - Automated flag generation based on rules
    - Flag severity escalation and lifecycle management
    - Network-wide flag synchronization
    - Flag-based alerting and notifications
    - Operational metrics and reporting
    """
    
    def __init__(self, db: DatabaseAdapter, peer_discovery: PeerDiscovery,
                 work_credits: WorkCreditsCalculator):
        self.db = db
        self.peer_discovery = peer_discovery
        self.work_credits = work_credits
        
        # State tracking
        self.active_flags: Dict[str, NodeFlag] = {}
        self.flag_rules: Dict[str, FlagRule] = {}
        self.node_summaries: Dict[str, NodeFlagSummary] = {}
        self.running = False
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._escalation_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._sync_task: Optional[asyncio.Task] = None
        
        logger.info("Node flag system initialized")
    
    async def start(self):
        """Start node flag system"""
        try:
            self.running = True
            
            # Setup database indexes
            await self._setup_indexes()
            
            # Load existing flags and rules
            await self._load_active_flags()
            await self._load_flag_rules()
            
            # Initialize default rules if none exist
            if not self.flag_rules:
                await self._create_default_rules()
            
            # Start background tasks
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._escalation_task = asyncio.create_task(self._escalation_loop())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._sync_task = asyncio.create_task(self._sync_loop())
            
            logger.info("Node flag system started")
            
        except Exception as e:
            logger.error(f"Failed to start node flag system: {e}")
            raise
    
    async def stop(self):
        """Stop node flag system"""
        try:
            self.running = False
            
            # Cancel background tasks
            tasks = [self._monitoring_task, self._escalation_task, self._cleanup_task, self._sync_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)
            
            logger.info("Node flag system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping node flag system: {e}")
    
    async def create_flag(self, node_id: str, flag_type: FlagType, severity: FlagSeverity,
                         title: str, description: str, source: FlagSource = FlagSource.SYSTEM,
                         metadata: Optional[Dict[str, Any]] = None,
                         expires_in_hours: Optional[int] = None) -> str:
        """
        Create a new node flag.
        
        Args:
            node_id: Target node ID
            flag_type: Type of flag
            severity: Severity level
            title: Short title
            description: Detailed description
            source: Source of the flag
            metadata: Additional metadata
            expires_in_hours: Auto-expiry time in hours
            
        Returns:
            Flag ID
        """
        try:
            flag_id = str(uuid.uuid4())
            expires_at = None
            
            if expires_in_hours:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
            
            flag = NodeFlag(
                flag_id=flag_id,
                node_id=node_id,
                flag_type=flag_type,
                severity=severity,
                status=FlagStatus.ACTIVE,
                source=source,
                title=title,
                description=description,
                metadata=metadata or {},
                expires_at=expires_at
            )
            
            # Check if node has too many flags
            node_flag_count = len([f for f in self.active_flags.values() if f.node_id == node_id])
            if node_flag_count >= MAX_FLAGS_PER_NODE:
                logger.warning(f"Node {node_id} has reached maximum flag limit")
                # Remove oldest info/low severity flags to make room
                await self._cleanup_old_flags(node_id)
            
            # Store flag
            self.active_flags[flag_id] = flag
            await self.db["node_flags"].replace_one(
                {"_id": flag_id},
                flag.to_dict(),
                upsert=True
            )
            
            # Create flag event
            await self._create_flag_event(flag_id, "created", str(source.value), {"severity": severity.value})
            
            # Update node summary
            await self._update_node_summary(node_id)
            
            logger.info(f"Flag created: {flag_id} ({severity.value}) for node {node_id}")
            return flag_id
            
        except Exception as e:
            logger.error(f"Failed to create flag: {e}")
            raise
    
    async def acknowledge_flag(self, flag_id: str, acknowledger: str) -> bool:
        """
        Acknowledge a flag.
        
        Args:
            flag_id: Flag to acknowledge
            acknowledger: Who is acknowledging
            
        Returns:
            True if acknowledged successfully
        """
        try:
            flag = self.active_flags.get(flag_id)
            if not flag:
                raise ValueError(f"Flag not found: {flag_id}")
            
            if flag.status != FlagStatus.ACTIVE:
                raise ValueError(f"Flag not in active status: {flag.status}")
            
            # Update flag
            flag.status = FlagStatus.ACKNOWLEDGED
            flag.acknowledged_at = datetime.now(timezone.utc)
            flag.acknowledged_by = acknowledger
            flag.updated_at = datetime.now(timezone.utc)
            
            # Save to database
            await self.db["node_flags"].update_one(
                {"_id": flag_id},
                {"$set": {
                    "status": flag.status.value,
                    "acknowledged_at": flag.acknowledged_at,
                    "acknowledged_by": flag.acknowledged_by,
                    "updated_at": flag.updated_at
                }}
            )
            
            # Create flag event
            await self._create_flag_event(flag_id, "acknowledged", acknowledger)
            
            # Update node summary
            await self._update_node_summary(flag.node_id)
            
            logger.info(f"Flag acknowledged: {flag_id} by {acknowledger}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge flag: {e}")
            return False
    
    async def resolve_flag(self, flag_id: str, resolver: str, resolution_notes: str = "") -> bool:
        """
        Resolve a flag.
        
        Args:
            flag_id: Flag to resolve
            resolver: Who is resolving
            resolution_notes: Optional resolution notes
            
        Returns:
            True if resolved successfully
        """
        try:
            flag = self.active_flags.get(flag_id)
            if not flag:
                raise ValueError(f"Flag not found: {flag_id}")
            
            if flag.status == FlagStatus.RESOLVED:
                raise ValueError("Flag already resolved")
            
            # Update flag
            flag.status = FlagStatus.RESOLVED
            flag.resolved_at = datetime.now(timezone.utc)
            flag.resolved_by = resolver
            flag.updated_at = datetime.now(timezone.utc)
            
            # Add resolution notes to metadata
            if resolution_notes:
                flag.metadata["resolution_notes"] = resolution_notes
            
            # Save to database
            await self.db["node_flags"].update_one(
                {"_id": flag_id},
                {"$set": {
                    "status": flag.status.value,
                    "resolved_at": flag.resolved_at,
                    "resolved_by": flag.resolved_by,
                    "updated_at": flag.updated_at,
                    "metadata": flag.metadata
                }}
            )
            
            # Create flag event
            await self._create_flag_event(flag_id, "resolved", resolver, 
                                        {"resolution_notes": resolution_notes})
            
            # Remove from active flags
            del self.active_flags[flag_id]
            
            # Update node summary
            await self._update_node_summary(flag.node_id)
            
            logger.info(f"Flag resolved: {flag_id} by {resolver}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve flag: {e}")
            return False
    
    async def get_node_flags(self, node_id: str, include_resolved: bool = False) -> List[Dict[str, Any]]:
        """
        Get flags for a specific node.
        
        Args:
            node_id: Node to get flags for
            include_resolved: Whether to include resolved flags
            
        Returns:
            List of flag dictionaries
        """
        try:
            # Get active flags
            flags = [flag.to_dict() for flag in self.active_flags.values() if flag.node_id == node_id]
            
            # Include resolved flags if requested
            if include_resolved:
                cursor = self.db["node_flags"].find({
                    "node_id": node_id,
                    "status": FlagStatus.RESOLVED.value
                }).sort("resolved_at", -1).limit(50)
                
                async for flag_doc in cursor:
                    flags.append(flag_doc)
            
            # Sort by severity and creation time
            severity_order = {
                FlagSeverity.CRITICAL.value: 0,
                FlagSeverity.HIGH.value: 1,
                FlagSeverity.MEDIUM.value: 2,
                FlagSeverity.LOW.value: 3,
                FlagSeverity.INFO.value: 4
            }
            
            flags.sort(key=lambda f: (severity_order.get(f["severity"], 5), f["created_at"]))
            
            return flags
            
        except Exception as e:
            logger.error(f"Failed to get node flags: {e}")
            return []
    
    async def get_flag_summary(self, node_id: str) -> Optional[NodeFlagSummary]:
        """Get flag summary for a node"""
        try:
            return self.node_summaries.get(node_id)
        except Exception as e:
            logger.error(f"Failed to get flag summary: {e}")
            return None
    
    async def get_network_flag_overview(self) -> Dict[str, Any]:
        """Get network-wide flag overview"""
        try:
            total_nodes = len(self.node_summaries)
            total_flags = len(self.active_flags)
            
            # Count by severity
            severity_counts = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0
            }
            
            # Count by type
            type_counts = {
                "operational": 0,
                "performance": 0,
                "security": 0,
                "governance": 0,
                "compliance": 0,
                "maintenance": 0,
                "network": 0,
                "resource": 0
            }
            
            for flag in self.active_flags.values():
                severity_counts[flag.severity.value] += 1
                type_counts[flag.flag_type.value] += 1
            
            # Calculate health score (100 - weighted flag penalty)
            health_score = 100.0
            health_score -= severity_counts["critical"] * 20
            health_score -= severity_counts["high"] * 10
            health_score -= severity_counts["medium"] * 5
            health_score -= severity_counts["low"] * 2
            health_score -= severity_counts["info"] * 0.5
            health_score = max(0.0, health_score)
            
            # Nodes with active flags
            flagged_nodes = len(set(flag.node_id for flag in self.active_flags.values()))
            healthy_nodes = total_nodes - flagged_nodes
            
            return {
                "network_health_score": health_score,
                "total_nodes": total_nodes,
                "healthy_nodes": healthy_nodes,
                "flagged_nodes": flagged_nodes,
                "total_active_flags": total_flags,
                "flags_by_severity": severity_counts,
                "flags_by_type": type_counts,
                "last_updated": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Failed to get network flag overview: {e}")
            return {"error": str(e)}
    
    async def create_flag_rule(self, name: str, description: str, flag_type: FlagType,
                              severity: FlagSeverity, condition: str,
                              auto_resolve: bool = False, auto_escalate: bool = False,
                              expiry_hours: Optional[int] = None) -> str:
        """
        Create a new flag rule.
        
        Args:
            name: Rule name
            description: Rule description
            flag_type: Type of flags to create
            severity: Severity of flags
            condition: JSON condition for rule trigger
            auto_resolve: Auto-resolve flags
            auto_escalate: Auto-escalate flags
            expiry_hours: Auto-expiry time
            
        Returns:
            Rule ID
        """
        try:
            rule_id = str(uuid.uuid4())
            
            rule = FlagRule(
                rule_id=rule_id,
                name=name,
                description=description,
                flag_type=flag_type,
                severity=severity,
                condition=condition,
                auto_resolve=auto_resolve,
                auto_escalate=auto_escalate,
                expiry_hours=expiry_hours
            )
            
            self.flag_rules[rule_id] = rule
            await self.db["flag_rules"].replace_one(
                {"_id": rule_id},
                rule.to_dict(),
                upsert=True
            )
            
            logger.info(f"Flag rule created: {rule_id} ({name})")
            return rule_id
            
        except Exception as e:
            logger.error(f"Failed to create flag rule: {e}")
            raise
    
    async def _create_flag_event(self, flag_id: str, event_type: str, actor: str,
                                details: Optional[Dict[str, Any]] = None):
        """Create a flag lifecycle event"""
        try:
            event_id = str(uuid.uuid4())
            
            event = FlagEvent(
                event_id=event_id,
                flag_id=flag_id,
                event_type=event_type,
                actor=actor,
                details=details or {}
            )
            
            await self.db["flag_events"].insert_one(event.to_dict())
            
        except Exception as e:
            logger.error(f"Failed to create flag event: {e}")
    
    async def _update_node_summary(self, node_id: str):
        """Update flag summary for a node"""
        try:
            node_flags = [flag for flag in self.active_flags.values() if flag.node_id == node_id]
            
            if not node_flags:
                # Remove empty summary
                if node_id in self.node_summaries:
                    del self.node_summaries[node_id]
                return
            
            # Count by severity
            severity_counts = {
                FlagSeverity.CRITICAL: 0,
                FlagSeverity.HIGH: 0,
                FlagSeverity.MEDIUM: 0,
                FlagSeverity.LOW: 0,
                FlagSeverity.INFO: 0
            }
            
            active_count = 0
            last_flag_at = None
            
            for flag in node_flags:
                severity_counts[flag.severity] += 1
                if flag.status == FlagStatus.ACTIVE:
                    active_count += 1
                if not last_flag_at or flag.created_at > last_flag_at:
                    last_flag_at = flag.created_at
            
            # Calculate flag score (weighted by severity)
            flag_score = (
                severity_counts[FlagSeverity.CRITICAL] * 10 +
                severity_counts[FlagSeverity.HIGH] * 5 +
                severity_counts[FlagSeverity.MEDIUM] * 2 +
                severity_counts[FlagSeverity.LOW] * 1 +
                severity_counts[FlagSeverity.INFO] * 0.1
            )
            
            summary = NodeFlagSummary(
                node_id=node_id,
                total_flags=len(node_flags),
                active_flags=active_count,
                critical_flags=severity_counts[FlagSeverity.CRITICAL],
                high_flags=severity_counts[FlagSeverity.HIGH],
                medium_flags=severity_counts[FlagSeverity.MEDIUM],
                low_flags=severity_counts[FlagSeverity.LOW],
                info_flags=severity_counts[FlagSeverity.INFO],
                last_flag_at=last_flag_at,
                flag_score=flag_score
            )
            
            self.node_summaries[node_id] = summary
            
            # Store summary in database
            await self.db["node_flag_summaries"].replace_one(
                {"_id": node_id},
                summary.to_dict(),
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Failed to update node summary: {e}")
    
    async def _monitoring_loop(self):
        """Monitor nodes and apply flag rules"""
        while self.running:
            try:
                # Get all active peers
                active_peers = await self.peer_discovery.get_active_peers()
                
                for peer in active_peers:
                    try:
                        # Check each flag rule against this node
                        await self._evaluate_flag_rules(peer.node_id)
                        
                    except Exception as peer_error:
                        logger.error(f"Flag rule evaluation failed for {peer.node_id}: {peer_error}")
                
                await asyncio.sleep(FLAG_SYNC_INTERVAL_SEC)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)
    
    async def _escalation_loop(self):
        """Handle flag escalation"""
        while self.running:
            try:
                for flag in list(self.active_flags.values()):
                    try:
                        # Check for auto-escalation conditions
                        if await self._should_escalate_flag(flag):
                            await self._escalate_flag(flag)
                        
                        # Check for expiration
                        if flag.expires_at and datetime.now(timezone.utc) > flag.expires_at:
                            await self._expire_flag(flag)
                        
                    except Exception as flag_error:
                        logger.error(f"Flag escalation check failed for {flag.flag_id}: {flag_error}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Escalation loop error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Cleanup old flags and events"""
        while self.running:
            try:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=FLAG_RETENTION_DAYS)
                
                # Clean up old resolved flags
                await self.db["node_flags"].delete_many({
                    "status": FlagStatus.RESOLVED.value,
                    "resolved_at": {"$lt": cutoff_date}
                })
                
                # Clean up old flag events
                await self.db["flag_events"].delete_many({
                    "timestamp": {"$lt": cutoff_date}
                })
                
                logger.info("Flag system cleanup completed")
                
                await asyncio.sleep(86400)  # Daily cleanup
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)
    
    async def _sync_loop(self):
        """Synchronize flags across network"""
        while self.running:
            try:
                # In a real implementation, this would sync flags with other nodes
                # For now, just update summaries
                for node_id in list(self.node_summaries.keys()):
                    await self._update_node_summary(node_id)
                
                await asyncio.sleep(FLAG_SYNC_INTERVAL_SEC * 5)  # Every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(60)
    
    async def _evaluate_flag_rules(self, node_id: str):
        """Evaluate flag rules for a node"""
        try:
            for rule in self.flag_rules.values():
                if not rule.enabled:
                    continue
                
                # Check if rule condition is met (simplified evaluation)
                if await self._evaluate_rule_condition(node_id, rule.condition):
                    # Check if similar flag already exists
                    existing_flag = None
                    for flag in self.active_flags.values():
                        if (flag.node_id == node_id and 
                            flag.flag_type == rule.flag_type and
                            flag.status == FlagStatus.ACTIVE):
                            existing_flag = flag
                            break
                    
                    if not existing_flag:
                        # Create new flag based on rule
                        await self.create_flag(
                            node_id=node_id,
                            flag_type=rule.flag_type,
                            severity=rule.severity,
                            title=f"Auto-generated: {rule.name}",
                            description=rule.description,
                            source=FlagSource.SYSTEM,
                            expires_in_hours=rule.expiry_hours
                        )
            
        except Exception as e:
            logger.error(f"Failed to evaluate flag rules: {e}")
    
    async def _evaluate_rule_condition(self, node_id: str, condition: str) -> bool:
        """Evaluate a flag rule condition (simplified)"""
        try:
            # Parse condition (simplified JSON-based evaluation)
            condition_data = json.loads(condition)
            
            # Example conditions:
            # {"type": "uptime", "operator": "lt", "value": 0.95}
            # {"type": "work_credits", "operator": "eq", "value": 0}
            # {"type": "response_time", "operator": "gt", "value": 5000}
            
            condition_type = condition_data.get("type")
            operator = condition_data.get("operator")
            expected_value = condition_data.get("value")
            
            if condition_type == "uptime":
                # Mock uptime check
                uptime = 0.98  # Would get actual uptime from node
                return self._compare_values(uptime, operator, expected_value)
            
            elif condition_type == "work_credits":
                # Check recent work credits
                recent_credits = await self.work_credits.calculate_work_credits(node_id, window_days=1)
                return self._compare_values(recent_credits, operator, expected_value)
            
            elif condition_type == "response_time":
                # Mock response time check
                response_time = 1000  # Would get actual response time
                return self._compare_values(response_time, operator, expected_value)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to evaluate condition: {e}")
            return False
    
    def _compare_values(self, actual: Union[int, float], operator: str, expected: Union[int, float]) -> bool:
        """Compare values with operator"""
        if operator == "eq":
            return actual == expected
        elif operator == "ne":
            return actual != expected
        elif operator == "lt":
            return actual < expected
        elif operator == "le":
            return actual <= expected
        elif operator == "gt":
            return actual > expected
        elif operator == "ge":
            return actual >= expected
        return False
    
    async def _should_escalate_flag(self, flag: NodeFlag) -> bool:
        """Check if flag should be escalated"""
        try:
            # Auto-escalate after threshold is reached
            if flag.escalation_count >= FLAG_ESCALATION_THRESHOLD:
                return False  # Already escalated enough
            
            # Escalate critical flags immediately if not acknowledged
            if (flag.severity == FlagSeverity.CRITICAL and 
                flag.status == FlagStatus.ACTIVE and
                flag.acknowledged_at is None):
                
                time_since_creation = datetime.now(timezone.utc) - flag.created_at
                return time_since_creation > timedelta(minutes=30)  # Escalate after 30 minutes
            
            # Escalate high severity flags after 2 hours
            if (flag.severity == FlagSeverity.HIGH and
                flag.status == FlagStatus.ACTIVE and
                flag.acknowledged_at is None):
                
                time_since_creation = datetime.now(timezone.utc) - flag.created_at
                return time_since_creation > timedelta(hours=2)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check escalation: {e}")
            return False
    
    async def _escalate_flag(self, flag: NodeFlag):
        """Escalate a flag"""
        try:
            flag.escalation_count += 1
            flag.status = FlagStatus.ESCALATED
            flag.updated_at = datetime.now(timezone.utc)
            
            # Save to database
            await self.db["node_flags"].update_one(
                {"_id": flag.flag_id},
                {"$set": {
                    "escalation_count": flag.escalation_count,
                    "status": flag.status.value,
                    "updated_at": flag.updated_at
                }}
            )
            
            # Create escalation event
            await self._create_flag_event(flag.flag_id, "escalated", "system", 
                                        {"escalation_count": flag.escalation_count})
            
            logger.warning(f"Flag escalated: {flag.flag_id} (escalation {flag.escalation_count})")
            
        except Exception as e:
            logger.error(f"Failed to escalate flag: {e}")
    
    async def _expire_flag(self, flag: NodeFlag):
        """Expire a flag"""
        try:
            flag.status = FlagStatus.EXPIRED
            flag.updated_at = datetime.now(timezone.utc)
            
            # Save to database
            await self.db["node_flags"].update_one(
                {"_id": flag.flag_id},
                {"$set": {
                    "status": flag.status.value,
                    "updated_at": flag.updated_at
                }}
            )
            
            # Create expiration event
            await self._create_flag_event(flag.flag_id, "expired", "system")
            
            # Remove from active flags
            del self.active_flags[flag.flag_id]
            
            # Update node summary
            await self._update_node_summary(flag.node_id)
            
            logger.info(f"Flag expired: {flag.flag_id}")
            
        except Exception as e:
            logger.error(f"Failed to expire flag: {e}")
    
    async def _cleanup_old_flags(self, node_id: str):
        """Clean up old flags for a node that has too many"""
        try:
            node_flags = [flag for flag in self.active_flags.values() 
                         if flag.node_id == node_id and flag.severity in [FlagSeverity.INFO, FlagSeverity.LOW]]
            
            # Sort by creation time (oldest first)
            node_flags.sort(key=lambda f: f.created_at)
            
            # Remove oldest flags
            flags_to_remove = min(10, len(node_flags))  # Remove up to 10 old flags
            for flag in node_flags[:flags_to_remove]:
                await self.resolve_flag(flag.flag_id, "system", "Auto-resolved due to flag limit")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old flags: {e}")
    
    async def _create_default_rules(self):
        """Create default flag rules"""
        try:
            default_rules = [
                {
                    "name": "Low Work Credits",
                    "description": "Node has not earned work credits recently",
                    "flag_type": FlagType.PERFORMANCE,
                    "severity": FlagSeverity.MEDIUM,
                    "condition": '{"type": "work_credits", "operator": "eq", "value": 0}',
                    "expiry_hours": 24
                },
                {
                    "name": "High Response Time",
                    "description": "Node response time is above threshold",
                    "flag_type": FlagType.PERFORMANCE,
                    "severity": FlagSeverity.LOW,
                    "condition": '{"type": "response_time", "operator": "gt", "value": 5000}',
                    "expiry_hours": 6
                },
                {
                    "name": "Low Uptime",
                    "description": "Node uptime is below required threshold",
                    "flag_type": FlagType.OPERATIONAL,
                    "severity": FlagSeverity.HIGH,
                    "condition": '{"type": "uptime", "operator": "lt", "value": 0.95}',
                    "auto_escalate": True
                }
            ]
            
            for rule_data in default_rules:
                await self.create_flag_rule(**rule_data)
            
            logger.info(f"Created {len(default_rules)} default flag rules")
            
        except Exception as e:
            logger.error(f"Failed to create default rules: {e}")
    
    async def _setup_indexes(self):
        """Setup database indexes"""
        try:
            # Node flags indexes
            await self.db["node_flags"].create_index("node_id")
            await self.db["node_flags"].create_index("flag_type")
            await self.db["node_flags"].create_index("severity")
            await self.db["node_flags"].create_index("status")
            await self.db["node_flags"].create_index("created_at")
            await self.db["node_flags"].create_index([("node_id", 1), ("status", 1)])
            
            # Flag events indexes
            await self.db["flag_events"].create_index("flag_id")
            await self.db["flag_events"].create_index("event_type")
            await self.db["flag_events"].create_index("timestamp")
            
            # Flag rules indexes
            await self.db["flag_rules"].create_index("enabled")
            await self.db["flag_rules"].create_index("flag_type")
            
            # Node flag summaries indexes
            await self.db["node_flag_summaries"].create_index("flag_score")
            await self.db["node_flag_summaries"].create_index("active_flags")
            
            logger.info("Node flag system database indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create flag system indexes: {e}")
    
    async def _load_active_flags(self):
        """Load active flags from database"""
        try:
            cursor = self.db["node_flags"].find({
                "status": {"$in": [FlagStatus.ACTIVE.value, FlagStatus.ACKNOWLEDGED.value, FlagStatus.ESCALATED.value]}
            })
            
            async for flag_doc in cursor:
                flag = NodeFlag(
                    flag_id=flag_doc["_id"],
                    node_id=flag_doc["node_id"],
                    flag_type=FlagType(flag_doc["flag_type"]),
                    severity=FlagSeverity(flag_doc["severity"]),
                    status=FlagStatus(flag_doc["status"]),
                    source=FlagSource(flag_doc["source"]),
                    title=flag_doc["title"],
                    description=flag_doc["description"],
                    metadata=flag_doc.get("metadata", {}),
                    created_at=flag_doc["created_at"],
                    updated_at=flag_doc["updated_at"],
                    acknowledged_at=flag_doc.get("acknowledged_at"),
                    resolved_at=flag_doc.get("resolved_at"),
                    expires_at=flag_doc.get("expires_at"),
                    acknowledged_by=flag_doc.get("acknowledged_by"),
                    resolved_by=flag_doc.get("resolved_by"),
                    escalation_count=flag_doc.get("escalation_count", 0),
                    related_flags=flag_doc.get("related_flags", [])
                )
                
                self.active_flags[flag.flag_id] = flag
            
            logger.info(f"Loaded {len(self.active_flags)} active flags")
            
        except Exception as e:
            logger.error(f"Failed to load active flags: {e}")
    
    async def _load_flag_rules(self):
        """Load flag rules from database"""
        try:
            cursor = self.db["flag_rules"].find({"enabled": True})
            
            async for rule_doc in cursor:
                rule = FlagRule(
                    rule_id=rule_doc["_id"],
                    name=rule_doc["name"],
                    description=rule_doc["description"],
                    flag_type=FlagType(rule_doc["flag_type"]),
                    severity=FlagSeverity(rule_doc["severity"]),
                    condition=rule_doc["condition"],
                    auto_resolve=rule_doc.get("auto_resolve", False),
                    auto_escalate=rule_doc.get("auto_escalate", False),
                    expiry_hours=rule_doc.get("expiry_hours"),
                    enabled=rule_doc.get("enabled", True)
                )
                
                self.flag_rules[rule.rule_id] = rule
            
            logger.info(f"Loaded {len(self.flag_rules)} flag rules")
            
        except Exception as e:
            logger.error(f"Failed to load flag rules: {e}")


# Global node flag system instance
_node_flag_system: Optional[NodeFlagSystem] = None


def get_node_flag_system() -> Optional[NodeFlagSystem]:
    """Get global node flag system instance"""
    global _node_flag_system
    return _node_flag_system


def create_node_flag_system(db: DatabaseAdapter, peer_discovery: PeerDiscovery,
                           work_credits: WorkCreditsCalculator) -> NodeFlagSystem:
    """Create node flag system instance"""
    global _node_flag_system
    _node_flag_system = NodeFlagSystem(db, peer_discovery, work_credits)
    return _node_flag_system


async def cleanup_node_flag_system():
    """Cleanup node flag system"""
    global _node_flag_system
    if _node_flag_system:
        await _node_flag_system.stop()
        _node_flag_system = None


if __name__ == "__main__":
    # Test node flag system
    async def test_node_flag_system():
        print("Testing Lucid Node Flag System...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - node flag system ready")
    
    asyncio.run(test_node_flag_system())