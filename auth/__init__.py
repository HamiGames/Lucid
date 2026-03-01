"""
Lucid Authentication Service
Cluster 09: Authentication
Port: 8089

Features:
- TRON signature verification
- Hardware wallet integration (Ledger, Trezor, KeepKey)
- JWT token management (15min access, 7day refresh)
- RBAC engine (4 roles: USER, NODE_OPERATOR, ADMIN, SUPER_ADMIN)
- Session management
- Rate limiting
- Audit logging
"""

__version__ = "1.0.0"
__cluster__ = "09-authentication"
__port__ = 8089

