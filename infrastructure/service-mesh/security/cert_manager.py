"""
Lucid Service Mesh - Certificate Manager
Certificate lifecycle management for service mesh.

File: infrastructure/service-mesh/security/cert_manager.py
Lines: ~250
Purpose: Certificate management
Dependencies: cryptography, asyncio
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from .mtls_manager import mTLSManager

logger = logging.getLogger(__name__)


class CertManager:
    """
    Certificate lifecycle manager for service mesh.
    
    Handles:
    - Certificate lifecycle management
    - Certificate distribution
    - Certificate monitoring
    - Automatic renewal
    """
    
    def __init__(self):
        self.mtls_manager = mTLSManager()
        self.cert_monitoring: Dict[str, Dict[str, Any]] = {}
        self.auto_renewal_enabled = True
        self.renewal_threshold_days = 30
        self.monitoring_interval = 3600  # 1 hour
        
    async def initialize(self):
        """Initialize certificate manager."""
        try:
            logger.info("Initializing Certificate Manager...")
            
            # Initialize mTLS manager
            await self.mtls_manager.initialize()
            
            # Start monitoring task
            if self.auto_renewal_enabled:
                asyncio.create_task(self._monitoring_loop())
                
            logger.info("Certificate Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Certificate Manager: {e}")
            raise
            
    async def _monitoring_loop(self):
        """Background task for certificate monitoring."""
        while True:
            try:
                await self._check_certificates()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in certificate monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
                
    async def _check_certificates(self):
        """Check all certificates for renewal needs."""
        try:
            for service_name in await self.mtls_manager.list_certificates():
                await self._check_certificate_renewal(service_name)
                
        except Exception as e:
            logger.error(f"Error checking certificates: {e}")
            
    async def _check_certificate_renewal(self, service_name: str):
        """Check if a certificate needs renewal."""
        try:
            cert_info = await self.mtls_manager.get_certificate_info(service_name)
            if not cert_info:
                return
                
            # Parse validity dates
            valid_to = datetime.fromisoformat(cert_info["valid_to"])
            days_until_expiry = (valid_to - datetime.utcnow()).days
            
            # Update monitoring info
            self.cert_monitoring[service_name] = {
                "days_until_expiry": days_until_expiry,
                "needs_renewal": days_until_expiry <= self.renewal_threshold_days,
                "last_check": datetime.utcnow().isoformat()
            }
            
            # Auto-renew if needed
            if days_until_expiry <= self.renewal_threshold_days:
                logger.info(f"Certificate for {service_name} needs renewal ({days_until_expiry} days left)")
                await self.renew_certificate(service_name)
                
        except Exception as e:
            logger.error(f"Error checking certificate renewal for {service_name}: {e}")
            
    async def issue_certificate(
        self,
        service_name: str,
        validity_days: int = None
    ) -> bool:
        """
        Issue a new certificate for a service.
        
        Args:
            service_name: Service name
            validity_days: Certificate validity in days
            
        Returns:
            True if certificate issued successfully
        """
        try:
            logger.info(f"Issuing certificate for service: {service_name}")
            
            # Generate certificate
            cert, private_key = await self.mtls_manager.generate_certificate(
                service_name, validity_days
            )
            
            # Initialize monitoring
            self.cert_monitoring[service_name] = {
                "days_until_expiry": validity_days or self.mtls_manager.cert_validity_days,
                "needs_renewal": False,
                "last_check": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Certificate issued successfully for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to issue certificate for {service_name}: {e}")
            return False
            
    async def renew_certificate(self, service_name: str) -> bool:
        """
        Renew certificate for a service.
        
        Args:
            service_name: Service name
            
        Returns:
            True if renewal successful
        """
        try:
            logger.info(f"Renewing certificate for service: {service_name}")
            
            # Rotate certificate
            success = await self.mtls_manager.rotate_certificate(service_name)
            
            if success:
                # Update monitoring info
                cert_info = await self.mtls_manager.get_certificate_info(service_name)
                if cert_info:
                    valid_to = datetime.fromisoformat(cert_info["valid_to"])
                    days_until_expiry = (valid_to - datetime.utcnow()).days
                    
                    self.cert_monitoring[service_name] = {
                        "days_until_expiry": days_until_expiry,
                        "needs_renewal": False,
                        "last_check": datetime.utcnow().isoformat(),
                        "last_renewal": datetime.utcnow().isoformat()
                    }
                    
                logger.info(f"Certificate renewed successfully for {service_name}")
                return True
            else:
                logger.error(f"Failed to renew certificate for {service_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error renewing certificate for {service_name}: {e}")
            return False
            
    async def revoke_certificate(self, service_name: str) -> bool:
        """
        Revoke certificate for a service.
        
        Args:
            service_name: Service name
            
        Returns:
            True if revocation successful
        """
        try:
            logger.info(f"Revoking certificate for service: {service_name}")
            
            # Remove from mTLS manager
            if service_name in self.mtls_manager.certificates:
                del self.mtls_manager.certificates[service_name]
                
            if service_name in self.mtls_manager.private_keys:
                del self.mtls_manager.private_keys[service_name]
                
            # Remove from monitoring
            if service_name in self.cert_monitoring:
                del self.cert_monitoring[service_name]
                
            # Remove certificate files
            cert_path = os.path.join(self.mtls_manager.cert_storage_path, f"{service_name}.crt")
            key_path = os.path.join(self.mtls_manager.cert_storage_path, f"{service_name}.key")
            
            if os.path.exists(cert_path):
                os.remove(cert_path)
            if os.path.exists(key_path):
                os.remove(key_path)
                
            logger.info(f"Certificate revoked successfully for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke certificate for {service_name}: {e}")
            return False
            
    async def validate_certificate(self, service_name: str) -> bool:
        """
        Validate certificate for a service.
        
        Args:
            service_name: Service name
            
        Returns:
            True if certificate is valid
        """
        return await self.mtls_manager.validate_certificate(service_name)
        
    async def get_certificate_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get certificate status for a service."""
        try:
            cert_info = await self.mtls_manager.get_certificate_info(service_name)
            monitoring_info = self.cert_monitoring.get(service_name, {})
            
            if not cert_info:
                return None
                
            return {
                "service_name": service_name,
                "certificate_info": cert_info,
                "monitoring_info": monitoring_info,
                "is_valid": await self.mtls_manager.validate_certificate(service_name)
            }
            
        except Exception as e:
            logger.error(f"Error getting certificate status for {service_name}: {e}")
            return None
            
    async def list_certificates(self) -> List[Dict[str, Any]]:
        """List all certificates with their status."""
        try:
            certificates = []
            
            for service_name in await self.mtls_manager.list_certificates():
                status = await self.get_certificate_status(service_name)
                if status:
                    certificates.append(status)
                    
            return certificates
            
        except Exception as e:
            logger.error(f"Error listing certificates: {e}")
            return []
            
    async def get_expiring_certificates(self, days_threshold: int = None) -> List[str]:
        """
        Get list of certificates expiring within threshold.
        
        Args:
            days_threshold: Days threshold (default: renewal_threshold_days)
            
        Returns:
            List of service names with expiring certificates
        """
        try:
            if not days_threshold:
                days_threshold = self.renewal_threshold_days
                
            expiring_services = []
            
            for service_name, monitoring_info in self.cert_monitoring.items():
                days_until_expiry = monitoring_info.get("days_until_expiry", 0)
                if days_until_expiry <= days_threshold:
                    expiring_services.append(service_name)
                    
            return expiring_services
            
        except Exception as e:
            logger.error(f"Error getting expiring certificates: {e}")
            return []
            
    def set_auto_renewal(self, enabled: bool):
        """Enable or disable automatic certificate renewal."""
        self.auto_renewal_enabled = enabled
        logger.info(f"Auto-renewal {'enabled' if enabled else 'disabled'}")
        
    def set_renewal_threshold(self, days: int):
        """Set certificate renewal threshold in days."""
        self.renewal_threshold_days = days
        logger.info(f"Renewal threshold set to {days} days")
        
    def get_status(self) -> Dict[str, Any]:
        """Get certificate manager status."""
        return {
            "auto_renewal_enabled": self.auto_renewal_enabled,
            "renewal_threshold_days": self.renewal_threshold_days,
            "monitoring_interval": self.monitoring_interval,
            "certificates_count": len(self.cert_monitoring),
            "mtls_manager_status": self.mtls_manager.get_status(),
            "last_update": datetime.utcnow().isoformat()
        }
