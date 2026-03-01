# Path: gui/user/policy_controller.py
"""
Client-side policy enforcement for Lucid RDP GUI.
Provides policy validation, enforcement, and compliance monitoring for RDP sessions.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time

from ..core.config_manager import get_config_manager
from ..core.security import get_security_validator, CryptographicUtils
from ..core.networking import TorHttpClient, SecurityConfig

logger = logging.getLogger(__name__)


class PolicyViolationType(Enum):
    """Policy violation types"""
    INPUT_BLOCKED = "input_blocked"
    FILE_TRANSFER_DENIED = "file_transfer_denied"
    CLIPBOARD_DENIED = "clipboard_denied"
    SYSTEM_ACCESS_DENIED = "system_access_denied"
    AUTHENTICATION_FAILED = "authentication_failed"
    SESSION_POLICY_MISMATCH = "session_policy_mismatch"
    CONSENT_REVOKED = "consent_revoked"


class PolicyEnforcementLevel(Enum):
    """Policy enforcement levels"""
    WARNING = "warning"      # Log violation but allow action
    BLOCK = "block"          # Block action and log violation
    TERMINATE = "terminate"  # Terminate session on violation


@dataclass
class PolicyViolation:
    """Policy violation record"""
    violation_id: str
    violation_type: PolicyViolationType
    timestamp: datetime
    session_id: str
    user_action: str
    policy_rule: str
    enforcement_level: PolicyEnforcementLevel
    details: Dict[str, Any]
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['violation_type'] = self.violation_type.value
        data['enforcement_level'] = self.enforcement_level.value
        return data


@dataclass
class PolicyRule:
    """Individual policy rule"""
    rule_id: str
    rule_name: str
    description: str
    enabled: bool
    enforcement_level: PolicyEnforcementLevel
    conditions: Dict[str, Any]
    actions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class SessionPolicy:
    """Complete session policy configuration"""
    policy_id: str
    policy_name: str
    version: str
    created_at: datetime
    rules: List[PolicyRule]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data
    
    def calculate_hash(self) -> str:
        """Calculate policy hash for integrity verification"""
        policy_data = {
            'policy_id': self.policy_id,
            'version': self.version,
            'rules': [rule.to_dict() for rule in self.rules]
        }
        json_str = json.dumps(policy_data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()


class PolicyEnforcer:
    """Enforces session policies and monitors compliance"""
    
    def __init__(self):
        self.active_policies: Dict[str, SessionPolicy] = {}
        self.violations: List[PolicyViolation] = []
        self.violation_callbacks: List[Callable[[PolicyViolation], None]] = []
        self.policy_callbacks: List[Callable[[SessionPolicy], None]] = []
        self._lock = threading.Lock()
        
        # Policy enforcement state
        self.enforcement_enabled = True
        self.auto_resolve_violations = False
        self.violation_threshold = 5  # Terminate after N violations
        
        logger.debug("Policy enforcer initialized")
    
    def add_violation_callback(self, callback: Callable[[PolicyViolation], None]) -> None:
        """Add violation notification callback"""
        self.violation_callbacks.append(callback)
    
    def add_policy_callback(self, callback: Callable[[SessionPolicy], None]) -> None:
        """Add policy change notification callback"""
        self.policy_callbacks.append(callback)
    
    def load_policy(self, policy_data: Dict[str, Any]) -> bool:
        """Load and activate a session policy"""
        try:
            policy = SessionPolicy(
                policy_id=policy_data['policy_id'],
                policy_name=policy_data['policy_name'],
                version=policy_data['version'],
                created_at=datetime.fromisoformat(policy_data['created_at']),
                rules=[PolicyRule(**rule) for rule in policy_data['rules']],
                metadata=policy_data.get('metadata', {})
            )
            
            with self._lock:
                self.active_policies[policy.policy_id] = policy
            
            # Notify callbacks
            for callback in self.policy_callbacks:
                try:
                    callback(policy)
                except Exception as e:
                    logger.error(f"Policy callback failed: {e}")
            
            logger.info(f"Loaded policy: {policy.policy_name} (v{policy.version})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load policy: {e}")
            return False
    
    def unload_policy(self, policy_id: str) -> bool:
        """Unload and deactivate a session policy"""
        with self._lock:
            if policy_id in self.active_policies:
                policy = self.active_policies.pop(policy_id)
                logger.info(f"Unloaded policy: {policy.policy_name}")
                return True
        return False
    
    def validate_action(self, 
                       session_id: str, 
                       action_type: str, 
                       action_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate an action against active policies.
        
        Returns:
            Tuple of (is_allowed, violation_reason)
        """
        if not self.enforcement_enabled:
            return True, None
        
        with self._lock:
            # Check all active policies
            for policy in self.active_policies.values():
                for rule in policy.rules:
                    if not rule.enabled:
                        continue
                    
                    # Check if rule applies to this action
                    if self._rule_applies(rule, action_type, action_data):
                        # Check conditions
                        if self._evaluate_conditions(rule.conditions, action_data):
                            # Rule triggered - check enforcement level
                            if rule.enforcement_level == PolicyEnforcementLevel.BLOCK:
                                violation = self._record_violation(
                                    session_id, PolicyViolationType.SESSION_POLICY_MISMATCH,
                                    action_type, rule.rule_name, rule.enforcement_level,
                                    {'rule_id': rule.rule_id, 'policy_id': policy.policy_id}
                                )
                                return False, f"Action blocked by policy rule: {rule.rule_name}"
                            
                            elif rule.enforcement_level == PolicyEnforcementLevel.TERMINATE:
                                violation = self._record_violation(
                                    session_id, PolicyViolationType.SESSION_POLICY_MISMATCH,
                                    action_type, rule.rule_name, rule.enforcement_level,
                                    {'rule_id': rule.rule_id, 'policy_id': policy.policy_id}
                                )
                                return False, f"Session terminated by policy rule: {rule.rule_name}"
        
        return True, None
    
    def _rule_applies(self, rule: PolicyRule, action_type: str, action_data: Dict[str, Any]) -> bool:
        """Check if a rule applies to the given action"""
        # Simple action type matching for now
        # This could be extended with more sophisticated matching logic
        rule_actions = rule.actions
        return action_type in rule_actions or '*' in rule_actions
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], action_data: Dict[str, Any]) -> bool:
        """Evaluate rule conditions against action data"""
        try:
            # Simple condition evaluation
            # This could be extended with more sophisticated logic
            
            for condition_key, expected_value in conditions.items():
                if condition_key not in action_data:
                    return False
                
                actual_value = action_data[condition_key]
                
                # Type-specific comparison
                if isinstance(expected_value, dict):
                    # Complex condition (e.g., range, regex)
                    if 'operator' in expected_value:
                        operator = expected_value['operator']
                        compare_value = expected_value['value']
                        
                        if operator == 'equals':
                            if actual_value != compare_value:
                                return False
                        elif operator == 'not_equals':
                            if actual_value == compare_value:
                                return False
                        elif operator == 'greater_than':
                            if actual_value <= compare_value:
                                return False
                        elif operator == 'less_than':
                            if actual_value >= compare_value:
                                return False
                        elif operator == 'contains':
                            if compare_value not in str(actual_value):
                                return False
                        elif operator == 'regex':
                            import re
                            if not re.match(compare_value, str(actual_value)):
                                return False
                else:
                    # Simple equality check
                    if actual_value != expected_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            return False
    
    def _record_violation(self, 
                         session_id: str,
                         violation_type: PolicyViolationType,
                         user_action: str,
                         policy_rule: str,
                         enforcement_level: PolicyEnforcementLevel,
                         details: Dict[str, Any]) -> PolicyViolation:
        """Record a policy violation"""
        violation = PolicyViolation(
            violation_id=CryptographicUtils.generate_secure_token(16),
            violation_type=violation_type,
            timestamp=datetime.now(timezone.utc),
            session_id=session_id,
            user_action=user_action,
            policy_rule=policy_rule,
            enforcement_level=enforcement_level,
            details=details
        )
        
        with self._lock:
            self.violations.append(violation)
            
            # Trim old violations
            if len(self.violations) > 1000:
                self.violations = self.violations[-1000:]
        
        # Check violation threshold
        session_violations = [v for v in self.violations if v.session_id == session_id and not v.resolved]
        if len(session_violations) >= self.violation_threshold:
            logger.warning(f"Session {session_id} exceeded violation threshold")
            violation.enforcement_level = PolicyEnforcementLevel.TERMINATE
        
        # Notify callbacks
        for callback in self.violation_callbacks:
            try:
                callback(violation)
            except Exception as e:
                logger.error(f"Violation callback failed: {e}")
        
        logger.warning(f"Policy violation recorded: {violation_type.value} for session {session_id}")
        return violation
    
    def get_violations(self, session_id: Optional[str] = None) -> List[PolicyViolation]:
        """Get policy violations, optionally filtered by session"""
        with self._lock:
            if session_id:
                return [v for v in self.violations if v.session_id == session_id]
            return self.violations.copy()
    
    def resolve_violation(self, violation_id: str) -> bool:
        """Mark a violation as resolved"""
        with self._lock:
            for violation in self.violations:
                if violation.violation_id == violation_id:
                    violation.resolved = True
                    logger.info(f"Resolved violation: {violation_id}")
                    return True
        return False
    
    def get_active_policies(self) -> List[SessionPolicy]:
        """Get list of active policies"""
        with self._lock:
            return list(self.active_policies.values())
    
    def clear_violations(self, session_id: Optional[str] = None) -> None:
        """Clear violations, optionally for specific session"""
        with self._lock:
            if session_id:
                self.violations = [v for v in self.violations if v.session_id != session_id]
            else:
                self.violations.clear()
        
        logger.info(f"Cleared violations for session: {session_id or 'all'}")


class PolicyController:
    """Main policy controller for GUI applications"""
    
    def __init__(self, parent_frame: tk.Widget):
        self.parent_frame = parent_frame
        self.enforcer = PolicyEnforcer()
        self.config_manager = get_config_manager()
        
        # Setup callbacks
        self.enforcer.add_violation_callback(self._on_violation)
        self.enforcer.add_policy_callback(self._on_policy_loaded)
        
        # Policy management state
        self.policy_presets: Dict[str, Dict[str, Any]] = {}
        self.current_session_id: Optional[str] = None
        
        # Load saved policies
        self._load_policy_presets()
        
        logger.info("Policy controller initialized")
    
    def _load_policy_presets(self) -> None:
        """Load policy presets from configuration"""
        try:
            presets_data = self.config_manager.load_config(
                "policy_presets", 
                default_data={"presets": {}}
            )
            self.policy_presets = presets_data.get("presets", {})
            logger.debug(f"Loaded {len(self.policy_presets)} policy presets")
        except Exception as e:
            logger.error(f"Failed to load policy presets: {e}")
    
    def _save_policy_presets(self) -> None:
        """Save policy presets to configuration"""
        try:
            presets_data = {"presets": self.policy_presets}
            self.config_manager.save_config("policy_presets", presets_data)
            logger.debug("Saved policy presets")
        except Exception as e:
            logger.error(f"Failed to save policy presets: {e}")
    
    def _on_violation(self, violation: PolicyViolation) -> None:
        """Handle policy violation"""
        logger.warning(f"Policy violation: {violation.violation_type.value} - {violation.user_action}")
        
        # Show violation notification
        self._show_violation_notification(violation)
        
        # Auto-resolve if enabled
        if self.enforcer.auto_resolve_violations:
            if violation.enforcement_level == PolicyEnforcementLevel.WARNING:
                time.sleep(1)  # Brief delay for user to see notification
                self.enforcer.resolve_violation(violation.violation_id)
    
    def _on_policy_loaded(self, policy: SessionPolicy) -> None:
        """Handle policy loaded event"""
        logger.info(f"Policy loaded: {policy.policy_name}")
    
    def _show_violation_notification(self, violation: PolicyViolation) -> None:
        """Show policy violation notification"""
        try:
            # Create notification window
            notification = tk.Toplevel(self.parent_frame)
            notification.title("Policy Violation")
            notification.geometry("400x200")
            notification.resizable(False, False)
            
            # Make it modal
            notification.transient(self.parent_frame)
            notification.grab_set()
            
            # Notification content
            frame = ttk.Frame(notification)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Icon and title
            title_frame = ttk.Frame(frame)
            title_frame.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(title_frame, text="⚠️ Policy Violation", font=('Arial', 12, 'bold')).pack()
            
            # Details
            details_frame = ttk.Frame(frame)
            details_frame.pack(fill=tk.BOTH, expand=True)
            
            details_text = f"""Violation Type: {violation.violation_type.value.replace('_', ' ').title()}
Action: {violation.user_action}
Policy Rule: {violation.policy_rule}
Enforcement: {violation.enforcement_level.value.title()}
Time: {violation.timestamp.strftime('%H:%M:%S')}"""
            
            ttk.Label(details_frame, text=details_text, justify=tk.LEFT).pack(anchor=tk.W)
            
            # Buttons
            button_frame = ttk.Frame(frame)
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            if violation.enforcement_level == PolicyEnforcementLevel.WARNING:
                ttk.Button(button_frame, text="Acknowledge", 
                          command=notification.destroy).pack(side=tk.RIGHT)
            else:
                ttk.Button(button_frame, text="Close", 
                          command=notification.destroy).pack(side=tk.RIGHT)
            
            # Auto-close after 5 seconds for warnings
            if violation.enforcement_level == PolicyEnforcementLevel.WARNING:
                notification.after(5000, notification.destroy)
                
        except Exception as e:
            logger.error(f"Failed to show violation notification: {e}")
    
    def load_session_policy(self, session_id: str, policy_data: Dict[str, Any]) -> bool:
        """Load policy for a specific session"""
        self.current_session_id = session_id
        success = self.enforcer.load_policy(policy_data)
        
        if success:
            logger.info(f"Loaded policy for session: {session_id}")
        
        return success
    
    def validate_session_action(self, action_type: str, action_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate action for current session"""
        if not self.current_session_id:
            return True, None
        
        return self.enforcer.validate_action(self.current_session_id, action_type, action_data)
    
    def get_session_violations(self, session_id: Optional[str] = None) -> List[PolicyViolation]:
        """Get violations for session"""
        target_session = session_id or self.current_session_id
        return self.enforcer.get_violations(target_session)
    
    def resolve_violation(self, violation_id: str) -> bool:
        """Resolve a policy violation"""
        return self.enforcer.resolve_violation(violation_id)
    
    def clear_session_violations(self, session_id: Optional[str] = None) -> None:
        """Clear violations for session"""
        target_session = session_id or self.current_session_id
        self.enforcer.clear_violations(target_session)
    
    def get_active_policies(self) -> List[SessionPolicy]:
        """Get active policies"""
        return self.enforcer.get_active_policies()
    
    def set_enforcement_level(self, enabled: bool) -> None:
        """Enable or disable policy enforcement"""
        self.enforcer.enforcement_enabled = enabled
        logger.info(f"Policy enforcement {'enabled' if enabled else 'disabled'}")
    
    def set_auto_resolve(self, enabled: bool) -> None:
        """Enable or disable automatic violation resolution"""
        self.enforcer.auto_resolve_violations = enabled
        logger.info(f"Auto-resolve violations {'enabled' if enabled else 'disabled'}")
    
    def set_violation_threshold(self, threshold: int) -> None:
        """Set violation threshold for session termination"""
        self.enforcer.violation_threshold = threshold
        logger.info(f"Violation threshold set to: {threshold}")
    
    def create_policy_preset(self, name: str, policy_data: Dict[str, Any]) -> bool:
        """Create a new policy preset"""
        try:
            self.policy_presets[name] = policy_data
            self._save_policy_presets()
            logger.info(f"Created policy preset: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create policy preset: {e}")
            return False
    
    def get_policy_presets(self) -> Dict[str, Dict[str, Any]]:
        """Get available policy presets"""
        return self.policy_presets.copy()
    
    def delete_policy_preset(self, name: str) -> bool:
        """Delete a policy preset"""
        try:
            if name in self.policy_presets:
                del self.policy_presets[name]
                self._save_policy_presets()
                logger.info(f"Deleted policy preset: {name}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete policy preset: {e}")
        return False
    
    def cleanup(self) -> None:
        """Cleanup policy controller"""
        with self.enforcer._lock:
            self.enforcer.active_policies.clear()
            self.enforcer.violations.clear()
        
        logger.info("Policy controller cleaned up")


# Global policy controller instance
_policy_controller: Optional[PolicyController] = None


def get_policy_controller(parent_frame: Optional[tk.Widget] = None) -> PolicyController:
    """Get global policy controller instance"""
    global _policy_controller
    
    if _policy_controller is None and parent_frame is not None:
        _policy_controller = PolicyController(parent_frame)
    
    return _policy_controller


def cleanup_policy_controller() -> None:
    """Cleanup global policy controller"""
    global _policy_controller
    
    if _policy_controller:
        _policy_controller.cleanup()
        _policy_controller = None
