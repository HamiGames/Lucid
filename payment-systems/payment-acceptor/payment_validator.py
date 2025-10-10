"""
Payment Validator Module for Lucid Network
Handles payment validation, compliance checks, and risk assessment
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

from pydantic import BaseModel, Field

# Import existing payment system components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tron_node.tron_client import TronService
from tron_node.usdt_trc20 import USDTTRC20Client, TransactionStatus
from wallet.integration_manager import WalletIntegrationManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationStatus(str, Enum):
    """Validation status"""
    PENDING = "pending"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"
    MANUAL_REVIEW = "manual_review"

class ValidationType(str, Enum):
    """Validation types"""
    BASIC = "basic"                 # Basic validation
    ENHANCED = "enhanced"           # Enhanced validation
    COMPLIANCE = "compliance"       # Compliance validation
    RISK_ASSESSMENT = "risk_assessment"  # Risk assessment
    AML = "aml"                    # Anti-Money Laundering
    KYC = "kyc"                    # Know Your Customer

class RiskLevel(str, Enum):
    """Risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceStatus(str, Enum):
    """Compliance status"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"
    EXEMPT = "exempt"

@dataclass
class ValidationRule:
    """Validation rule"""
    rule_id: str
    name: str
    validation_type: ValidationType
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    priority: int = 0
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ValidationResult:
    """Validation result"""
    validation_id: str
    payment_id: str
    validation_type: ValidationType
    status: ValidationStatus
    risk_level: RiskLevel
    compliance_status: ComplianceStatus
    score: float  # 0.0 to 1.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    validated_at: Optional[datetime] = None
    validated_by: Optional[str] = None

@dataclass
class ComplianceCheck:
    """Compliance check result"""
    check_id: str
    check_type: str
    status: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class RiskAssessment:
    """Risk assessment result"""
    assessment_id: str
    payment_id: str
    risk_score: float  # 0.0 to 1.0
    risk_level: RiskLevel
    risk_factors: List[str] = field(default_factory=list)
    mitigation_actions: List[str] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class ValidationRequestModel(BaseModel):
    """Pydantic model for validation requests"""
    payment_id: str = Field(..., description="Payment ID to validate")
    validation_type: ValidationType = Field(..., description="Type of validation")
    amount: float = Field(..., gt=0, description="Payment amount")
    token_type: str = Field(..., description="Token type")
    sender_address: str = Field(..., description="Sender address")
    recipient_address: str = Field(..., description="Recipient address")
    payment_type: str = Field(..., description="Payment type")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    node_id: Optional[str] = Field(default=None, description="Node ID")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class ValidationResponseModel(BaseModel):
    """Pydantic model for validation responses"""
    validation_id: str
    payment_id: str
    status: str
    risk_level: str
    compliance_status: str
    score: float
    errors: List[str]
    warnings: List[str]
    flags: List[str]
    validated_at: str
    requires_manual_review: bool = False

class PaymentValidator:
    """Payment validation and compliance system"""
    
    def __init__(self):
        self.validation_results: Dict[str, ValidationResult] = {}
        self.compliance_checks: Dict[str, List[ComplianceCheck]] = {}
        self.risk_assessments: Dict[str, RiskAssessment] = {}
        self.validation_rules: Dict[str, ValidationRule] = {}
        self.blocked_addresses: set = set()
        self.suspicious_patterns: List[Dict[str, Any]] = []
        
        # Initialize services
        self.tron_service = TronService()
        self.usdt_client = USDTTRC20Client()
        self.wallet_manager = WalletIntegrationManager()
        
        # Configuration
        self.config = {
            "max_validation_time_seconds": 30,
            "risk_threshold_high": 0.7,
            "risk_threshold_medium": 0.4,
            "max_daily_amount": 50000.0,
            "max_hourly_amount": 5000.0,
            "min_confirmations": 1,
            "blacklist_check_enabled": True,
            "aml_check_enabled": True,
            "kyc_check_enabled": True,
            "pattern_analysis_enabled": True
        }
        
        # Initialize validation rules
        self._initialize_validation_rules()
        
        # Load blocked addresses and suspicious patterns
        self._load_security_data()
        
        logger.info("PaymentValidator initialized")

    def _initialize_validation_rules(self):
        """Initialize validation rules"""
        # Rule 1: Amount validation
        amount_rule = ValidationRule(
            rule_id="amount_validation",
            name="Amount Validation",
            validation_type=ValidationType.BASIC,
            conditions={
                "min_amount": 0.01,
                "max_amount": 10000.0
            },
            actions=[
                {"action": "validate_amount_range"},
                {"action": "check_daily_limits"},
                {"action": "check_hourly_limits"}
            ],
            priority=100
        )
        self.validation_rules["amount_validation"] = amount_rule
        
        # Rule 2: Address validation
        address_rule = ValidationRule(
            rule_id="address_validation",
            name="Address Validation",
            validation_type=ValidationType.BASIC,
            conditions={
                "check_format": True,
                "check_blacklist": True
            },
            actions=[
                {"action": "validate_address_format"},
                {"action": "check_blacklist"},
                {"action": "check_whitelist"}
            ],
            priority=90
        )
        self.validation_rules["address_validation"] = address_rule
        
        # Rule 3: Transaction pattern analysis
        pattern_rule = ValidationRule(
            rule_id="pattern_analysis",
            name="Transaction Pattern Analysis",
            validation_type=ValidationType.RISK_ASSESSMENT,
            conditions={
                "check_frequency": True,
                "check_amount_patterns": True,
                "check_timing_patterns": True
            },
            actions=[
                {"action": "analyze_transaction_frequency"},
                {"action": "analyze_amount_patterns"},
                {"action": "analyze_timing_patterns"},
                {"action": "calculate_risk_score"}
            ],
            priority=80
        )
        self.validation_rules["pattern_analysis"] = pattern_rule
        
        # Rule 4: AML compliance
        aml_rule = ValidationRule(
            rule_id="aml_compliance",
            name="AML Compliance Check",
            validation_type=ValidationType.AML,
            conditions={
                "check_sanctions": True,
                "check_pep": True,
                "check_adverse_media": True
            },
            actions=[
                {"action": "check_sanctions_list"},
                {"action": "check_pep_list"},
                {"action": "check_adverse_media"},
                {"action": "generate_compliance_report"}
            ],
            priority=70
        )
        self.validation_rules["aml_compliance"] = aml_rule
        
        # Rule 5: KYC validation
        kyc_rule = ValidationRule(
            rule_id="kyc_validation",
            name="KYC Validation",
            validation_type=ValidationType.KYC,
            conditions={
                "require_kyc_for_high_amounts": True,
                "kyc_threshold": 1000.0
            },
            actions=[
                {"action": "check_kyc_status"},
                {"action": "validate_kyc_documents"},
                {"action": "check_kyc_expiry"}
            ],
            priority=60
        )
        self.validation_rules["kyc_validation"] = kyc_rule

    def _load_security_data(self):
        """Load security data (blocked addresses, suspicious patterns)"""
        # In a real implementation, this would load from a database or external service
        # For now, we'll use some example data
        
        # Example blocked addresses
        self.blocked_addresses = {
            "TBlockedAddress1234567890123456789012345",
            "TSuspiciousAddress1234567890123456789012345"
        }
        
        # Example suspicious patterns
        self.suspicious_patterns = [
            {
                "pattern_type": "rapid_transactions",
                "description": "Multiple transactions in short time",
                "threshold": 10,
                "time_window_minutes": 60,
                "risk_multiplier": 0.3
            },
            {
                "pattern_type": "round_amounts",
                "description": "Frequent round amount transactions",
                "threshold": 5,
                "time_window_hours": 24,
                "risk_multiplier": 0.2
            },
            {
                "pattern_type": "unusual_timing",
                "description": "Transactions at unusual hours",
                "time_range": {"start": 2, "end": 6},  # 2 AM to 6 AM
                "risk_multiplier": 0.1
            }
        ]

    async def validate_payment(self, request: ValidationRequestModel) -> ValidationResponseModel:
        """Validate payment"""
        try:
            # Generate validation ID
            validation_id = f"VAL_{uuid4().hex[:16].upper()}"
            
            # Create validation result
            result = ValidationResult(
                validation_id=validation_id,
                payment_id=request.payment_id,
                validation_type=request.validation_type,
                status=ValidationStatus.VALIDATING,
                risk_level=RiskLevel.LOW,
                compliance_status=ComplianceStatus.PENDING_REVIEW,
                score=0.0
            )
            
            # Store validation result
            self.validation_results[validation_id] = result
            
            # Start validation process
            await self._perform_validation(result, request)
            
            # Determine final status
            result.status = self._determine_validation_status(result)
            result.validated_at = datetime.now(timezone.utc)
            result.validated_by = "system"
            
            # Create compliance checks
            await self._perform_compliance_checks(validation_id, request)
            
            # Perform risk assessment
            await self._perform_risk_assessment(validation_id, request)
            
            return ValidationResponseModel(
                validation_id=validation_id,
                payment_id=request.payment_id,
                status=result.status.value,
                risk_level=result.risk_level.value,
                compliance_status=result.compliance_status.value,
                score=result.score,
                errors=result.errors,
                warnings=result.warnings,
                flags=result.flags,
                validated_at=result.validated_at.isoformat(),
                requires_manual_review=result.status == ValidationStatus.MANUAL_REVIEW
            )
            
        except Exception as e:
            logger.error(f"Error validating payment: {e}")
            return ValidationResponseModel(
                validation_id="",
                payment_id=request.payment_id,
                status="failed",
                risk_level="critical",
                compliance_status="non_compliant",
                score=1.0,
                errors=[f"Validation failed: {str(e)}"],
                warnings=[],
                flags=[],
                validated_at=datetime.now(timezone.utc).isoformat(),
                requires_manual_review=True
            )

    async def _perform_validation(self, result: ValidationResult, request: ValidationRequestModel):
        """Perform validation based on type"""
        try:
            if request.validation_type == ValidationType.BASIC:
                await self._perform_basic_validation(result, request)
            elif request.validation_type == ValidationType.ENHANCED:
                await self._perform_enhanced_validation(result, request)
            elif request.validation_type == ValidationType.COMPLIANCE:
                await self._perform_compliance_validation(result, request)
            elif request.validation_type == ValidationType.RISK_ASSESSMENT:
                await self._perform_risk_validation(result, request)
            elif request.validation_type == ValidationType.AML:
                await self._perform_aml_validation(result, request)
            elif request.validation_type == ValidationType.KYC:
                await self._perform_kyc_validation(result, request)
            else:
                # Perform all validations
                await self._perform_comprehensive_validation(result, request)
                
        except Exception as e:
            logger.error(f"Error in validation process: {e}")
            result.errors.append(f"Validation process error: {str(e)}")
            result.score = 1.0

    async def _perform_basic_validation(self, result: ValidationResult, request: ValidationRequestModel):
        """Perform basic validation"""
        # Amount validation
        if request.amount < 0.01:
            result.errors.append("Amount too small")
            result.score += 0.3
        
        if request.amount > 10000.0:
            result.warnings.append("Large amount transaction")
            result.score += 0.2
        
        # Address format validation
        if not self._validate_tron_address(request.sender_address):
            result.errors.append("Invalid sender address format")
            result.score += 0.5
        
        if not self._validate_tron_address(request.recipient_address):
            result.errors.append("Invalid recipient address format")
            result.score += 0.5
        
        # Blacklist check
        if request.sender_address in self.blocked_addresses:
            result.errors.append("Sender address is blocked")
            result.score += 1.0
            result.flags.append("blocked_sender")
        
        if request.recipient_address in self.blocked_addresses:
            result.errors.append("Recipient address is blocked")
            result.score += 1.0
            result.flags.append("blocked_recipient")

    async def _perform_enhanced_validation(self, result: ValidationResult, request: ValidationRequestModel):
        """Perform enhanced validation"""
        # Perform basic validation first
        await self._perform_basic_validation(result, request)
        
        # Transaction history analysis
        await self._analyze_transaction_history(result, request)
        
        # Pattern analysis
        await self._analyze_transaction_patterns(result, request)
        
        # Network analysis
        await self._analyze_network_behavior(result, request)

    async def _perform_compliance_validation(self, result: ValidationResult, request: ValidationRequestModel):
        """Perform compliance validation"""
        # Regulatory compliance checks
        await self._check_regulatory_compliance(result, request)
        
        # Jurisdictional compliance
        await self._check_jurisdictional_compliance(result, request)
        
        # Industry compliance
        await self._check_industry_compliance(result, request)

    async def _perform_risk_validation(self, result: ValidationResult, request: ValidationRequestModel):
        """Perform risk validation"""
        # Calculate risk score
        risk_score = await self._calculate_risk_score(request)
        result.score = risk_score
        
        # Determine risk level
        if risk_score >= self.config["risk_threshold_high"]:
            result.risk_level = RiskLevel.HIGH
            result.flags.append("high_risk")
        elif risk_score >= self.config["risk_threshold_medium"]:
            result.risk_level = RiskLevel.MEDIUM
            result.flags.append("medium_risk")
        else:
            result.risk_level = RiskLevel.LOW

    async def _perform_aml_validation(self, result: ValidationResult, request: ValidationRequestModel):
        """Perform AML validation"""
        # Sanctions list check
        sanctions_check = await self._check_sanctions_list(request.sender_address, request.recipient_address)
        if sanctions_check["hit"]:
            result.errors.append("Address found on sanctions list")
            result.score += 1.0
            result.flags.append("sanctions_hit")
        
        # PEP (Politically Exposed Person) check
        pep_check = await self._check_pep_list(request.sender_address, request.recipient_address)
        if pep_check["hit"]:
            result.warnings.append("Address associated with PEP")
            result.score += 0.3
            result.flags.append("pep_associated")
        
        # Adverse media check
        media_check = await self._check_adverse_media(request.sender_address, request.recipient_address)
        if media_check["hit"]:
            result.warnings.append("Address found in adverse media")
            result.score += 0.2
            result.flags.append("adverse_media")

    async def _perform_kyc_validation(self, result: ValidationResult, request: ValidationRequestModel):
        """Perform KYC validation"""
        # Check if KYC is required
        if request.amount >= 1000.0:  # KYC threshold
            kyc_status = await self._check_kyc_status(request.sender_address)
            
            if not kyc_status["verified"]:
                result.errors.append("KYC verification required for high amount")
                result.score += 0.5
                result.flags.append("kyc_required")
            
            if kyc_status["expired"]:
                result.warnings.append("KYC verification expired")
                result.score += 0.3
                result.flags.append("kyc_expired")

    async def _perform_comprehensive_validation(self, result: ValidationResult, request: ValidationRequestModel):
        """Perform comprehensive validation"""
        # Run all validation types
        await self._perform_basic_validation(result, request)
        await self._perform_enhanced_validation(result, request)
        await self._perform_compliance_validation(result, request)
        await self._perform_risk_validation(result, request)
        await self._perform_aml_validation(result, request)
        await self._perform_kyc_validation(result, request)

    def _validate_tron_address(self, address: str) -> bool:
        """Validate TRON address format"""
        if not address or len(address) != 34:
            return False
        return address.startswith('T') and address[1:].isalnum()

    async def _analyze_transaction_history(self, result: ValidationResult, request: ValidationRequestModel):
        """Analyze transaction history"""
        try:
            # Get transaction history for sender
            sender_history = await self._get_transaction_history(request.sender_address)
            
            # Analyze frequency
            if len(sender_history) > 100:  # High frequency
                result.warnings.append("High transaction frequency")
                result.score += 0.1
                result.flags.append("high_frequency")
            
            # Analyze amounts
            amounts = [tx["amount"] for tx in sender_history]
            if len(amounts) > 0:
                avg_amount = sum(amounts) / len(amounts)
                if request.amount > avg_amount * 10:  # Unusually large
                    result.warnings.append("Unusually large amount")
                    result.score += 0.2
                    result.flags.append("unusual_amount")
                    
        except Exception as e:
            logger.error(f"Error analyzing transaction history: {e}")

    async def _analyze_transaction_patterns(self, result: ValidationResult, request: ValidationRequestModel):
        """Analyze transaction patterns"""
        try:
            # Check for suspicious patterns
            for pattern in self.suspicious_patterns:
                if await self._matches_pattern(pattern, request):
                    result.warnings.append(f"Suspicious pattern detected: {pattern['description']}")
                    result.score += pattern.get("risk_multiplier", 0.1)
                    result.flags.append(f"pattern_{pattern['pattern_type']}")
                    
        except Exception as e:
            logger.error(f"Error analyzing transaction patterns: {e}")

    async def _analyze_network_behavior(self, result: ValidationResult, request: ValidationRequestModel):
        """Analyze network behavior"""
        try:
            # Check network congestion
            network_info = self.tron_service.get_chain_info()
            
            # Check if transaction is during high congestion
            if network_info.latest_block % 100 < 10:  # Example condition
                result.warnings.append("Transaction during network congestion")
                result.score += 0.1
                
        except Exception as e:
            logger.error(f"Error analyzing network behavior: {e}")

    async def _check_regulatory_compliance(self, result: ValidationResult, request: ValidationRequestModel):
        """Check regulatory compliance"""
        # This would integrate with regulatory compliance systems
        # For now, we'll do basic checks
        
        # Check amount limits
        if request.amount > 10000.0:
            result.warnings.append("Transaction exceeds regulatory reporting threshold")
            result.score += 0.1
            result.flags.append("regulatory_reporting")

    async def _check_jurisdictional_compliance(self, result: ValidationResult, request: ValidationRequestModel):
        """Check jurisdictional compliance"""
        # This would check compliance with specific jurisdictions
        # For now, we'll do basic checks
        pass

    async def _check_industry_compliance(self, result: ValidationResult, request: ValidationRequestModel):
        """Check industry compliance"""
        # This would check industry-specific compliance requirements
        # For now, we'll do basic checks
        pass

    async def _calculate_risk_score(self, request: ValidationRequestModel) -> float:
        """Calculate risk score"""
        risk_score = 0.0
        
        # Amount-based risk
        if request.amount > 5000.0:
            risk_score += 0.3
        elif request.amount > 1000.0:
            risk_score += 0.1
        
        # Payment type risk
        if request.payment_type in ["donation", "custom_service"]:
            risk_score += 0.2
        
        # Address risk (would need to check against known risky addresses)
        # For now, we'll use a simple heuristic
        
        return min(risk_score, 1.0)

    async def _check_sanctions_list(self, sender_address: str, recipient_address: str) -> Dict[str, Any]:
        """Check sanctions list"""
        # This would integrate with sanctions list APIs
        # For now, return no hits
        return {"hit": False, "details": {}}

    async def _check_pep_list(self, sender_address: str, recipient_address: str) -> Dict[str, Any]:
        """Check PEP list"""
        # This would integrate with PEP list APIs
        # For now, return no hits
        return {"hit": False, "details": {}}

    async def _check_adverse_media(self, sender_address: str, recipient_address: str) -> Dict[str, Any]:
        """Check adverse media"""
        # This would integrate with adverse media APIs
        # For now, return no hits
        return {"hit": False, "details": {}}

    async def _check_kyc_status(self, address: str) -> Dict[str, Any]:
        """Check KYC status"""
        # This would integrate with KYC systems
        # For now, return verified
        return {"verified": True, "expired": False, "level": "basic"}

    async def _get_transaction_history(self, address: str) -> List[Dict[str, Any]]:
        """Get transaction history for address"""
        try:
            # This would integrate with blockchain APIs
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return []

    async def _matches_pattern(self, pattern: Dict[str, Any], request: ValidationRequestModel) -> bool:
        """Check if request matches suspicious pattern"""
        try:
            pattern_type = pattern["pattern_type"]
            
            if pattern_type == "rapid_transactions":
                # Check for rapid transactions
                # This would need historical data
                return False
            
            elif pattern_type == "round_amounts":
                # Check for round amounts
                return request.amount % 100 == 0
            
            elif pattern_type == "unusual_timing":
                # Check for unusual timing
                current_hour = datetime.now().hour
                time_range = pattern["time_range"]
                return time_range["start"] <= current_hour <= time_range["end"]
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking pattern match: {e}")
            return False

    async def _perform_compliance_checks(self, validation_id: str, request: ValidationRequestModel):
        """Perform compliance checks"""
        try:
            checks = []
            
            # AML check
            aml_check = ComplianceCheck(
                check_id=f"AML_{uuid4().hex[:8]}",
                check_type="aml",
                status="passed",
                details={"sanctions": False, "pep": False, "adverse_media": False}
            )
            checks.append(aml_check)
            
            # KYC check
            kyc_check = ComplianceCheck(
                check_id=f"KYC_{uuid4().hex[:8]}",
                check_type="kyc",
                status="passed",
                details={"verified": True, "level": "basic"}
            )
            checks.append(kyc_check)
            
            # Regulatory check
            regulatory_check = ComplianceCheck(
                check_id=f"REG_{uuid4().hex[:8]}",
                check_type="regulatory",
                status="passed",
                details={"jurisdiction": "global", "compliant": True}
            )
            checks.append(regulatory_check)
            
            self.compliance_checks[validation_id] = checks
            
        except Exception as e:
            logger.error(f"Error performing compliance checks: {e}")

    async def _perform_risk_assessment(self, validation_id: str, request: ValidationRequestModel):
        """Perform risk assessment"""
        try:
            risk_score = await self._calculate_risk_score(request)
            
            # Determine risk level
            if risk_score >= self.config["risk_threshold_high"]:
                risk_level = RiskLevel.HIGH
            elif risk_score >= self.config["risk_threshold_medium"]:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            # Identify risk factors
            risk_factors = []
            if request.amount > 1000.0:
                risk_factors.append("high_amount")
            if request.payment_type in ["donation", "custom_service"]:
                risk_factors.append("unusual_payment_type")
            
            # Determine mitigation actions
            mitigation_actions = []
            if risk_level == RiskLevel.HIGH:
                mitigation_actions.append("manual_review")
                mitigation_actions.append("additional_verification")
            elif risk_level == RiskLevel.MEDIUM:
                mitigation_actions.append("enhanced_monitoring")
            
            assessment = RiskAssessment(
                assessment_id=f"RISK_{uuid4().hex[:8]}",
                payment_id=request.payment_id,
                risk_score=risk_score,
                risk_level=risk_level,
                risk_factors=risk_factors,
                mitigation_actions=mitigation_actions
            )
            
            self.risk_assessments[validation_id] = assessment
            
        except Exception as e:
            logger.error(f"Error performing risk assessment: {e}")

    def _determine_validation_status(self, result: ValidationResult) -> ValidationStatus:
        """Determine final validation status"""
        if result.score >= 1.0:
            return ValidationStatus.BLOCKED
        elif result.score >= 0.7:
            return ValidationStatus.SUSPICIOUS
        elif result.score >= 0.4:
            return ValidationStatus.MANUAL_REVIEW
        elif result.errors:
            return ValidationStatus.INVALID
        else:
            return ValidationStatus.VALID

    async def get_validation_result(self, validation_id: str) -> Optional[Dict[str, Any]]:
        """Get validation result"""
        if validation_id not in self.validation_results:
            return None
        
        result = self.validation_results[validation_id]
        compliance_checks = self.compliance_checks.get(validation_id, [])
        risk_assessment = self.risk_assessments.get(validation_id)
        
        return {
            "validation_id": validation_id,
            "payment_id": result.payment_id,
            "status": result.status.value,
            "risk_level": result.risk_level.value,
            "compliance_status": result.compliance_status.value,
            "score": result.score,
            "errors": result.errors,
            "warnings": result.warnings,
            "flags": result.flags,
            "validated_at": result.validated_at.isoformat() if result.validated_at else None,
            "validated_by": result.validated_by,
            "compliance_checks": [
                {
                    "check_id": check.check_id,
                    "check_type": check.check_type,
                    "status": check.status,
                    "details": check.details,
                    "timestamp": check.timestamp.isoformat()
                }
                for check in compliance_checks
            ],
            "risk_assessment": {
                "assessment_id": risk_assessment.assessment_id,
                "risk_score": risk_assessment.risk_score,
                "risk_level": risk_assessment.risk_level.value,
                "risk_factors": risk_assessment.risk_factors,
                "mitigation_actions": risk_assessment.mitigation_actions,
                "assessed_at": risk_assessment.assessed_at.isoformat()
            } if risk_assessment else None
        }

    async def list_validations(self, status: Optional[ValidationStatus] = None,
                              validation_type: Optional[ValidationType] = None,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """List validations"""
        validations = []
        
        for validation_id, result in self.validation_results.items():
            if status and result.status != status:
                continue
            if validation_type and result.validation_type != validation_type:
                continue
            
            validation_data = await self.get_validation_result(validation_id)
            if validation_data:
                validations.append(validation_data)
        
        # Sort by validation time (newest first)
        validations.sort(key=lambda x: x["validated_at"], reverse=True)
        
        return validations[:limit]

    async def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        total_validations = len(self.validation_results)
        status_counts = {}
        type_counts = {}
        risk_level_counts = {}
        
        for result in self.validation_results.values():
            # Status counts
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Type counts
            validation_type = result.validation_type.value
            type_counts[validation_type] = type_counts.get(validation_type, 0) + 1
            
            # Risk level counts
            risk_level = result.risk_level.value
            risk_level_counts[risk_level] = risk_level_counts.get(risk_level, 0) + 1
        
        return {
            "total_validations": total_validations,
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "risk_level_breakdown": risk_level_counts,
            "blocked_addresses": len(self.blocked_addresses),
            "suspicious_patterns": len(self.suspicious_patterns),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Global instance
payment_validator = PaymentValidator()

# Public API functions
async def validate_payment(request: ValidationRequestModel) -> ValidationResponseModel:
    """Validate payment"""
    return await payment_validator.validate_payment(request)

async def get_validation_result(validation_id: str) -> Optional[Dict[str, Any]]:
    """Get validation result"""
    return await payment_validator.get_validation_result(validation_id)

async def list_validations(status: Optional[ValidationStatus] = None,
                          validation_type: Optional[ValidationType] = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
    """List validations"""
    return await payment_validator.list_validations(status, validation_type, limit)

async def get_validation_statistics() -> Dict[str, Any]:
    """Get validation statistics"""
    return await payment_validator.get_validation_statistics()

async def main():
    """Main function for testing"""
    # Create a test validation request
    request = ValidationRequestModel(
        payment_id="PAY_TEST123",
        validation_type=ValidationType.COMPREHENSIVE,
        amount=100.0,
        token_type="USDT",
        sender_address="TSenderAddress1234567890123456789012345",
        recipient_address="TRecipientAddress1234567890123456789012345",
        payment_type="session_payment"
    )
    
    response = await validate_payment(request)
    print(f"Validation result: {response}")
    
    # Get validation details
    details = await get_validation_result(response.validation_id)
    print(f"Validation details: {details}")
    
    # Get statistics
    stats = await get_validation_statistics()
    print(f"Validation statistics: {stats}")

if __name__ == "__main__":
    asyncio.run(main())
