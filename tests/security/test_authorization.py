"""
Authorization Security Tests

Tests RBAC (Role-Based Access Control) authorization,
permission enforcement, and privilege escalation protection.

Author: Lucid Development Team
Version: 1.0.0
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from auth.permissions import PermissionManager, RoleManager
from auth.models.user import User, UserRole
from auth.models.permissions import Permission, Role
from admin.rbac.manager import RBACManager
from admin.rbac.roles import RoleDefinitions


class TestAuthorizationSecurity:
    """Test authorization and RBAC security mechanisms."""

    def setup_method(self):
        """Setup test fixtures."""
        self.permission_manager = PermissionManager()
        self.role_manager = RoleManager()
        self.rbac_manager = RBACManager()
        
        # Test users with different roles
        self.admin_user = User(
            id="admin-123",
            username="admin",
            email="admin@lucid.com",
            role=UserRole.ADMIN,
            is_active=True
        )
        
        self.node_operator = User(
            id="node-456",
            username="nodeop",
            email="nodeop@lucid.com",
            role=UserRole.NODE_OPERATOR,
            is_active=True
        )
        
        self.regular_user = User(
            id="user-789",
            username="user",
            email="user@lucid.com",
            role=UserRole.USER,
            is_active=True
        )

    def test_role_based_access_control(self):
        """Test RBAC permission enforcement."""
        # Test admin permissions
        assert self.rbac_manager.has_permission(
            user=self.admin_user,
            permission="system:admin:full_access"
        )
        
        # Test node operator permissions
        assert self.rbac_manager.has_permission(
            user=self.node_operator,
            permission="node:management:create"
        )
        
        # Test regular user permissions
        assert self.rbac_manager.has_permission(
            user=self.regular_user,
            permission="session:create"
        )

    def test_permission_denial_for_unauthorized_roles(self):
        """Test permission denial for unauthorized roles."""
        # Regular user should not have admin permissions
        assert not self.rbac_manager.has_permission(
            user=self.regular_user,
            permission="system:admin:full_access"
        )
        
        # Regular user should not have node management permissions
        assert not self.rbac_manager.has_permission(
            user=self.regular_user,
            permission="node:management:create"
        )
        
        # Node operator should not have admin permissions
        assert not self.rbac_manager.has_permission(
            user=self.node_operator,
            permission="system:admin:full_access"
        )

    def test_privilege_escalation_protection(self):
        """Test protection against privilege escalation attempts."""
        # Test role modification attempt
        with pytest.raises(HTTPException) as exc_info:
            self.rbac_manager.modify_user_role(
                current_user=self.regular_user,
                target_user_id=self.regular_user.id,
                new_role=UserRole.ADMIN
            )
        assert exc_info.value.status_code == 403

    def test_resource_access_authorization(self):
        """Test resource-level access authorization."""
        # Test session access
        assert self.rbac_manager.can_access_resource(
            user=self.regular_user,
            resource_type="session",
            resource_id="user-session-123",
            action="read"
        )
        
        # Test cross-user session access denial
        assert not self.rbac_manager.can_access_resource(
            user=self.regular_user,
            resource_type="session",
            resource_id="other-user-session-456",
            action="read"
        )

    def test_admin_override_permissions(self):
        """Test admin override permissions."""
        # Admin should be able to access any resource
        assert self.rbac_manager.can_access_resource(
            user=self.admin_user,
            resource_type="session",
            resource_id="any-session-123",
            action="read"
        )
        
        assert self.rbac_manager.can_access_resource(
            user=self.admin_user,
            resource_type="user",
            resource_id="any-user-456",
            action="modify"
        )

    def test_node_operator_permissions(self):
        """Test node operator specific permissions."""
        # Node operator should manage nodes
        assert self.rbac_manager.has_permission(
            user=self.node_operator,
            permission="node:management:create"
        )
        
        assert self.rbac_manager.has_permission(
            user=self.node_operator,
            permission="node:management:update"
        )
        
        # Node operator should not have admin permissions
        assert not self.rbac_manager.has_permission(
            user=self.node_operator,
            permission="system:admin:full_access"
        )

    def test_permission_inheritance(self):
        """Test permission inheritance in role hierarchy."""
        # Super admin should inherit all permissions
        super_admin = User(
            id="super-admin-123",
            username="superadmin",
            email="superadmin@lucid.com",
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        
        # Super admin should have all permissions
        all_permissions = [
            "system:admin:full_access",
            "node:management:create",
            "session:create",
            "user:management:create"
        ]
        
        for permission in all_permissions:
            assert self.rbac_manager.has_permission(
                user=super_admin,
                permission=permission
            )

    def test_session_based_authorization(self):
        """Test session-based authorization."""
        # Create session for user
        session = self.rbac_manager.create_user_session(
            user=self.regular_user,
            ip_address="192.168.1.100"
        )
        
        # Test session authorization
        assert self.rbac_manager.validate_session_authorization(
            session_id=session.id,
            required_permission="session:create"
        )

    def test_api_endpoint_authorization(self):
        """Test API endpoint authorization."""
        # Test admin endpoint access
        assert self.rbac_manager.can_access_endpoint(
            user=self.admin_user,
            endpoint="/admin/dashboard",
            method="GET"
        )
        
        # Test regular user admin endpoint denial
        assert not self.rbac_manager.can_access_endpoint(
            user=self.regular_user,
            endpoint="/admin/dashboard",
            method="GET"
        )

    def test_emergency_controls_authorization(self):
        """Test emergency controls authorization."""
        # Only super admin should have emergency controls
        super_admin = User(
            id="super-admin-123",
            username="superadmin",
            email="superadmin@lucid.com",
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        
        assert self.rbac_manager.has_permission(
            user=super_admin,
            permission="system:emergency:lockdown"
        )
        
        # Regular admin should not have emergency controls
        assert not self.rbac_manager.has_permission(
            user=self.admin_user,
            permission="system:emergency:lockdown"
        )

    def test_audit_trail_authorization(self):
        """Test audit trail access authorization."""
        # Admin should access audit logs
        assert self.rbac_manager.has_permission(
            user=self.admin_user,
            permission="audit:logs:read"
        )
        
        # Regular user should not access audit logs
        assert not self.rbac_manager.has_permission(
            user=self.regular_user,
            permission="audit:logs:read"
        )

    def test_permission_validation_security(self):
        """Test permission validation security."""
        # Test invalid permission format
        with pytest.raises(ValueError):
            self.rbac_manager.has_permission(
                user=self.regular_user,
                permission="invalid:permission:format"
            )
        
        # Test empty permission
        with pytest.raises(ValueError):
            self.rbac_manager.has_permission(
                user=self.regular_user,
                permission=""
            )

    def test_role_escalation_attempts(self):
        """Test protection against role escalation attempts."""
        # Test self-promotion attempt
        with pytest.raises(HTTPException) as exc_info:
            self.rbac_manager.update_user_role(
                current_user=self.regular_user,
                target_user_id=self.regular_user.id,
                new_role=UserRole.ADMIN
            )
        assert exc_info.value.status_code == 403

    def test_permission_caching_security(self):
        """Test permission caching security."""
        # Test permission cache invalidation
        self.rbac_manager.cache_user_permissions(self.regular_user)
        
        # Modify user role
        self.regular_user.role = UserRole.NODE_OPERATOR
        
        # Cache should be invalidated
        assert not self.rbac_manager.is_permission_cached(
            user=self.regular_user,
            permission="session:create"
        )

    def test_multi_tenant_authorization(self):
        """Test multi-tenant authorization isolation."""
        # Test tenant isolation
        tenant_a_user = User(
            id="tenant-a-user",
            username="tenant-a-user",
            email="user@tenant-a.com",
            role=UserRole.USER,
            tenant_id="tenant-a",
            is_active=True
        )
        
        tenant_b_user = User(
            id="tenant-b-user",
            username="tenant-b-user",
            email="user@tenant-b.com",
            role=UserRole.USER,
            tenant_id="tenant-b",
            is_active=True
        )
        
        # Users should not access each other's resources
        assert not self.rbac_manager.can_access_resource(
            user=tenant_a_user,
            resource_type="session",
            resource_id="tenant-b-session-123",
            action="read"
        )

    def test_authorization_bypass_attempts(self):
        """Test protection against authorization bypass attempts."""
        # Test direct database access attempt
        with pytest.raises(HTTPException) as exc_info:
            self.rbac_manager.bypass_authorization_check(
                user=self.regular_user,
                resource="admin:users"
            )
        assert exc_info.value.status_code == 403

    def test_permission_audit_logging(self):
        """Test permission access audit logging."""
        with patch('admin.audit.logger.AuditLogger') as mock_logger:
            # Perform authorized action
            self.rbac_manager.has_permission(
                user=self.regular_user,
                permission="session:create"
            )
            
            # Verify audit logging
            mock_logger.log_permission_check.assert_called()

    def test_authorization_timeout_security(self):
        """Test authorization timeout security."""
        # Test expired authorization
        with patch('time.time', return_value=time.time() + 3600):  # 1 hour later
            with pytest.raises(HTTPException) as exc_info:
                self.rbac_manager.validate_authorization_timeout(
                    user=self.regular_user,
                    permission="session:create"
                )
            assert exc_info.value.status_code == 401
