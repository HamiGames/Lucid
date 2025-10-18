"""
Lucid Service Mesh - mTLS Manager
Mutual TLS certificate management for service mesh.

File: infrastructure/service-mesh/security/mtls_manager.py
Lines: ~280
Purpose: mTLS management
Dependencies: cryptography, asyncio
"""

import asyncio
import logging
import ssl
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
import os

logger = logging.getLogger(__name__)


class mTLSManager:
    """
    Mutual TLS certificate manager for service mesh.
    
    Handles:
    - Certificate generation
    - Certificate validation
    - Certificate rotation
    - mTLS configuration
    """
    
    def __init__(self):
        self.certificates: Dict[str, Dict[str, Any]] = {}
        self.private_keys: Dict[str, bytes] = {}
        self.ca_cert: Optional[x509.Certificate] = None
        self.ca_private_key: Optional[rsa.RSAPrivateKey] = None
        self.cert_validity_days = 90
        self.cert_storage_path = "/etc/ssl/lucid"
        
    async def initialize(self):
        """Initialize mTLS manager."""
        try:
            logger.info("Initializing mTLS Manager...")
            
            # Create certificate storage directory
            os.makedirs(self.cert_storage_path, exist_ok=True)
            
            # Generate or load CA certificate
            await self._initialize_ca()
            
            logger.info("mTLS Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize mTLS Manager: {e}")
            raise
            
    async def _initialize_ca(self):
        """Initialize Certificate Authority."""
        try:
            ca_cert_path = os.path.join(self.cert_storage_path, "ca.crt")
            ca_key_path = os.path.join(self.cert_storage_path, "ca.key")
            
            if os.path.exists(ca_cert_path) and os.path.exists(ca_key_path):
                # Load existing CA
                await self._load_ca_certificate(ca_cert_path, ca_key_path)
            else:
                # Generate new CA
                await self._generate_ca_certificate()
                
        except Exception as e:
            logger.error(f"Failed to initialize CA: {e}")
            raise
            
    async def _load_ca_certificate(self, cert_path: str, key_path: str):
        """Load existing CA certificate."""
        try:
            # Load CA certificate
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
                self.ca_cert = x509.load_pem_x509_certificate(cert_data)
                
            # Load CA private key
            with open(key_path, 'rb') as f:
                key_data = f.read()
                self.ca_private_key = serialization.load_pem_private_key(
                    key_data, password=None
                )
                
            logger.info("CA certificate loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load CA certificate: {e}")
            raise
            
    async def _generate_ca_certificate(self):
        """Generate new CA certificate."""
        try:
            # Generate CA private key
            self.ca_private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Generate CA certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Lucid"),
                x509.NameAttribute(NameOID.COMMON_NAME, "Lucid CA"),
            ])
            
            self.ca_cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                self.ca_private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            ).add_extension(
                x509.KeyUsage(
                    key_cert_sign=True,
                    crl_sign=True,
                    digital_signature=True,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True,
            ).sign(self.ca_private_key, hashes.SHA256())
            
            # Save CA certificate and key
            await self._save_ca_certificate()
            
            logger.info("CA certificate generated successfully")
            
        except Exception as e:
            logger.error(f"Failed to generate CA certificate: {e}")
            raise
            
    async def _save_ca_certificate(self):
        """Save CA certificate and key to files."""
        try:
            # Save CA certificate
            ca_cert_path = os.path.join(self.cert_storage_path, "ca.crt")
            with open(ca_cert_path, 'wb') as f:
                f.write(self.ca_cert.public_bytes(serialization.Encoding.PEM))
                
            # Save CA private key
            ca_key_path = os.path.join(self.cert_storage_path, "ca.key")
            with open(ca_key_path, 'wb') as f:
                f.write(self.ca_private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
                
        except Exception as e:
            logger.error(f"Failed to save CA certificate: {e}")
            raise
            
    async def generate_certificate(
        self,
        service_name: str,
        validity_days: int = None
    ) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """
        Generate certificate for a service.
        
        Args:
            service_name: Service name
            validity_days: Certificate validity in days
            
        Returns:
            Tuple of (certificate, private_key)
        """
        try:
            if not validity_days:
                validity_days = self.cert_validity_days
                
            logger.info(f"Generating certificate for service: {service_name}")
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Generate certificate
            subject = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Lucid"),
                x509.NameAttribute(NameOID.COMMON_NAME, f"{service_name}.lucid.internal"),
            ])
            
            # Add SAN (Subject Alternative Name)
            san_list = [
                x509.DNSName(f"{service_name}.lucid.internal"),
                x509.DNSName(f"{service_name}"),
                x509.DNSName("localhost"),
                x509.IPAddress("127.0.0.1")
            ]
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                self.ca_cert.subject
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=validity_days)
            ).add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            ).add_extension(
                x509.KeyUsage(
                    key_cert_sign=False,
                    crl_sign=False,
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True,
            ).add_extension(
                x509.ExtendedKeyUsage([
                    ExtendedKeyUsageOID.SERVER_AUTH,
                    ExtendedKeyUsageOID.CLIENT_AUTH
                ]),
                critical=True,
            ).sign(self.ca_private_key, hashes.SHA256())
            
            # Store certificate and key
            self.certificates[service_name] = {
                "certificate": cert,
                "valid_from": cert.not_valid_before,
                "valid_to": cert.not_valid_after,
                "generated_at": datetime.utcnow().isoformat()
            }
            self.private_keys[service_name] = private_key
            
            # Save certificate and key to files
            await self._save_service_certificate(service_name, cert, private_key)
            
            logger.info(f"Certificate generated successfully for {service_name}")
            return cert, private_key
            
        except Exception as e:
            logger.error(f"Failed to generate certificate for {service_name}: {e}")
            raise
            
    async def _save_service_certificate(
        self,
        service_name: str,
        cert: x509.Certificate,
        private_key: rsa.RSAPrivateKey
    ):
        """Save service certificate and key to files."""
        try:
            # Save certificate
            cert_path = os.path.join(self.cert_storage_path, f"{service_name}.crt")
            with open(cert_path, 'wb') as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
                
            # Save private key
            key_path = os.path.join(self.cert_storage_path, f"{service_name}.key")
            with open(key_path, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
                
        except Exception as e:
            logger.error(f"Failed to save certificate for {service_name}: {e}")
            raise
            
    async def validate_certificate(self, service_name: str) -> bool:
        """
        Validate certificate for a service.
        
        Args:
            service_name: Service name
            
        Returns:
            True if certificate is valid
        """
        try:
            if service_name not in self.certificates:
                return False
                
            cert_info = self.certificates[service_name]
            cert = cert_info["certificate"]
            
            # Check if certificate is not expired
            now = datetime.utcnow()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                return False
                
            # Verify certificate signature
            try:
                cert.public_key().verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    cert.signature_algorithm_oid._name,
                    cert.signature_hash_algorithm
                )
            except Exception:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate certificate for {service_name}: {e}")
            return False
            
    async def rotate_certificate(self, service_name: str) -> bool:
        """
        Rotate certificate for a service.
        
        Args:
            service_name: Service name
            
        Returns:
            True if rotation successful
        """
        try:
            logger.info(f"Rotating certificate for service: {service_name}")
            
            # Generate new certificate
            new_cert, new_key = await self.generate_certificate(service_name)
            
            logger.info(f"Certificate rotated successfully for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate certificate for {service_name}: {e}")
            return False
            
    async def get_certificate_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get certificate information for a service."""
        if service_name not in self.certificates:
            return None
            
        cert_info = self.certificates[service_name]
        cert = cert_info["certificate"]
        
        return {
            "service_name": service_name,
            "subject": cert.subject.rfc4514_string(),
            "issuer": cert.issuer.rfc4514_string(),
            "valid_from": cert.not_valid_before.isoformat(),
            "valid_to": cert.not_valid_after.isoformat(),
            "serial_number": str(cert.serial_number),
            "generated_at": cert_info["generated_at"]
        }
        
    async def list_certificates(self) -> List[str]:
        """List all certificates."""
        return list(self.certificates.keys())
        
    async def get_ssl_context(
        self,
        service_name: str,
        server_side: bool = True
    ) -> ssl.SSLContext:
        """
        Get SSL context for a service.
        
        Args:
            service_name: Service name
            server_side: True for server context, False for client
            
        Returns:
            SSL context
        """
        try:
            if service_name not in self.certificates:
                raise ValueError(f"No certificate found for service {service_name}")
                
            # Create SSL context
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH if server_side else ssl.Purpose.SERVER_AUTH)
            
            # Load certificate and key
            cert_path = os.path.join(self.cert_storage_path, f"{service_name}.crt")
            key_path = os.path.join(self.cert_storage_path, f"{service_name}.key")
            ca_path = os.path.join(self.cert_storage_path, "ca.crt")
            
            if server_side:
                context.load_cert_chain(cert_path, key_path)
                context.load_verify_locations(ca_path)
                context.verify_mode = ssl.CERT_REQUIRED
            else:
                context.load_verify_locations(ca_path)
                context.verify_mode = ssl.CERT_REQUIRED
                
            return context
            
        except Exception as e:
            logger.error(f"Failed to create SSL context for {service_name}: {e}")
            raise
            
    def get_status(self) -> Dict[str, Any]:
        """Get mTLS manager status."""
        return {
            "ca_initialized": self.ca_cert is not None,
            "certificates_count": len(self.certificates),
            "cert_validity_days": self.cert_validity_days,
            "cert_storage_path": self.cert_storage_path,
            "last_update": datetime.utcnow().isoformat()
        }
