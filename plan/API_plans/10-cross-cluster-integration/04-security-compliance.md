# Cross-Cluster Integration Security & Compliance

## Overview

This document defines the comprehensive security and compliance requirements for the Cross-Cluster Integration cluster, including authentication, authorization, encryption, rate limiting, audit logging, and TRON isolation enforcement.

## Security Architecture

### Multi-Layer Security Model

```
┌─────────────────────────────────────────────────────────────────┐
│                      Security Layer 1: Network                  │
│  • Tor Integration (.onion endpoints)                          │
│  • Network Policies (Kubernetes)                               │
│  • Plane Isolation (ops/chain/wallet)                          │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Security Layer 2: Transport                    │
│  • mTLS (Mutual TLS)                                           │
│  • Certificate Management                                       │
│  • Encrypted Communication                                      │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Security Layer 3: Application                   │
│  • Service-to-Service Authentication (JWT)                     │
│  • Authorization (RBAC/ACL)                                    │
│  • Rate Limiting                                               │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Security Layer 4: Audit                      │
│  • Audit Logging                                               │
│  • Security Monitoring                                          │
│  • Compliance Reporting                                         │
└─────────────────────────────────────────────────────────────────┘
```

## mTLS Configuration

### 1. Certificate Authority Setup

```yaml
# Certificate Authority Configuration
CertificateAuthority:
  organization: "Lucid"
  commonName: "Lucid Root CA"
  validityPeriod: "10 years"
  keySize: 4096
  algorithm: "RSA"
  
  intermediateCAs:
    - name: "Lucid Service Mesh CA"
      commonName: "Lucid Service Mesh Intermediate CA"
      validityPeriod: "5 years"
      keySize: 4096
      
  certificateRotation:
    enabled: true
    rotationInterval: "90 days"
    renewalThreshold: "30 days"
    autoRotation: true
```

### 2. Service Certificate Management

```python
# lucid/service-mesh/security/cert_manager.py

import os
import logging
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class CertificateManager:
    """Manages SSL/TLS certificates for service mesh."""
    
    def __init__(
        self,
        ca_cert_path: str = "/etc/certs/ca.crt",
        ca_key_path: str = "/etc/certs/ca.key",
        cert_output_dir: str = "/etc/certs/services"
    ):
        self.ca_cert_path = ca_cert_path
        self.ca_key_path = ca_key_path
        self.cert_output_dir = cert_output_dir
        
        # Load CA certificate and key
        self.ca_cert = self._load_certificate(ca_cert_path)
        self.ca_key = self._load_private_key(ca_key_path)
    
    def generate_service_certificate(
        self,
        service_name: str,
        service_id: str,
        cluster: str,
        plane: str,
        validity_days: int = 90
    ) -> tuple:
        """
        Generate a certificate for a service.
        
        Args:
            service_name: Name of the service
            service_id: Unique service identifier
            cluster: Service cluster
            plane: Service plane (ops, chain, wallet)
            validity_days: Certificate validity period in days
            
        Returns:
            (cert_path, key_path): Paths to generated certificate and key
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Build subject name
        subject = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Lucid"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, f"plane-{plane}"),
            x509.NameAttribute(NameOID.COMMON_NAME, service_name),
        ])
        
        # Build certificate
        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(subject)
        cert_builder = cert_builder.issuer_name(self.ca_cert.subject)
        cert_builder = cert_builder.public_key(private_key.public_key())
        cert_builder = cert_builder.serial_number(x509.random_serial_number())
        cert_builder = cert_builder.not_valid_before(datetime.utcnow())
        cert_builder = cert_builder.not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        )
        
        # Add Subject Alternative Names (SANs)
        san_list = [
            x509.DNSName(f"{service_name}.lucid.internal"),
            x509.DNSName(f"{service_name}.lucid.onion"),
            x509.DNSName(f"{service_name}.{cluster}.lucid.internal"),
            x509.URIName(f"spiffe://lucid.onion/{plane}/{cluster}/{service_name}"),
        ]
        
        cert_builder = cert_builder.add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False
        )
        
        # Add Extended Key Usage
        cert_builder = cert_builder.add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True
        )
        
        # Add Key Usage
        cert_builder = cert_builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=False,
                content_commitment=False,
                data_encipherment=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True
        )
        
        # Sign certificate with CA
        certificate = cert_builder.sign(
            self.ca_key,
            hashes.SHA256(),
            backend=default_backend()
        )
        
        # Save certificate and key
        cert_path = os.path.join(
            self.cert_output_dir,
            f"{service_name}-{service_id[:8]}.crt"
        )
        key_path = os.path.join(
            self.cert_output_dir,
            f"{service_name}-{service_id[:8]}.key"
        )
        
        self._save_certificate(certificate, cert_path)
        self._save_private_key(private_key, key_path)
        
        logger.info(
            f"Generated certificate for {service_name} "
            f"(ID: {service_id}, Plane: {plane})"
        )
        
        return cert_path, key_path
    
    def verify_certificate(
        self,
        cert_path: str,
        expected_service: str,
        expected_plane: str
    ) -> bool:
        """
        Verify a service certificate.
        
        Args:
            cert_path: Path to certificate file
            expected_service: Expected service name
            expected_plane: Expected service plane
            
        Returns:
            valid: True if certificate is valid
        """
        try:
            cert = self._load_certificate(cert_path)
            
            # Check if signed by our CA
            # (Simplified check - production should use proper chain validation)
            if cert.issuer != self.ca_cert.subject:
                logger.error("Certificate not signed by Lucid CA")
                return False
            
            # Check validity period
            now = datetime.utcnow()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                logger.error("Certificate expired or not yet valid")
                return False
            
            # Check common name matches service
            cn = cert.subject.get_attributes_for_oid(
                NameOID.COMMON_NAME
            )[0].value
            if cn != expected_service:
                logger.error(f"Certificate CN mismatch: {cn} != {expected_service}")
                return False
            
            # Check organizational unit matches plane
            ou = cert.subject.get_attributes_for_oid(
                NameOID.ORGANIZATIONAL_UNIT_NAME
            )[0].value
            if ou != f"plane-{expected_plane}":
                logger.error(f"Certificate plane mismatch: {ou}")
                return False
            
            logger.info(f"Certificate verified for {expected_service}")
            return True
            
        except Exception as e:
            logger.error(f"Certificate verification failed: {str(e)}")
            return False
    
    def _load_certificate(self, path: str):
        """Load certificate from file."""
        with open(path, 'rb') as f:
            return x509.load_pem_x509_certificate(
                f.read(),
                default_backend()
            )
    
    def _load_private_key(self, path: str):
        """Load private key from file."""
        with open(path, 'rb') as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
    
    def _save_certificate(self, cert, path: str):
        """Save certificate to file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        os.chmod(path, 0o644)
    
    def _save_private_key(self, key, path: str):
        """Save private key to file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        os.chmod(path, 0o600)  # Restrict permissions
```

### 3. mTLS Verification in Beta Sidecar

```python
# lucid/service-mesh/security/mtls_manager.py

import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MTLSManager:
    """Manages mTLS verification in Beta sidecar."""
    
    def __init__(self, cert_manager: 'CertificateManager'):
        self.cert_manager = cert_manager
    
    def verify_client_certificate(
        self,
        client_cert_path: str,
        allowed_planes: list,
        allowed_clusters: list
    ) -> dict:
        """
        Verify client certificate and extract service identity.
        
        Args:
            client_cert_path: Path to client certificate
            allowed_planes: List of allowed planes
            allowed_clusters: List of allowed clusters
            
        Returns:
            identity: Service identity dict or None if invalid
            
        Raises:
            MTLSVerificationError: If verification fails (LUCID_ERR_1204)
        """
        try:
            cert = self.cert_manager._load_certificate(client_cert_path)
            
            # Extract service identity
            cn = cert.subject.get_attributes_for_oid(
                x509.oid.NameOID.COMMON_NAME
            )[0].value
            
            ou = cert.subject.get_attributes_for_oid(
                x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME
            )[0].value
            
            # Extract plane from OU
            if not ou.startswith("plane-"):
                raise MTLSVerificationError(
                    "LUCID_ERR_1204",
                    "Invalid certificate OU format"
                )
            
            plane = ou.replace("plane-", "")
            
            # Verify plane is allowed
            if plane not in allowed_planes:
                raise MTLSVerificationError(
                    "LUCID_ERR_1203",
                    f"Plane {plane} not allowed for this service"
                )
            
            # Extract cluster from SAN URI
            cluster = self._extract_cluster_from_san(cert)
            
            # Verify cluster is allowed
            if allowed_clusters and cluster not in allowed_clusters:
                raise MTLSVerificationError(
                    "LUCID_ERR_1203",
                    f"Cluster {cluster} not allowed for this service"
                )
            
            # Verify certificate is valid
            if not self.cert_manager.verify_certificate(
                client_cert_path,
                cn,
                plane
            ):
                raise MTLSVerificationError(
                    "LUCID_ERR_1204",
                    "Certificate verification failed"
                )
            
            identity = {
                "serviceName": cn,
                "plane": plane,
                "cluster": cluster,
                "verified": True
            }
            
            logger.info(
                f"Client certificate verified: {cn} "
                f"(plane: {plane}, cluster: {cluster})"
            )
            
            return identity
            
        except MTLSVerificationError:
            raise
        except Exception as e:
            logger.error(f"mTLS verification failed: {str(e)}")
            raise MTLSVerificationError("LUCID_ERR_1204", str(e))
    
    def _extract_cluster_from_san(self, cert) -> Optional[str]:
        """Extract cluster from certificate SAN URI."""
        try:
            san_ext = cert.extensions.get_extension_for_oid(
                x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            )
            
            for name in san_ext.value:
                if isinstance(name, x509.URIName):
                    # Parse SPIFFE URI: spiffe://lucid.onion/plane/cluster/service
                    uri = name.value
                    if uri.startswith("spiffe://lucid.onion/"):
                        parts = uri.replace("spiffe://lucid.onion/", "").split("/")
                        if len(parts) >= 3:
                            return parts[1]  # cluster
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract cluster from SAN: {str(e)}")
            return None


class MTLSVerificationError(Exception):
    """Exception raised when mTLS verification fails."""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")
```

## Service-to-Service Authentication

### 1. JWT Token Generation

```python
# lucid/service-mesh/security/auth_provider.py

import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ServiceAuthProvider:
    """Provides JWT-based service-to-service authentication."""
    
    def __init__(
        self,
        issuer: str = "lucid.onion",
        audience: str = "lucid-services",
        secret_key: str = "",
        algorithm: str = "RS256",
        private_key_path: str = "/etc/secrets/jwt-private.key",
        public_key_path: str = "/etc/secrets/jwt-public.key"
    ):
        self.issuer = issuer
        self.audience = audience
        self.algorithm = algorithm
        
        # Load keys for RS256
        if algorithm == "RS256":
            with open(private_key_path, 'r') as f:
                self.private_key = f.read()
            with open(public_key_path, 'r') as f:
                self.public_key = f.read()
        else:
            self.secret_key = secret_key
    
    def generate_service_token(
        self,
        service_name: str,
        service_id: str,
        cluster: str,
        plane: str,
        validity_hours: int = 24
    ) -> str:
        """
        Generate JWT token for service-to-service authentication.
        
        Args:
            service_name: Name of the service
            service_id: Unique service identifier
            cluster: Service cluster
            plane: Service plane
            validity_hours: Token validity period in hours
            
        Returns:
            token: JWT token string
        """
        now = datetime.utcnow()
        
        payload = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": service_id,
            "iat": now,
            "exp": now + timedelta(hours=validity_hours),
            "nbf": now,
            "jti": service_id,
            "service_name": service_name,
            "cluster": cluster,
            "plane": plane,
            "permissions": self._get_service_permissions(cluster, plane)
        }
        
        if self.algorithm == "RS256":
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm=self.algorithm
            )
        else:
            token = jwt.encode(
                payload,
                self.secret_key,
                algorithm=self.algorithm
            )
        
        logger.info(
            f"Generated JWT token for {service_name} "
            f"(plane: {plane}, valid: {validity_hours}h)"
        )
        
        return token
    
    def verify_service_token(
        self,
        token: str,
        required_plane: Optional[str] = None,
        required_cluster: Optional[str] = None
    ) -> Dict:
        """
        Verify JWT token and extract service identity.
        
        Args:
            token: JWT token string
            required_plane: Required plane (optional)
            required_cluster: Required cluster (optional)
            
        Returns:
            payload: Decoded token payload
            
        Raises:
            AuthenticationError: If verification fails
        """
        try:
            if self.algorithm == "RS256":
                payload = jwt.decode(
                    token,
                    self.public_key,
                    algorithms=[self.algorithm],
                    audience=self.audience,
                    issuer=self.issuer
                )
            else:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm],
                    audience=self.audience,
                    issuer=self.issuer
                )
            
            # Verify plane if required
            if required_plane and payload.get('plane') != required_plane:
                raise AuthenticationError(
                    "LUCID_ERR_1203",
                    f"Plane mismatch: expected {required_plane}, "
                    f"got {payload.get('plane')}"
                )
            
            # Verify cluster if required
            if required_cluster and payload.get('cluster') != required_cluster:
                raise AuthenticationError(
                    "LUCID_ERR_1203",
                    f"Cluster mismatch: expected {required_cluster}, "
                    f"got {payload.get('cluster')}"
                )
            
            logger.info(
                f"JWT token verified for {payload.get('service_name')}"
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError(
                "LUCID_ERR_1203",
                "Token expired"
            )
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(
                "LUCID_ERR_1203",
                f"Invalid token: {str(e)}"
            )
    
    def _get_service_permissions(self, cluster: str, plane: str) -> list:
        """Get default permissions for service based on cluster and plane."""
        permissions = []
        
        # Base permissions for all services
        permissions.append(f"service:read:{cluster}")
        
        # Plane-specific permissions
        if plane == "ops":
            permissions.extend([
                "service:read:chain",  # Can read from chain
                "service:write:ops"    # Can write to ops
            ])
        elif plane == "chain":
            permissions.extend([
                "service:write:chain",
                "service:read:storage"
            ])
        elif plane == "wallet":
            permissions.append("service:write:wallet")
        
        return permissions


class AuthenticationError(Exception):
    """Exception raised when authentication fails."""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")
```

## Plane Isolation & ACL Policies

### 1. Network Policies (Kubernetes)

```yaml
# deployments/kubernetes/network-policies.yaml

# Ops Plane Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ops-plane-isolation
  namespace: lucid-ops
spec:
  podSelector:
    matchLabels:
      plane: ops
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          plane: ops
    - podSelector:
        matchLabels:
          component: gateway
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          plane: ops
    - namespaceSelector:
        matchLabels:
          plane: chain
    ports:
    - protocol: TCP
      port: 8084  # Blockchain core (read-only)
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 53   # DNS
    - protocol: UDP
      port: 53

---
# Chain Plane Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: chain-plane-isolation
  namespace: lucid-chain
spec:
  podSelector:
    matchLabels:
      plane: chain
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          plane: chain
    - namespaceSelector:
        matchLabels:
          plane: ops
      podSelector:
        matchLabels:
          service: api-gateway
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          plane: chain
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53

---
# Wallet Plane Network Policy (TRON Isolation)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: wallet-plane-isolation
  namespace: lucid-wallet
spec:
  podSelector:
    matchLabels:
      plane: wallet
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          plane: wallet
    - namespaceSelector:
        matchLabels:
          plane: ops
      podSelector:
        matchLabels:
          service: api-gateway
    ports:
    - protocol: TCP
      port: 8087  # TRON payment service
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          plane: wallet
  - to:
    - podSelector: {}  # Allow external (TRON network)
    ports:
    - protocol: TCP
      port: 8090  # TRON full node
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

### 2. Beta Sidecar ACL Policies

```yaml
# config/sidecar-policies.yaml

# ACL Policies for Service Mesh
aclPolicies:
  # Ops Plane Policies
  - name: "ops-plane-default"
    plane: "ops"
    defaultAction: "deny"
    rules:
      # Ops services can communicate with each other
      - source:
          plane: "ops"
        destination:
          plane: "ops"
        action: "allow"
        methods: ["GET", "POST", "PUT", "DELETE"]
      
      # Ops can read from Chain
      - source:
          plane: "ops"
        destination:
          plane: "chain"
        action: "allow"
        methods: ["GET"]
        paths:
          - "/api/v1/blocks/*"
          - "/api/v1/sessions/*"
      
      # Ops can call Wallet for payments
      - source:
          plane: "ops"
          cluster: "api-gateway"
        destination:
          plane: "wallet"
          cluster: "tron-payment"
        action: "allow"
        methods: ["POST"]
        paths:
          - "/api/v1/payments/*"
  
  # Chain Plane Policies
  - name: "chain-plane-default"
    plane: "chain"
    defaultAction: "deny"
    rules:
      # Chain services can communicate with each other
      - source:
          plane: "chain"
        destination:
          plane: "chain"
        action: "allow"
        methods: ["GET", "POST", "PUT", "DELETE"]
      
      # Chain cannot access Ops
      - source:
          plane: "chain"
        destination:
          plane: "ops"
        action: "deny"
      
      # Chain cannot access Wallet
      - source:
          plane: "chain"
        destination:
          plane: "wallet"
        action: "deny"
  
  # Wallet Plane Policies (TRON Isolation)
  - name: "wallet-plane-isolation"
    plane: "wallet"
    defaultAction: "deny"
    rules:
      # Wallet services can communicate with each other
      - source:
          plane: "wallet"
        destination:
          plane: "wallet"
        action: "allow"
        methods: ["GET", "POST", "PUT", "DELETE"]
      
      # Only API Gateway can call Wallet
      - source:
          plane: "ops"
          cluster: "api-gateway"
        destination:
          plane: "wallet"
        action: "allow"
        methods: ["POST", "GET"]
        paths:
          - "/api/v1/payments/*"
          - "/api/v1/wallets/*"
          - "/api/v1/transactions/*"
        rateLimit:
          requestsPerMinute: 100
          burstSize: 20
      
      # Wallet cannot access Chain
      - source:
          plane: "wallet"
        destination:
          plane: "chain"
        action: "deny"
      
      # Wallet cannot access Ops (except responses)
      - source:
          plane: "wallet"
        destination:
          plane: "ops"
        action: "deny"
```

## Rate Limiting

### Rate Limiting Configuration

```yaml
# Rate Limiting Rules per API Endpoint
rateLimiting:
  # Service Discovery APIs
  serviceDiscovery:
    registration:
      requestsPerMinute: 100
      burstSize: 20
      scope: "per-service"
    
    deregistration:
      requestsPerMinute: 100
      burstSize: 20
      scope: "per-service"
    
    healthUpdates:
      requestsPerMinute: 1000
      burstSize: 100
      scope: "per-service"
    
    discovery:
      requestsPerMinute: 1000
      burstSize: 200
      scope: "per-service"
  
  # Beta Sidecar APIs
  betaSidecar:
    configuration:
      requestsPerMinute: 10
      burstSize: 5
      scope: "per-sidecar"
    
    metrics:
      requestsPerMinute: 100
      burstSize: 20
      scope: "per-sidecar"
    
    health:
      requestsPerMinute: 1000
      burstSize: 100
      scope: "per-sidecar"
  
  # Service Mesh APIs
  serviceMesh:
    policyManagement:
      requestsPerMinute: 50
      burstSize: 10
      scope: "per-admin"
    
    trafficManagement:
      requestsPerMinute: 100
      burstSize: 20
      scope: "per-admin"
    
    securityManagement:
      requestsPerMinute: 50
      burstSize: 10
      scope: "per-admin"
  
  # Inter-Service Communication APIs
  interService:
    messageSending:
      requestsPerMinute: 1000
      burstSize: 200
      scope: "per-service"
    
    eventPublishing:
      requestsPerMinute: 500
      burstSize: 100
      scope: "per-service"
    
    eventSubscription:
      requestsPerMinute: 100
      burstSize: 20
      scope: "per-service"
  
  # TRON Payment Service (Critical)
  tronPayment:
    createPayment:
      requestsPerMinute: 100
      burstSize: 20
      scope: "per-user"
      enforceStrict: true
    
    checkPayment:
      requestsPerMinute: 500
      burstSize: 100
      scope: "per-user"
    
    listTransactions:
      requestsPerMinute: 200
      burstSize: 40
      scope: "per-user"
```

## Audit Logging

### 1. Audit Log Format

```yaml
# Audit Log Schema
AuditLogEntry:
  timestamp: "ISO 8601 datetime"
  requestId: "UUID"
  eventType: "string"
  severity: "string (INFO, WARN, ERROR, CRITICAL)"
  
  source:
    serviceId: "UUID"
    serviceName: "string"
    cluster: "string"
    plane: "string"
    ipAddress: "string"
    
  destination:
    serviceId: "UUID"
    serviceName: "string"
    cluster: "string"
    plane: "string"
    
  request:
    method: "string"
    path: "string"
    headers: "object"
    queryParams: "object"
    
  response:
    statusCode: "integer"
    latencyMs: "integer"
    bytesReceived: "integer"
    bytesSent: "integer"
    
  security:
    authenticated: "boolean"
    authMethod: "string (jwt, mtls, api-key)"
    principal: "string"
    permissions: "array"
    policyViolations: "array"
    
  metadata:
    correlationId: "UUID"
    traceId: "string"
    spanId: "string"
    userAgent: "string"
```

### 2. Audit Logger Implementation

```python
# lucid/service-mesh/monitoring/audit_logger.py

import json
import logging
from datetime import datetime
from typing import Dict, Optional
import uuid

logger = logging.getLogger(__name__)

class AuditLogger:
    """Centralized audit logging for service mesh."""
    
    def __init__(self, log_file: str = "/var/log/lucid/audit.log"):
        self.log_file = log_file
        
        # Configure audit logger
        self.audit_logger = logging.getLogger('lucid.audit')
        self.audit_logger.setLevel(logging.INFO)
        
        # File handler
        handler = logging.FileHandler(log_file)
        handler.setFormatter(
            logging.Formatter('%(message)s')
        )
        self.audit_logger.addHandler(handler)
    
    def log_service_communication(
        self,
        request_id: str,
        source: Dict,
        destination: Dict,
        request: Dict,
        response: Dict,
        security: Dict,
        metadata: Optional[Dict] = None
    ):
        """
        Log inter-service communication for audit trail.
        
        Args:
            request_id: Unique request identifier
            source: Source service information
            destination: Destination service information
            request: Request details
            response: Response details
            security: Security information
            metadata: Additional metadata
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "requestId": request_id,
            "eventType": "service_communication",
            "severity": self._determine_severity(response),
            "source": source,
            "destination": destination,
            "request": request,
            "response": response,
            "security": security,
            "metadata": metadata or {}
        }
        
        self.audit_logger.info(json.dumps(audit_entry))
        
        # Log security violations separately
        if security.get('policyViolations'):
            self.log_security_violation(audit_entry)
    
    def log_security_violation(self, audit_entry: Dict):
        """Log security policy violations with high severity."""
        violation_entry = {
            **audit_entry,
            "eventType": "security_violation",
            "severity": "CRITICAL"
        }
        
        self.audit_logger.critical(json.dumps(violation_entry))
        
        # Alert security monitoring system
        self._alert_security_team(violation_entry)
    
    def log_authentication_attempt(
        self,
        request_id: str,
        source: Dict,
        auth_method: str,
        success: bool,
        failure_reason: Optional[str] = None
    ):
        """Log authentication attempts."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "requestId": request_id,
            "eventType": "authentication_attempt",
            "severity": "INFO" if success else "WARN",
            "source": source,
            "security": {
                "authMethod": auth_method,
                "success": success,
                "failureReason": failure_reason
            }
        }
        
        self.audit_logger.info(json.dumps(audit_entry))
        
        # Track failed attempts for potential security threats
        if not success:
            self._track_failed_auth(source, auth_method)
    
    def log_rate_limit_exceeded(
        self,
        request_id: str,
        source: Dict,
        destination: Dict,
        rate_limit: Dict
    ):
        """Log rate limiting events."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "requestId": request_id,
            "eventType": "rate_limit_exceeded",
            "severity": "WARN",
            "source": source,
            "destination": destination,
            "rateLimit": rate_limit
        }
        
        self.audit_logger.warning(json.dumps(audit_entry))
    
    def _determine_severity(self, response: Dict) -> str:
        """Determine log severity based on response."""
        status_code = response.get('statusCode', 0)
        
        if status_code >= 500:
            return "ERROR"
        elif status_code >= 400:
            return "WARN"
        else:
            return "INFO"
    
    def _alert_security_team(self, violation_entry: Dict):
        """Alert security team of policy violations."""
        # Implementation would send to security monitoring system
        logger.critical(
            f"Security violation detected: {violation_entry['requestId']}"
        )
    
    def _track_failed_auth(self, source: Dict, auth_method: str):
        """Track failed authentication attempts."""
        # Implementation would track and potentially block repeat offenders
        logger.warning(
            f"Failed authentication from {source.get('serviceName')} "
            f"using {auth_method}"
        )
```

## Tor Integration

### Tor Hidden Service Configuration

```yaml
# Tor Configuration for .onion Endpoints
torConfiguration:
  hiddenServices:
    - name: "api-gateway"
      onionAddress: "api-gateway.lucid.onion"
      localPort: 8080
      virtualPort: 8080
      
    - name: "admin-interface"
      onionAddress: "admin-interface.lucid.onion"
      localPort: 8083
      virtualPort: 8083
      
    - name: "service-mesh-controller"
      onionAddress: "service-mesh.lucid.onion"
      localPort: 8080
      virtualPort: 8080
  
  circuits:
    buildTimeout: 60
    circuitPadding: true
    maxCircuitDirtiness: 600
    
  security:
    enforceDistinctSubnets: true
    strictNodes: true
    isolateDestPort: true
    isolateDestAddr: true
```

## Compliance Requirements

### 1. Data Protection

- All inter-service communication must be encrypted (mTLS)
- Sensitive data must not be logged in audit logs
- Certificate rotation must occur every 90 days
- Failed authentication attempts must be logged and monitored

### 2. Access Control

- Services must authenticate using both mTLS and JWT
- Plane isolation must be strictly enforced
- TRON wallet operations must be isolated from other services
- Rate limiting must be enforced on all endpoints

### 3. Audit Trail

- All service-to-service communications must be audited
- Security policy violations must be logged and alerted
- Audit logs must be retained for 12 months
- Audit logs must be tamper-proof

### 4. TRON Isolation (Critical)

- Wallet plane services must not communicate with Chain plane
- Only API Gateway can initiate requests to TRON payment service
- All TRON transactions must be logged with full audit trail
- TRON private keys must never leave wallet plane

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10

