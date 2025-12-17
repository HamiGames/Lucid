"""
mTLS certificate manager for service mesh

File: service-mesh/certificate_manager.py
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Optional cryptography import
try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logger.warning("cryptography package not available")


class CertificateManager:
    """mTLS certificate manager"""
    
    def __init__(self, settings):
        self.settings = settings
        self.ca_cert = None
        self.ca_key = None
        self.certificates: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize certificate manager"""
        try:
            if not CRYPTOGRAPHY_AVAILABLE:
                logger.warning("Cryptography library not available, running in mock mode")
                return
            
            # Create CA certificate
            await self._create_ca_certificate()
            
            # Create certificates directory
            os.makedirs(self.settings.CERTIFICATES_PATH, exist_ok=True)
            
            logger.info("Certificate manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize certificate manager: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup certificate manager"""
        logger.info("Certificate manager cleaned up")
    
    async def _create_ca_certificate(self):
        """Create CA certificate"""
        if not CRYPTOGRAPHY_AVAILABLE:
            return
            
        # Generate CA private key
        self.ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.settings.CERT_KEY_SIZE
        )
        
        # Create CA certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, self.settings.CERT_COUNTRY),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, self.settings.CERT_STATE),
            x509.NameAttribute(NameOID.LOCALITY_NAME, self.settings.CERT_LOCALITY),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.settings.CERT_ORGANIZATION),
            x509.NameAttribute(NameOID.COMMON_NAME, "Lucid CA"),
        ])
        
        self.ca_cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            self.ca_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=self.settings.CA_VALIDITY_DAYS)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).sign(self.ca_key, hashes.SHA256())
        
        # Save CA certificate
        ca_cert_path = os.path.join(self.settings.CERTIFICATES_PATH, "ca.crt")
        ca_key_path = os.path.join(self.settings.CERTIFICATES_PATH, "ca.key")
        
        os.makedirs(self.settings.CERTIFICATES_PATH, exist_ok=True)
        
        with open(ca_cert_path, "wb") as f:
            f.write(self.ca_cert.public_bytes(serialization.Encoding.PEM))
        
        with open(ca_key_path, "wb") as f:
            f.write(self.ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        logger.info("CA certificate created")
    
    async def generate_service_certificate(self, service_name: str) -> Dict[str, Any]:
        """Generate mTLS certificate for service"""
        if not CRYPTOGRAPHY_AVAILABLE or not self.ca_cert or not self.ca_key:
            raise RuntimeError("Certificate manager not properly initialized")
            
        try:
            # Generate service private key
            service_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=self.settings.CERT_KEY_SIZE
            )
            
            # Create service certificate
            subject = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, self.settings.CERT_COUNTRY),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, self.settings.CERT_STATE),
                x509.NameAttribute(NameOID.LOCALITY_NAME, self.settings.CERT_LOCALITY),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.settings.CERT_ORGANIZATION),
                x509.NameAttribute(NameOID.COMMON_NAME, service_name),
            ])
            
            service_cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                self.ca_cert.subject
            ).public_key(
                service_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=self.settings.CERT_VALIDITY_DAYS)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(service_name),
                    x509.DNSName(f"{service_name}.lucid.local"),
                ]),
                critical=False,
            ).sign(self.ca_key, hashes.SHA256())
            
            # Save certificates
            cert_path = os.path.join(self.settings.CERTIFICATES_PATH, f"{service_name}.crt")
            key_path = os.path.join(self.settings.CERTIFICATES_PATH, f"{service_name}.key")
            
            with open(cert_path, "wb") as f:
                f.write(service_cert.public_bytes(serialization.Encoding.PEM))
            
            with open(key_path, "wb") as f:
                f.write(service_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Store certificate info
            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(days=self.settings.CERT_VALIDITY_DAYS)
            
            self.certificates[service_name] = {
                "cert_path": cert_path,
                "key_path": key_path,
                "created_at": created_at,
                "expires_at": expires_at
            }
            
            logger.info(f"Certificate generated for service {service_name}")
            
            return {
                "service_name": service_name,
                "cert_path": cert_path,
                "key_path": key_path,
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate certificate for {service_name}: {e}")
            raise
    
    async def get_certificate(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get certificate info for service"""
        if service_name in self.certificates:
            cert_info = self.certificates[service_name]
            return {
                "service_name": service_name,
                "cert_path": cert_info["cert_path"],
                "key_path": cert_info["key_path"],
                "created_at": cert_info["created_at"].isoformat(),
                "expires_at": cert_info["expires_at"].isoformat()
            }
        return None
    
    async def list_certificates(self) -> List[Dict[str, Any]]:
        """List all certificates"""
        return [
            {
                "service_name": name,
                "cert_path": info["cert_path"],
                "key_path": info["key_path"],
                "created_at": info["created_at"].isoformat(),
                "expires_at": info["expires_at"].isoformat()
            }
            for name, info in self.certificates.items()
        ]
    
    async def revoke_certificate(self, service_name: str) -> bool:
        """Revoke certificate for service"""
        if service_name not in self.certificates:
            return False
            
        try:
            cert_info = self.certificates[service_name]
            
            # Remove certificate files
            if os.path.exists(cert_info["cert_path"]):
                os.remove(cert_info["cert_path"])
            if os.path.exists(cert_info["key_path"]):
                os.remove(cert_info["key_path"])
            
            # Remove from tracking
            del self.certificates[service_name]
            
            logger.info(f"Certificate revoked for service {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke certificate for {service_name}: {e}")
            return False
    
    async def get_ca_certificate(self) -> Optional[str]:
        """Get CA certificate"""
        if not self.ca_cert:
            return None
        return self.ca_cert.public_bytes(serialization.Encoding.PEM).decode()
    
    async def check_health(self) -> bool:
        """Check certificate manager health"""
        try:
            return self.ca_cert is not None and self.ca_key is not None
        except Exception:
            return False

