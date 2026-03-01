# LUCID RDP Access Controller Tests
# Comprehensive test suite for access control system

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from access_controller import (
    AccessController,
    AccessLevel,
    ResourceType,
    PermissionType,
    SecurityPolicy,
    AccessRule,
    AccessRequest,
    AccessDecision,
    SecurityContext,
    SessionAccess
)


class TestAccessController:
    """Test suite for AccessController"""
    
    @pytest.fixture
    async def access_controller(self):
        """Create access controller for testing"""
        mock_db = AsyncMock()
        controller = AccessController(mock_db)
        await controller.start()
        return controller
    
    @pytest.fixture
    def sample_access_rule(self):
        """Sample access rule for testing"""
        return AccessRule(
            rule_id="test_rule_001",
            name="Test Recording Access",
            description="Allow recording for test users",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE,
            access_level=AccessLevel.STANDARD,
            conditions={"user_id": ["test_user_001"]},
            created_by="test_system"
        )
    
    @pytest.fixture
    def sample_security_context(self):
        """Sample security context for testing"""
        return SecurityContext(
            user_id="test_user_001",
            session_id="test_session_001",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0",
            trust_score=75.0,
            security_policy=SecurityPolicy.TRUST_NOTHING
        )
    
    async def test_create_access_rule(self, access_controller):
        """Test creating access rules"""
        rule_id = await access_controller.create_access_rule(
            name="Test Rule",
            description="Test rule description",
            resource_type=ResourceType.SESSION,
            permission_type=PermissionType.CREATE,
            access_level=AccessLevel.STANDARD,
            created_by="test_user"
        )
        
        assert rule_id is not None
        assert rule_id in access_controller.access_rules
        
        rule = access_controller.access_rules[rule_id]
        assert rule.name == "Test Rule"
        assert rule.resource_type == ResourceType.SESSION
        assert rule.permission_type == PermissionType.CREATE
        assert rule.access_level == AccessLevel.STANDARD
    
    async def test_grant_session_access(self, access_controller):
        """Test granting session access"""
        permissions = {
            (ResourceType.SESSION, PermissionType.CREATE),
            (ResourceType.RECORDING, PermissionType.READ)
        }
        
        result = await access_controller.grant_session_access(
            session_id="test_session_001",
            user_id="test_user_001",
            permissions=permissions,
            access_level=AccessLevel.STANDARD
        )
        
        assert result is True
        
        key = "test_session_001_test_user_001"
        assert key in access_controller.active_sessions
        
        session_access = access_controller.active_sessions[key]
        assert session_access.session_id == "test_session_001"
        assert session_access.user_id == "test_user_001"
        assert session_access.access_level == AccessLevel.STANDARD
        assert len(session_access.permissions) == 2
    
    async def test_revoke_session_access(self, access_controller):
        """Test revoking session access"""
        # First grant access
        permissions = {(ResourceType.SESSION, PermissionType.CREATE)}
        await access_controller.grant_session_access(
            session_id="test_session_001",
            user_id="test_user_001",
            permissions=permissions
        )
        
        # Then revoke access
        result = await access_controller.revoke_session_access(
            session_id="test_session_001",
            user_id="test_user_001"
        )
        
        assert result is True
        
        key = "test_session_001_test_user_001"
        assert key not in access_controller.active_sessions
    
    async def test_check_permission(self, access_controller):
        """Test checking permissions"""
        # Grant specific permissions
        permissions = {
            (ResourceType.SESSION, PermissionType.CREATE),
            (ResourceType.CLIPBOARD, PermissionType.READ)
        }
        
        await access_controller.grant_session_access(
            session_id="test_session_001",
            user_id="test_user_001",
            permissions=permissions
        )
        
        # Check existing permission
        has_permission = await access_controller.check_permission(
            user_id="test_user_001",
            session_id="test_session_001",
            resource_type=ResourceType.SESSION,
            permission_type=PermissionType.CREATE
        )
        assert has_permission is True
        
        # Check non-existing permission
        has_permission = await access_controller.check_permission(
            user_id="test_user_001",
            session_id="test_session_001",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE
        )
        assert has_permission is False
    
    async def test_evaluate_access_allow(self, access_controller):
        """Test access evaluation with allow decision"""
        # Grant session access
        permissions = {(ResourceType.RECORDING, PermissionType.CREATE)}
        await access_controller.grant_session_access(
            session_id="test_session_001",
            user_id="test_user_001",
            permissions=permissions,
            access_level=AccessLevel.STANDARD
        )
        
        # Evaluate access
        decision = await access_controller.evaluate_access(
            user_id="test_user_001",
            session_id="test_session_001",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE,
            resource_id="recording_001"
        )
        
        assert decision.decision == "allow"
        assert decision.access_level == AccessLevel.STANDARD
        assert "session_permission_match" in decision.conditions
    
    async def test_evaluate_access_deny(self, access_controller):
        """Test access evaluation with deny decision"""
        # Evaluate access without granting permissions
        decision = await access_controller.evaluate_access(
            user_id="test_user_001",
            session_id="test_session_001",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE,
            resource_id="recording_001"
        )
        
        assert decision.decision == "deny"
        assert decision.access_level == AccessLevel.DENIED
    
    async def test_get_user_permissions(self, access_controller):
        """Test getting user permissions"""
        # Grant permissions
        permissions = {
            (ResourceType.SESSION, PermissionType.CREATE),
            (ResourceType.CLIPBOARD, PermissionType.READ)
        }
        
        await access_controller.grant_session_access(
            session_id="test_session_001",
            user_id="test_user_001",
            permissions=permissions,
            access_level=AccessLevel.STANDARD
        )
        
        # Get user permissions
        user_permissions = await access_controller.get_user_permissions(
            user_id="test_user_001",
            session_id="test_session_001"
        )
        
        assert user_permissions["access_level"] == "standard"
        assert len(user_permissions["permissions"]) == 2
        assert ("session", "create") in user_permissions["permissions"]
        assert ("clipboard", "read") in user_permissions["permissions"]
    
    async def test_expired_session_cleanup(self, access_controller):
        """Test cleanup of expired sessions"""
        # Create session with short expiration
        permissions = {(ResourceType.SESSION, PermissionType.CREATE)}
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=1)
        
        await access_controller.grant_session_access(
            session_id="test_session_001",
            user_id="test_user_001",
            permissions=permissions,
            expires_at=expires_at
        )
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Run cleanup
        await access_controller._cleanup_expired_sessions()
        
        # Check that session was removed
        key = "test_session_001_test_user_001"
        assert key not in access_controller.active_sessions
    
    async def test_rule_condition_evaluation(self, access_controller):
        """Test rule condition evaluation"""
        # Create rule with conditions
        rule = AccessRule(
            rule_id="test_rule_001",
            name="Conditional Rule",
            description="Rule with conditions",
            resource_type=ResourceType.SESSION,
            permission_type=PermissionType.CREATE,
            access_level=AccessLevel.STANDARD,
            conditions={
                "user_id": ["test_user_001"],
                "min_trust_score": 50.0
            }
        )
        
        access_controller.access_rules[rule.rule_id] = rule
        
        # Create access request
        access_request = AccessRequest(
            request_id="test_request_001",
            user_id="test_user_001",
            session_id="test_session_001",
            resource_type=ResourceType.SESSION,
            permission_type=PermissionType.CREATE,
            resource_id="session_001"
        )
        
        # Create security context with high trust score
        security_context = SecurityContext(
            user_id="test_user_001",
            session_id="test_session_001",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0",
            trust_score=75.0
        )
        
        # Evaluate rule conditions
        result = access_controller._evaluate_rule_conditions(
            rule, access_request, security_context
        )
        
        assert result is True
    
    async def test_trust_nothing_policy(self, access_controller):
        """Test trust-nothing security policy"""
        # Create access request
        access_request = AccessRequest(
            request_id="test_request_001",
            user_id="test_user_001",
            session_id="test_session_001",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE,
            resource_id="recording_001"
        )
        
        # Create security context with trust-nothing policy
        security_context = SecurityContext(
            user_id="test_user_001",
            session_id="test_session_001",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0",
            security_policy=SecurityPolicy.TRUST_NOTHING
        )
        
        # Apply trust-nothing policy (should deny by default)
        decision = await access_controller._apply_trust_nothing_policy(
            access_request, security_context
        )
        
        assert decision.decision == "deny"
        assert decision.access_level == AccessLevel.DENIED
    
    async def test_security_context_management(self, access_controller):
        """Test security context management"""
        # Get security context
        context = await access_controller._get_security_context(
            user_id="test_user_001",
            session_id="test_session_001"
        )
        
        assert context.user_id == "test_user_001"
        assert context.session_id == "test_session_001"
        assert context.security_policy == SecurityPolicy.TRUST_NOTHING
        
        # Check that context is cached
        context_key = "test_user_001_test_session_001"
        assert context_key in access_controller.security_contexts


class TestAccessRule:
    """Test suite for AccessRule"""
    
    def test_access_rule_creation(self):
        """Test creating access rules"""
        rule = AccessRule(
            rule_id="test_rule_001",
            name="Test Rule",
            description="Test rule description",
            resource_type=ResourceType.SESSION,
            permission_type=PermissionType.CREATE,
            access_level=AccessLevel.STANDARD,
            conditions={"user_id": ["test_user_001"]},
            created_by="test_system"
        )
        
        assert rule.rule_id == "test_rule_001"
        assert rule.name == "Test Rule"
        assert rule.resource_type == ResourceType.SESSION
        assert rule.permission_type == PermissionType.CREATE
        assert rule.access_level == AccessLevel.STANDARD
        assert rule.is_active is True
    
    def test_access_rule_to_dict(self):
        """Test converting access rule to dictionary"""
        rule = AccessRule(
            rule_id="test_rule_001",
            name="Test Rule",
            description="Test rule description",
            resource_type=ResourceType.SESSION,
            permission_type=PermissionType.CREATE,
            access_level=AccessLevel.STANDARD
        )
        
        rule_dict = rule.to_dict()
        
        assert rule_dict["_id"] == "test_rule_001"
        assert rule_dict["name"] == "Test Rule"
        assert rule_dict["resource_type"] == "session"
        assert rule_dict["permission_type"] == "create"
        assert rule_dict["access_level"] == "standard"
        assert rule_dict["is_active"] is True


class TestAccessRequest:
    """Test suite for AccessRequest"""
    
    def test_access_request_creation(self):
        """Test creating access requests"""
        request = AccessRequest(
            request_id="test_request_001",
            user_id="test_user_001",
            session_id="test_session_001",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE,
            resource_id="recording_001",
            justification="Test recording access"
        )
        
        assert request.request_id == "test_request_001"
        assert request.user_id == "test_user_001"
        assert request.session_id == "test_session_001"
        assert request.resource_type == ResourceType.RECORDING
        assert request.permission_type == PermissionType.CREATE
        assert request.resource_id == "recording_001"
        assert request.justification == "Test recording access"
    
    def test_access_request_to_dict(self):
        """Test converting access request to dictionary"""
        request = AccessRequest(
            request_id="test_request_001",
            user_id="test_user_001",
            session_id="test_session_001",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE,
            resource_id="recording_001"
        )
        
        request_dict = request.to_dict()
        
        assert request_dict["_id"] == "test_request_001"
        assert request_dict["user_id"] == "test_user_001"
        assert request_dict["session_id"] == "test_session_001"
        assert request_dict["resource_type"] == "recording"
        assert request_dict["permission_type"] == "create"
        assert request_dict["resource_id"] == "recording_001"


class TestSecurityContext:
    """Test suite for SecurityContext"""
    
    def test_security_context_creation(self):
        """Test creating security contexts"""
        context = SecurityContext(
            user_id="test_user_001",
            session_id="test_session_001",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0",
            location="Test Location",
            device_fingerprint="test_fingerprint",
            trust_score=75.0,
            risk_indicators=["suspicious_activity"],
            security_policy=SecurityPolicy.TRUST_NOTHING
        )
        
        assert context.user_id == "test_user_001"
        assert context.session_id == "test_session_001"
        assert context.ip_address == "192.168.1.100"
        assert context.user_agent == "TestAgent/1.0"
        assert context.location == "Test Location"
        assert context.device_fingerprint == "test_fingerprint"
        assert context.trust_score == 75.0
        assert "suspicious_activity" in context.risk_indicators
        assert context.security_policy == SecurityPolicy.TRUST_NOTHING
    
    def test_security_context_to_dict(self):
        """Test converting security context to dictionary"""
        context = SecurityContext(
            user_id="test_user_001",
            session_id="test_session_001",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0",
            trust_score=75.0,
            security_policy=SecurityPolicy.TRUST_NOTHING
        )
        
        context_dict = context.to_dict()
        
        assert context_dict["user_id"] == "test_user_001"
        assert context_dict["session_id"] == "test_session_001"
        assert context_dict["ip_address"] == "192.168.1.100"
        assert context_dict["user_agent"] == "TestAgent/1.0"
        assert context_dict["trust_score"] == 75.0
        assert context_dict["security_policy"] == "trust_nothing"


class TestSessionAccess:
    """Test suite for SessionAccess"""
    
    def test_session_access_creation(self):
        """Test creating session access"""
        permissions = {
            (ResourceType.SESSION, PermissionType.CREATE),
            (ResourceType.RECORDING, PermissionType.READ)
        }
        
        session_access = SessionAccess(
            session_id="test_session_001",
            user_id="test_user_001",
            permissions=permissions,
            access_level=AccessLevel.STANDARD,
            restrictions={"max_duration": 3600}
        )
        
        assert session_access.session_id == "test_session_001"
        assert session_access.user_id == "test_user_001"
        assert len(session_access.permissions) == 2
        assert session_access.access_level == AccessLevel.STANDARD
        assert session_access.restrictions["max_duration"] == 3600
    
    def test_session_access_to_dict(self):
        """Test converting session access to dictionary"""
        permissions = {
            (ResourceType.SESSION, PermissionType.CREATE),
            (ResourceType.RECORDING, PermissionType.READ)
        }
        
        session_access = SessionAccess(
            session_id="test_session_001",
            user_id="test_user_001",
            permissions=permissions,
            access_level=AccessLevel.STANDARD
        )
        
        session_dict = session_access.to_dict()
        
        assert session_dict["_id"] == "test_session_001_test_user_001"
        assert session_dict["session_id"] == "test_session_001"
        assert session_dict["user_id"] == "test_user_001"
        assert len(session_dict["permissions"]) == 2
        assert ("session", "create") in session_dict["permissions"]
        assert ("recording", "read") in session_dict["permissions"]
        assert session_dict["access_level"] == "standard"


# Integration tests
class TestAccessControllerIntegration:
    """Integration tests for AccessController"""
    
    async def test_full_access_workflow(self):
        """Test complete access control workflow"""
        # Create access controller
        mock_db = AsyncMock()
        controller = AccessController(mock_db)
        await controller.start()
        
        try:
            # 1. Create access rule
            rule_id = await controller.create_access_rule(
                name="Recording Access Rule",
                description="Allow recording for standard users",
                resource_type=ResourceType.RECORDING,
                permission_type=PermissionType.CREATE,
                access_level=AccessLevel.STANDARD,
                conditions={"user_id": ["test_user_001"]},
                created_by="admin"
            )
            
            assert rule_id is not None
            
            # 2. Grant session access
            permissions = {
                (ResourceType.SESSION, PermissionType.CREATE),
                (ResourceType.RECORDING, PermissionType.CREATE),
                (ResourceType.CLIPBOARD, PermissionType.READ)
            }
            
            result = await controller.grant_session_access(
                session_id="test_session_001",
                user_id="test_user_001",
                permissions=permissions,
                access_level=AccessLevel.STANDARD
            )
            
            assert result is True
            
            # 3. Check permissions
            has_recording_permission = await controller.check_permission(
                user_id="test_user_001",
                session_id="test_session_001",
                resource_type=ResourceType.RECORDING,
                permission_type=PermissionType.CREATE
            )
            
            assert has_recording_permission is True
            
            # 4. Evaluate access
            decision = await controller.evaluate_access(
                user_id="test_user_001",
                session_id="test_session_001",
                resource_type=ResourceType.RECORDING,
                permission_type=PermissionType.CREATE,
                resource_id="recording_001"
            )
            
            assert decision.decision == "allow"
            assert decision.access_level == AccessLevel.STANDARD
            
            # 5. Get user permissions
            user_permissions = await controller.get_user_permissions(
                user_id="test_user_001",
                session_id="test_session_001"
            )
            
            assert user_permissions["access_level"] == "standard"
            assert len(user_permissions["permissions"]) == 3
            
            # 6. Revoke access
            revoke_result = await controller.revoke_session_access(
                session_id="test_session_001",
                user_id="test_user_001"
            )
            
            assert revoke_result is True
            
            # 7. Verify access is revoked
            has_permission_after_revoke = await controller.check_permission(
                user_id="test_user_001",
                session_id="test_session_001",
                resource_type=ResourceType.RECORDING,
                permission_type=PermissionType.CREATE
            )
            
            assert has_permission_after_revoke is False
            
        finally:
            await controller.stop()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
