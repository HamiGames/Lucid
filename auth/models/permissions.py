"""
Lucid Authentication Service - Permissions Model
RBAC Roles and Permissions
"""

from enum import Enum


class Role(str, Enum):
    """
    User roles in Lucid system
    
    Hierarchy:
    1. USER - Basic session operations
    2. NODE_OPERATOR - Node management, PoOT operations  
    3. ADMIN - System management, blockchain operations
    4. SUPER_ADMIN - Full system access, TRON payout management
    """
    USER = "USER"
    NODE_OPERATOR = "NODE_OPERATOR"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class Permission(str, Enum):
    """
    System permissions
    
    Organized by functional area:
    - Session Management
    - User Management
    - Node Operations
    - Blockchain Operations
    - Payment Operations
    - Administrative Operations
    """
    
    # Session Management Permissions
    CREATE_SESSION = "create_session"
    VIEW_OWN_SESSIONS = "view_own_sessions"
    VIEW_ALL_SESSIONS = "view_all_sessions"
    DELETE_OWN_SESSIONS = "delete_own_sessions"
    DELETE_ANY_SESSION = "delete_any_session"
    
    # User Management Permissions
    VIEW_OWN_PROFILE = "view_own_profile"
    UPDATE_OWN_PROFILE = "update_own_profile"
    VIEW_ALL_USERS = "view_all_users"
    MANAGE_USERS = "manage_users"
    ASSIGN_ROLES = "assign_roles"
    
    # Hardware Wallet Permissions
    CONNECT_HARDWARE_WALLET = "connect_hardware_wallet"
    SIGN_WITH_HARDWARE_WALLET = "sign_with_hardware_wallet"
    
    # Node Operations Permissions
    REGISTER_NODE = "register_node"
    MANAGE_OWN_NODES = "manage_own_nodes"
    VIEW_OWN_NODES = "view_own_nodes"
    VIEW_ALL_NODES = "view_all_nodes"
    MANAGE_ALL_NODES = "manage_all_nodes"
    
    # Pool Management Permissions
    VIEW_POOL_INFO = "view_pool_info"
    MANAGE_POOLS = "manage_pools"
    ASSIGN_NODES_TO_POOLS = "assign_nodes_to_pools"
    
    # PoOT (Proof of Observation Time) Permissions
    SUBMIT_POOT_VOTES = "submit_poot_votes"
    VIEW_POOT_SCORES = "view_poot_scores"
    VALIDATE_POOT_SCORES = "validate_poot_scores"
    
    # Blockchain Permissions
    VIEW_BLOCKCHAIN_INFO = "view_blockchain_info"
    SUBMIT_TRANSACTIONS = "submit_transactions"
    ANCHOR_SESSIONS = "anchor_sessions"
    VALIDATE_BLOCKS = "validate_blocks"
    
    # Trust Policy Permissions
    VIEW_TRUST_POLICIES = "view_trust_policies"
    MANAGE_TRUST_POLICIES = "manage_trust_policies"
    
    # Payout Permissions
    VIEW_OWN_PAYOUTS = "view_own_payouts"
    REQUEST_PAYOUT = "request_payout"
    VIEW_ALL_PAYOUTS = "view_all_payouts"
    MANAGE_PAYOUTS = "manage_payouts"
    APPROVE_PAYOUTS = "approve_payouts"
    
    # Administrative Permissions
    ACCESS_ADMIN_DASHBOARD = "access_admin_dashboard"
    VIEW_SYSTEM_METRICS = "view_system_metrics"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_SYSTEM_CONFIG = "manage_system_config"
    
    # Emergency Controls
    EMERGENCY_LOCKDOWN = "emergency_lockdown"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"
    FORCE_USER_LOGOUT = "force_user_logout"
    
    # API Access Permissions
    API_GATEWAY_ACCESS = "api_gateway_access"
    ADMIN_API_ACCESS = "admin_api_access"


# Permission descriptions for documentation
PERMISSION_DESCRIPTIONS = {
    Permission.CREATE_SESSION: "Create new RDP sessions",
    Permission.VIEW_OWN_SESSIONS: "View own sessions",
    Permission.VIEW_ALL_SESSIONS: "View all user sessions",
    Permission.DELETE_OWN_SESSIONS: "Delete own sessions",
    Permission.DELETE_ANY_SESSION: "Delete any user's session",
    
    Permission.VIEW_OWN_PROFILE: "View own user profile",
    Permission.UPDATE_OWN_PROFILE: "Update own user profile",
    Permission.VIEW_ALL_USERS: "View all user profiles",
    Permission.MANAGE_USERS: "Manage user accounts",
    Permission.ASSIGN_ROLES: "Assign roles to users",
    
    Permission.CONNECT_HARDWARE_WALLET: "Connect hardware wallet",
    Permission.SIGN_WITH_HARDWARE_WALLET: "Sign with hardware wallet",
    
    Permission.REGISTER_NODE: "Register worker node",
    Permission.MANAGE_OWN_NODES: "Manage own nodes",
    Permission.VIEW_OWN_NODES: "View own nodes",
    Permission.VIEW_ALL_NODES: "View all nodes",
    Permission.MANAGE_ALL_NODES: "Manage all nodes",
    
    Permission.VIEW_POOL_INFO: "View pool information",
    Permission.MANAGE_POOLS: "Manage node pools",
    Permission.ASSIGN_NODES_TO_POOLS: "Assign nodes to pools",
    
    Permission.SUBMIT_POOT_VOTES: "Submit PoOT consensus votes",
    Permission.VIEW_POOT_SCORES: "View PoOT scores",
    Permission.VALIDATE_POOT_SCORES: "Validate PoOT scores",
    
    Permission.VIEW_BLOCKCHAIN_INFO: "View blockchain information",
    Permission.SUBMIT_TRANSACTIONS: "Submit blockchain transactions",
    Permission.ANCHOR_SESSIONS: "Anchor sessions to blockchain",
    Permission.VALIDATE_BLOCKS: "Validate blockchain blocks",
    
    Permission.VIEW_TRUST_POLICIES: "View trust policies",
    Permission.MANAGE_TRUST_POLICIES: "Manage trust policies",
    
    Permission.VIEW_OWN_PAYOUTS: "View own payouts",
    Permission.REQUEST_PAYOUT: "Request payout",
    Permission.VIEW_ALL_PAYOUTS: "View all payouts",
    Permission.MANAGE_PAYOUTS: "Manage payouts",
    Permission.APPROVE_PAYOUTS: "Approve payout requests",
    
    Permission.ACCESS_ADMIN_DASHBOARD: "Access admin dashboard",
    Permission.VIEW_SYSTEM_METRICS: "View system metrics",
    Permission.VIEW_AUDIT_LOGS: "View audit logs",
    Permission.MANAGE_SYSTEM_CONFIG: "Manage system configuration",
    
    Permission.EMERGENCY_LOCKDOWN: "Trigger emergency lockdown",
    Permission.EMERGENCY_SHUTDOWN: "Trigger emergency shutdown",
    Permission.FORCE_USER_LOGOUT: "Force user logout",
    
    Permission.API_GATEWAY_ACCESS: "Access API Gateway",
    Permission.ADMIN_API_ACCESS: "Access Admin APIs"
}


# Role descriptions for documentation
ROLE_DESCRIPTIONS = {
    Role.USER: "Standard user with basic session access",
    Role.NODE_OPERATOR: "Worker node operator with node management and PoOT capabilities",
    Role.ADMIN: "System administrator with full management capabilities",
    Role.SUPER_ADMIN: "Super administrator with all system permissions including emergency controls"
}

