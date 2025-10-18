#!/usr/bin/env python3
"""
TRON Isolation Verification Script
Verifies that TRON payment system is completely isolated from blockchain core
Part of Step 28: TRON Isolation Verification

This script performs comprehensive analysis of the codebase to ensure:
1. No TRON references in blockchain/core/ directory
2. All TRON code is properly contained in payment-systems/ directory
3. Network isolation is properly configured
4. Directory structure follows isolation requirements
"""

import os
import sys
import json
import re
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tron-isolation-verification.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class VerificationStatus(Enum):
    """Verification status enumeration"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"

@dataclass
class Violation:
    """Represents a TRON isolation violation"""
    file_path: str
    line_number: int
    line_content: str
    violation_type: str
    severity: str
    keyword: str

@dataclass
class VerificationResult:
    """Result of a verification check"""
    status: VerificationStatus
    message: str
    violations: List[Violation]
    files_scanned: int
    details: Dict[str, Any]

class TRONIsolationVerifier:
    """Main TRON isolation verification class"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.blockchain_dir = self.project_root / "blockchain"
        self.payment_systems_dir = self.project_root / "payment-systems"
        self.reports_dir = self.project_root / "reports" / "verification"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # TRON-related keywords to search for
        self.tron_keywords = [
            "tron", "TRON", "TronNode", "TronClient", "tron_client",
            "tron-node", "tron-client", "usdt", "USDT", "TRX", "trx",
            "tron_payment", "TronPayment", "tron_payout", "TronPayout",
            "tron_wallet", "TronWallet", "tron_network", "TronNetwork"
        ]
        
        # File extensions to scan
        self.scan_extensions = [".py", ".js", ".ts", ".yml", ".yaml", ".json", ".toml", ".md"]
        
        # Initialize results
        self.results = {
            "blockchain_core_scan": VerificationResult(
                status=VerificationStatus.PENDING,
                message="Blockchain core scan not started",
                violations=[],
                files_scanned=0,
                details={}
            ),
            "payment_systems_scan": VerificationResult(
                status=VerificationStatus.PENDING,
                message="Payment systems scan not started",
                violations=[],
                files_scanned=0,
                details={}
            ),
            "network_isolation": VerificationResult(
                status=VerificationStatus.PENDING,
                message="Network isolation check not started",
                violations=[],
                files_scanned=0,
                details={}
            ),
            "directory_structure": VerificationResult(
                status=VerificationStatus.PENDING,
                message="Directory structure check not started",
                violations=[],
                files_scanned=0,
                details={}
            )
        }
    
    def scan_blockchain_core(self) -> VerificationResult:
        """Scan blockchain core directory for TRON references"""
        logger.info("Scanning blockchain core directory for TRON references...")
        
        violations = []
        files_scanned = 0
        
        if not self.blockchain_dir.exists():
            logger.error(f"Blockchain directory not found: {self.blockchain_dir}")
            return VerificationResult(
                status=VerificationStatus.FAILED,
                message="Blockchain directory not found",
                violations=[],
                files_scanned=0,
                details={"error": "Directory not found"}
            )
        
        # Scan all relevant files in blockchain directory
        for file_path in self.blockchain_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in self.scan_extensions:
                files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                        for line_num, line in enumerate(lines, 1):
                            for keyword in self.tron_keywords:
                                if re.search(rf'\b{re.escape(keyword)}\b', line, re.IGNORECASE):
                                    violation = Violation(
                                        file_path=str(file_path.relative_to(self.project_root)),
                                        line_number=line_num,
                                        line_content=line.strip(),
                                        violation_type="TRON_REFERENCE_IN_BLOCKCHAIN_CORE",
                                        severity="HIGH",
                                        keyword=keyword
                                    )
                                    violations.append(violation)
                                    logger.warning(f"TRON reference found in blockchain core: {file_path}:{line_num}")
                
                except Exception as e:
                    logger.warning(f"Error scanning file {file_path}: {e}")
        
        status = VerificationStatus.PASSED if len(violations) == 0 else VerificationStatus.FAILED
        
        result = VerificationResult(
            status=status,
            message=f"Found {len(violations)} TRON violations in blockchain core" if violations else "No TRON references found in blockchain core",
            violations=violations,
            files_scanned=files_scanned,
            details={"violation_count": len(violations)}
        )
        
        self.results["blockchain_core_scan"] = result
        return result
    
    def scan_payment_systems(self) -> VerificationResult:
        """Scan payment systems directory for TRON files"""
        logger.info("Scanning payment systems directory for TRON files...")
        
        tron_files = []
        files_scanned = 0
        
        if not self.payment_systems_dir.exists():
            logger.error(f"Payment systems directory not found: {self.payment_systems_dir}")
            return VerificationResult(
                status=VerificationStatus.FAILED,
                message="Payment systems directory not found",
                violations=[],
                files_scanned=0,
                details={"error": "Directory not found"}
            )
        
        # Find all TRON-related files
        for file_path in self.payment_systems_dir.rglob("*"):
            if file_path.is_file():
                files_scanned += 1
                
                # Check if filename contains TRON-related keywords
                filename = file_path.name.lower()
                if any(keyword.lower() in filename for keyword in self.tron_keywords):
                    tron_files.append(str(file_path.relative_to(self.project_root)))
                    logger.info(f"Found TRON file: {file_path}")
        
        # Also scan content for TRON references
        tron_content_files = []
        for file_path in self.payment_systems_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in self.scan_extensions:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if any(keyword.lower() in content.lower() for keyword in self.tron_keywords):
                            tron_content_files.append(str(file_path.relative_to(self.project_root)))
                except Exception as e:
                    logger.warning(f"Error scanning file {file_path}: {e}")
        
        all_tron_files = list(set(tron_files + tron_content_files))
        
        status = VerificationStatus.PASSED if len(all_tron_files) > 0 else VerificationStatus.WARNING
        
        result = VerificationResult(
            status=status,
            message=f"Found {len(all_tron_files)} TRON files in payment systems" if all_tron_files else "No TRON files found in payment systems",
            violations=[],
            files_scanned=files_scanned,
            details={
                "tron_files": all_tron_files,
                "tron_file_count": len(all_tron_files)
            }
        )
        
        self.results["payment_systems_scan"] = result
        return result
    
    def verify_network_isolation(self) -> VerificationResult:
        """Verify network isolation configuration"""
        logger.info("Verifying network isolation...")
        
        network_checks = []
        violations = []
        
        try:
            # Check Docker networks
            result = subprocess.run(['docker', 'network', 'ls'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                networks = result.stdout
                
                # Check for lucid-dev network (main network)
                if 'lucid-dev' in networks:
                    network_checks.append("✓ lucid-dev network exists")
                    logger.info("lucid-dev network found")
                else:
                    network_checks.append("✗ lucid-dev network missing")
                    violations.append(Violation(
                        file_path="docker_networks",
                        line_number=0,
                        line_content="lucid-dev network not found",
                        violation_type="MISSING_MAIN_NETWORK",
                        severity="MEDIUM",
                        keyword="lucid-dev"
                    ))
                
                # Check for lucid-network-isolated network (TRON isolation)
                if 'lucid-network-isolated' in networks:
                    network_checks.append("✓ lucid-network-isolated network exists")
                    logger.info("lucid-network-isolated network found")
                else:
                    network_checks.append("✗ lucid-network-isolated network missing")
                    violations.append(Violation(
                        file_path="docker_networks",
                        line_number=0,
                        line_content="lucid-network-isolated network not found",
                        violation_type="MISSING_ISOLATED_NETWORK",
                        severity="HIGH",
                        keyword="lucid-network-isolated"
                    ))
            else:
                network_checks.append("Docker not available for network verification")
                logger.warning("Docker not available")
        
        except subprocess.TimeoutExpired:
            network_checks.append("Docker command timed out")
            logger.warning("Docker command timed out")
        except Exception as e:
            network_checks.append(f"Docker error: {e}")
            logger.warning(f"Docker error: {e}")
        
        # Check for network configuration files
        network_config_files = [
            "configs/docker/docker-compose.all.yml",
            "configs/docker/docker-compose.foundation.yml",
            "configs/docker/docker-compose.core.yml",
            "configs/docker/docker-compose.application.yml",
            "configs/docker/docker-compose.support.yml"
        ]
        
        for config_file in network_config_files:
            config_path = self.project_root / config_file
            if config_path.exists():
                network_checks.append(f"✓ {config_file} exists")
            else:
                network_checks.append(f"✗ {config_file} missing")
        
        status = VerificationStatus.PASSED if len(violations) == 0 else VerificationStatus.FAILED
        
        result = VerificationResult(
            status=status,
            message=f"Network isolation check completed with {len(violations)} violations",
            violations=violations,
            files_scanned=len(network_config_files),
            details={"network_checks": network_checks}
        )
        
        self.results["network_isolation"] = result
        return result
    
    def verify_directory_structure(self) -> VerificationResult:
        """Verify directory structure compliance"""
        logger.info("Verifying directory structure compliance...")
        
        compliance_checks = []
        violations = []
        
        # Required directories for proper isolation
        required_dirs = [
            "blockchain/core",
            "blockchain/api",
            "payment-systems/tron",
            "payment-systems/tron/services",
            "payment-systems/tron/api",
            "payment-systems/tron/models"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                compliance_checks.append(f"✓ {dir_path} exists")
                logger.info(f"Directory exists: {dir_path}")
            else:
                compliance_checks.append(f"✗ {dir_path} missing")
                violations.append(Violation(
                    file_path=dir_path,
                    line_number=0,
                    line_content=f"Required directory missing: {dir_path}",
                    violation_type="MISSING_REQUIRED_DIRECTORY",
                    severity="HIGH",
                    keyword=dir_path
                ))
                logger.error(f"Directory missing: {dir_path}")
        
        # Check for forbidden TRON files in blockchain directory
        forbidden_files = []
        for file_path in self.blockchain_dir.rglob("*"):
            if file_path.is_file():
                filename = file_path.name.lower()
                if any(keyword.lower() in filename for keyword in self.tron_keywords):
                    forbidden_files.append(str(file_path.relative_to(self.project_root)))
                    violations.append(Violation(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=0,
                        line_content=f"Forbidden TRON file in blockchain directory: {file_path.name}",
                        violation_type="FORBIDDEN_TRON_FILE_IN_BLOCKCHAIN",
                        severity="HIGH",
                        keyword=file_path.name
                    ))
        
        if forbidden_files:
            compliance_checks.append(f"✗ TRON files found in blockchain directory: {forbidden_files}")
            logger.error(f"TRON files found in blockchain directory: {forbidden_files}")
        else:
            compliance_checks.append("✓ No TRON files in blockchain directory")
            logger.info("No TRON files in blockchain directory")
        
        status = VerificationStatus.PASSED if len(violations) == 0 else VerificationStatus.FAILED
        
        result = VerificationResult(
            status=status,
            message=f"Directory structure check completed with {len(violations)} violations",
            violations=violations,
            files_scanned=len(required_dirs),
            details={"compliance_checks": compliance_checks}
        )
        
        self.results["directory_structure"] = result
        return result
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive verification report"""
        logger.info("Generating verification report...")
        
        # Calculate summary statistics
        total_violations = sum(len(result.violations) for result in self.results.values())
        passed_checks = sum(1 for result in self.results.values() if result.status == VerificationStatus.PASSED)
        total_checks = len(self.results)
        compliance_score = (passed_checks * 100) // total_checks if total_checks > 0 else 0
        isolation_verified = total_violations == 0 and compliance_score >= 75
        
        # Create report
        report = {
            "verification_timestamp": datetime.utcnow().isoformat() + "Z",
            "project_root": str(self.project_root),
            "verification_results": {
                key: {
                    "status": result.status.value,
                    "message": result.message,
                    "violations": [asdict(v) for v in result.violations],
                    "files_scanned": result.files_scanned,
                    "details": result.details
                }
                for key, result in self.results.items()
            },
            "summary": {
                "total_violations": total_violations,
                "isolation_verified": isolation_verified,
                "compliance_score": compliance_score,
                "passed_checks": passed_checks,
                "total_checks": total_checks
            }
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any]) -> str:
        """Save verification report to file"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_file = self.reports_dir / f"tron-isolation-report-{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to: {report_file}")
        return str(report_file)
    
    def run_verification(self) -> bool:
        """Run complete TRON isolation verification"""
        logger.info("=== TRON ISOLATION VERIFICATION ===")
        logger.info("Step 28: TRON Isolation Verification")
        logger.info("=====================================")
        
        # Run all verification steps
        self.scan_blockchain_core()
        self.scan_payment_systems()
        self.verify_network_isolation()
        self.verify_directory_structure()
        
        # Generate and save report
        report = self.generate_report()
        report_file = self.save_report(report)
        
        # Print summary
        logger.info("=== TRON ISOLATION VERIFICATION SUMMARY ===")
        logger.info(f"Total Violations: {report['summary']['total_violations']}")
        logger.info(f"Compliance Score: {report['summary']['compliance_score']}%")
        logger.info(f"Isolation Verified: {report['summary']['isolation_verified']}")
        logger.info(f"Passed Checks: {report['summary']['passed_checks']}/{report['summary']['total_checks']}")
        
        if report['summary']['isolation_verified']:
            logger.info("✓ TRON isolation verification PASSED")
            return True
        else:
            logger.error("✗ TRON isolation verification FAILED")
            return False

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()
    
    verifier = TRONIsolationVerifier(project_root)
    success = verifier.run_verification()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
