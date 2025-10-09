#!/usr/bin/env python3
"""
LUCID RDP Access Controller - Example Usage
Demonstrates how to use the access control system for RDP sessions
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from access_controller import (
    AccessController,
    AccessLevel,
    ResourceType,
    PermissionType,
    SecurityPolicy,
    create_access_controller
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_basic_usage():
    """Example of basic access controller usage"""
    print("=== LUCID RDP Access Controller - Basic Usage Example ===\n")
    
    # Create access controller (without database for demo)
    controller = create_access_controller()
    await controller.start()
    
    try:
        # 1. Create access rules
        print("1. Creating access rules...")
        
        # Rule for session creation
        session_rule_id = await controller.create_access_rule(
            name="Session Creation Rule",
            description="Allow standard users to create RDP sessions",
            resource_type=ResourceType.SESSION,
            permission_type=PermissionType.CREATE,
            access_level=AccessLevel.STANDARD,
            conditions={"user_id": ["user_001", "user_002"]},
            created_by="admin"
        )
        print(f"   Created session rule: {session_rule_id}")
        
        # Rule for recording access
        recording_rule_id = await controller.create_access_rule(
            name="Recording Access Rule",
            description="Allow recording for trusted users",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE,
            access_level=AccessLevel.STANDARD,
            conditions={"min_trust_score": 60.0},
            created_by="admin"
        )
        print(f"   Created recording rule: {recording_rule_id}")
        
        # 2. Grant session access
        print("\n2. Granting session access...")
        
        # Grant permissions for user_001
        user_001_permissions = {
            (ResourceType.SESSION, PermissionType.CREATE),
            (ResourceType.RECORDING, PermissionType.CREATE),
            (ResourceType.CLIPBOARD, PermissionType.READ),
            (ResourceType.FILE_TRANSFER, PermissionType.READ)
        }
        
        await controller.grant_session_access(
            session_id="session_001",
            user_id="user_001",
            permissions=user_001_permissions,
            access_level=AccessLevel.STANDARD,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2)
        )
        print("   Granted permissions for user_001")
        
        # Grant limited permissions for user_002
        user_002_permissions = {
            (ResourceType.SESSION, PermissionType.CREATE),
            (ResourceType.CLIPBOARD, PermissionType.READ)
        }
        
        await controller.grant_session_access(
            session_id="session_002",
            user_id="user_002",
            permissions=user_002_permissions,
            access_level=AccessLevel.LIMITED,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        print("   Granted limited permissions for user_002")
        
        # 3. Check permissions
        print("\n3. Checking permissions...")
        
        # Check if user_001 can create recordings
        can_record = await controller.check_permission(
            user_id="user_001",
            session_id="session_001",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE
        )
        print(f"   user_001 can create recordings: {can_record}")
        
        # Check if user_002 can create recordings (should be False)
        can_record_002 = await controller.check_permission(
            user_id="user_002",
            session_id="session_002",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE
        )
        print(f"   user_002 can create recordings: {can_record_002}")
        
        # 4. Evaluate access requests
        print("\n4. Evaluating access requests...")
        
        # Evaluate recording access for user_001
        recording_decision = await controller.evaluate_access(
            user_id="user_001",
            session_id="session_001",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE,
            resource_id="recording_001",
            context={"ip_address": "192.168.1.100", "user_agent": "RDPClient/1.0"}
        )
        print(f"   Recording access for user_001: {recording_decision.decision}")
        print(f"   Access level: {recording_decision.access_level.value}")
        print(f"   Reasoning: {recording_decision.reasoning}")
        
        # Evaluate file transfer access for user_002
        file_transfer_decision = await controller.evaluate_access(
            user_id="user_002",
            session_id="session_002",
            resource_type=ResourceType.FILE_TRANSFER,
            permission_type=PermissionType.CREATE,
            resource_id="transfer_001"
        )
        print(f"   File transfer access for user_002: {file_transfer_decision.decision}")
        print(f"   Access level: {file_transfer_decision.access_level.value}")
        
        # 5. Get user permissions
        print("\n5. Getting user permissions...")
        
        user_001_permissions = await controller.get_user_permissions(
            user_id="user_001",
            session_id="session_001"
        )
        print(f"   user_001 permissions: {user_001_permissions}")
        
        user_002_permissions = await controller.get_user_permissions(
            user_id="user_002",
            session_id="session_002"
        )
        print(f"   user_002 permissions: {user_002_permissions}")
        
        # 6. Demonstrate trust-nothing policy
        print("\n6. Demonstrating trust-nothing policy...")
        
        # Try to access without proper permissions
        unauthorized_decision = await controller.evaluate_access(
            user_id="user_003",  # User not in system
            session_id="session_003",
            resource_type=ResourceType.ADMIN,
            permission_type=PermissionType.MANAGE,
            resource_id="admin_panel"
        )
        print(f"   Unauthorized admin access: {unauthorized_decision.decision}")
        print(f"   Access level: {unauthorized_decision.access_level.value}")
        
        # 7. Revoke access
        print("\n7. Revoking access...")
        
        revoke_result = await controller.revoke_session_access(
            session_id="session_001",
            user_id="user_001"
        )
        print(f"   Revoked access for user_001: {revoke_result}")
        
        # Check permissions after revocation
        can_record_after_revoke = await controller.check_permission(
            user_id="user_001",
            session_id="session_001",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE
        )
        print(f"   user_001 can create recordings after revocation: {can_record_after_revoke}")
        
        print("\n=== Example completed successfully! ===")
        
    except Exception as e:
        print(f"Error in example: {e}")
        logger.error(f"Example failed: {e}")
    
    finally:
        await controller.stop()


async def example_advanced_usage():
    """Example of advanced access controller features"""
    print("\n=== LUCID RDP Access Controller - Advanced Usage Example ===\n")
    
    controller = create_access_controller()
    await controller.start()
    
    try:
        # 1. Create complex access rules with conditions
        print("1. Creating complex access rules...")
        
        # Rule with time restrictions
        time_rule_id = await controller.create_access_rule(
            name="Business Hours Access",
            description="Allow admin access during business hours",
            resource_type=ResourceType.ADMIN,
            permission_type=PermissionType.MANAGE,
            access_level=AccessLevel.ADMIN,
            conditions={
                "time_restrictions": {
                    "allowed_hours": list(range(9, 17))  # 9 AM to 5 PM
                },
                "min_trust_score": 80.0
            },
            created_by="admin"
        )
        print(f"   Created time-restricted rule: {time_rule_id}")
        
        # Rule with trust score requirements
        trust_rule_id = await controller.create_access_rule(
            name="High Trust Recording",
            description="Allow recording for high-trust users",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE,
            access_level=AccessLevel.ELEVATED,
            conditions={
                "min_trust_score": 90.0,
                "user_id": ["trusted_user_001"]
            },
            created_by="admin"
        )
        print(f"   Created trust-based rule: {trust_rule_id}")
        
        # 2. Demonstrate security policy differences
        print("\n2. Demonstrating security policies...")
        
        # Create sessions with different security policies
        policies = [
            SecurityPolicy.TRUST_NOTHING,
            SecurityPolicy.ZERO_TRUST,
            SecurityPolicy.STRICT,
            SecurityPolicy.STANDARD,
            SecurityPolicy.PERMISSIVE
        ]
        
        for policy in policies:
            print(f"   Testing {policy.value} policy...")
            
            # Create session with specific policy
            session_id = f"session_{policy.value}"
            permissions = {(ResourceType.SESSION, PermissionType.CREATE)}
            
            await controller.grant_session_access(
                session_id=session_id,
                user_id="test_user",
                permissions=permissions,
                access_level=AccessLevel.STANDARD
            )
            
            # Evaluate access with policy
            decision = await controller.evaluate_access(
                user_id="test_user",
                session_id=session_id,
                resource_type=ResourceType.RECORDING,
                permission_type=PermissionType.CREATE,
                resource_id="recording_001"
            )
            
            print(f"     Decision: {decision.decision}, Level: {decision.access_level.value}")
        
        # 3. Demonstrate conditional access
        print("\n3. Demonstrating conditional access...")
        
        # Create rule that requires additional verification
        conditional_rule_id = await controller.create_access_rule(
            name="Conditional Access Rule",
            description="Requires additional verification",
            resource_type=ResourceType.WALLET,
            permission_type=PermissionType.MANAGE,
            access_level=AccessLevel.ELEVATED,
            conditions={"require_mfa": True},
            created_by="admin"
        )
        
        # Evaluate access that triggers conditional decision
        conditional_decision = await controller.evaluate_access(
            user_id="test_user",
            session_id="session_001",
            resource_type=ResourceType.WALLET,
            permission_type=PermissionType.MANAGE,
            resource_id="wallet_001"
        )
        
        print(f"   Conditional access decision: {conditional_decision.decision}")
        print(f"   Conditions: {conditional_decision.conditions}")
        print(f"   Reasoning: {conditional_decision.reasoning}")
        
        # 4. Demonstrate audit logging
        print("\n4. Demonstrating audit logging...")
        
        # Make several access requests to generate audit logs
        for i in range(3):
            decision = await controller.evaluate_access(
                user_id=f"user_{i:03d}",
                session_id=f"session_{i:03d}",
                resource_type=ResourceType.SESSION,
                permission_type=PermissionType.CREATE,
                resource_id=f"resource_{i:03d}"
            )
            print(f"   Request {i+1}: {decision.decision} - {decision.decided_at}")
        
        print("\n=== Advanced example completed successfully! ===")
        
    except Exception as e:
        print(f"Error in advanced example: {e}")
        logger.error(f"Advanced example failed: {e}")
    
    finally:
        await controller.stop()


async def main():
    """Run all examples"""
    print("LUCID RDP Access Controller - Usage Examples")
    print("=" * 50)
    
    # Run basic usage example
    await example_basic_usage()
    
    # Run advanced usage example
    await example_advanced_usage()
    
    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
