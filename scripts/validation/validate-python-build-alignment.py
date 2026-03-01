#!/usr/bin/env python3
"""
LUCID Python Files Build Alignment Validator

This script validates all Python files against the lucid-container-build-plan.plan.md
and API_plans directory requirements. It performs comprehensive checks for:
- Distroless compliance
- TRON isolation
- Docker build requirements
- API specification alignment
- Security compliance
- Performance requirements

Usage:
    python scripts/validation/validate-python-build-alignment.py [--verbose] [--fix]

Author: LUCID Project Team
Version: 1.0.0
"""

import os
import sys
import re
import json
import ast
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    INFO = "INFO"

@dataclass
class ValidationResult:
    file_path: str
    status: ValidationStatus
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class BuildRequirements:
    """Build requirements from lucid-container-build-plan.plan.md"""
    distroless_required: bool = True
    tron_isolation_required: bool = True
    docker_build_required: bool = True
    security_compliance: bool = True
    performance_requirements: bool = True

class PythonBuildValidator:
    """Main validator class for Python files build alignment"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.results: List[ValidationResult] = []
        self.python_files: List[Path] = []
        self.build_requirements = BuildRequirements()
        
        # TRON isolation patterns
        self.tron_patterns = [
            r'import.*tron',
            r'from.*tron',
            r'TronWeb',
            r'tronpy',
            r'tronapi',
            r'TRON',
            r'TRX',
            r'USDT.*TRC20'
        ]
        
        # Distroless compliance patterns
        self.distroless_patterns = [
            r'subprocess\.run',
            r'os\.system',
            r'os\.popen',
            r'shell=True',
            r'bash',
            r'sh -c'
        ]
        
        # Security compliance patterns
        self.security_patterns = [
            r'eval\(',
            r'exec\(',
            r'__import__\(',
            r'compile\(',
            r'getattr\(',
            r'setattr\(',
            r'hasattr\(',
            r'delattr\('
        ]
        
        # Performance anti-patterns
        self.performance_patterns = [
            r'while\s+True:',
            r'for\s+.*\s+in\s+range\(1000000\)',
            r'time\.sleep\(0\)',
            r'\.join\(\)\s*$'
        ]

    def discover_python_files(self) -> List[Path]:
        """Discover all Python files in the project"""
        python_files = []
        
        # Directories to scan based on build plan
        scan_dirs = [
            'auth',
            'blockchain', 
            'sessions',
            'RDP',
            'node',
            'admin',
            'payment-systems',
            '03-api-gateway',
            'database',
            'common',
            'core',
            'apps',
            'gui',
            'user_content',
            'vm',
            'wallet'
        ]
        
        for scan_dir in scan_dirs:
            dir_path = self.project_root / scan_dir
            if dir_path.exists():
                for py_file in dir_path.rglob("*.py"):
                    # Skip __pycache__ and test files for main validation
                    if "__pycache__" not in str(py_file) and "test_" not in py_file.name:
                        python_files.append(py_file)
        
        logger.info(f"Discovered {len(python_files)} Python files to validate")
        return python_files

    def validate_tron_isolation(self, file_path: Path, content: str) -> List[ValidationResult]:
        """Validate TRON isolation requirements"""
        results = []
        
        # Check if file is in blockchain core (should not have TRON)
        if "blockchain" in str(file_path) and "payment" not in str(file_path):
            for pattern in self.tron_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    results.append(ValidationResult(
                        file_path=str(file_path),
                        status=ValidationStatus.FAIL,
                        message=f"TRON reference found in blockchain core: {match.group()}",
                        line_number=line_num,
                        suggestion="Move TRON code to payment-systems/tron/ directory"
                    ))
        
        # Check if TRON code is properly isolated
        if "payment-systems/tron" in str(file_path):
            # This is expected to have TRON code
            pass
        elif any(pattern in content.lower() for pattern in ['tron', 'trx', 'usdt']):
            # Check if it's a legitimate reference or should be moved
            results.append(ValidationResult(
                file_path=str(file_path),
                status=ValidationStatus.WARNING,
                message="TRON reference found outside payment-systems/tron/",
                suggestion="Verify if this should be moved to payment-systems/tron/"
            ))
        
        return results

    def validate_distroless_compliance(self, file_path: Path, content: str) -> List[ValidationResult]:
        """Validate distroless compliance"""
        results = []
        
        for pattern in self.distroless_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.FAIL,
                    message=f"Non-distroless pattern found: {match.group()}",
                    line_number=line_num,
                    suggestion="Use distroless-compatible alternatives"
                ))
        
        return results

    def validate_security_compliance(self, file_path: Path, content: str) -> List[ValidationResult]:
        """Validate security compliance"""
        results = []
        
        for pattern in self.security_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message=f"Potentially unsafe pattern: {match.group()}",
                    line_number=line_num,
                    suggestion="Review for security implications"
                ))
        
        return results

    def validate_performance_requirements(self, file_path: Path, content: str) -> List[ValidationResult]:
        """Validate performance requirements"""
        results = []
        
        for pattern in self.performance_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message=f"Potential performance issue: {match.group()}",
                    line_number=line_num,
                    suggestion="Consider optimization"
                ))
        
        return results

    def validate_docker_requirements(self, file_path: Path) -> List[ValidationResult]:
        """Validate Docker build requirements"""
        results = []
        
        # Check if Dockerfile exists for the service
        service_dir = file_path.parent
        dockerfile_path = service_dir / "Dockerfile"
        
        if not dockerfile_path.exists():
            results.append(ValidationResult(
                file_path=str(file_path),
                status=ValidationStatus.FAIL,
                message="No Dockerfile found for service",
                suggestion="Create Dockerfile with distroless base"
            ))
        else:
            # Validate Dockerfile content
            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_content = f.read()
                
                if "gcr.io/distroless" not in dockerfile_content:
                    results.append(ValidationResult(
                        file_path=str(dockerfile_path),
                        status=ValidationStatus.FAIL,
                        message="Dockerfile not using distroless base",
                        suggestion="Use gcr.io/distroless/python3-debian12:arm64"
                    ))
                
                if "USER nonroot" not in dockerfile_content:
                    results.append(ValidationResult(
                        file_path=str(dockerfile_path),
                        status=ValidationStatus.WARNING,
                        message="Dockerfile not using nonroot user",
                        suggestion="Add USER nonroot for security"
                    ))
                    
            except Exception as e:
                results.append(ValidationResult(
                    file_path=str(dockerfile_path),
                    status=ValidationStatus.FAIL,
                    message=f"Error reading Dockerfile: {str(e)}",
                    suggestion="Check Dockerfile syntax"
                ))
        
        return results

    def validate_api_specification_alignment(self, file_path: Path, content: str) -> List[ValidationResult]:
        """Validate API specification alignment"""
        results = []
        
        # Check for FastAPI usage
        if "fastapi" in content.lower() or "FastAPI" in content:
            # Validate FastAPI best practices
            if "from fastapi import" not in content:
                results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message="FastAPI import not found",
                    suggestion="Use proper FastAPI imports"
                ))
            
            # Check for proper error handling
            if "HTTPException" not in content and "raise" in content:
                results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message="Consider using HTTPException for API errors",
                    suggestion="Import and use HTTPException from fastapi"
                ))
        
        return results

    def validate_requirements_txt(self, file_path: Path) -> List[ValidationResult]:
        """Validate requirements.txt file"""
        results = []
        
        requirements_file = file_path.parent / "requirements.txt"
        if requirements_file.exists():
            try:
                with open(requirements_file, 'r') as f:
                    requirements = f.read()
                
                # Check for security vulnerabilities
                vulnerable_packages = [
                    'requests<2.25.0',
                    'urllib3<1.26.0',
                    'pyyaml<5.4'
                ]
                
                for vuln_pkg in vulnerable_packages:
                    if vuln_pkg.split('<')[0] in requirements:
                        results.append(ValidationResult(
                            file_path=str(requirements_file),
                            status=ValidationStatus.WARNING,
                            message=f"Potentially vulnerable package: {vuln_pkg.split('<')[0]}",
                            suggestion=f"Update to {vuln_pkg}"
                        ))
                        
            except Exception as e:
                results.append(ValidationResult(
                    file_path=str(requirements_file),
                    status=ValidationStatus.FAIL,
                    message=f"Error reading requirements.txt: {str(e)}",
                    suggestion="Check file format"
                ))
        
        return results

    def validate_file(self, file_path: Path) -> List[ValidationResult]:
        """Validate a single Python file"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            results.append(ValidationResult(
                file_path=str(file_path),
                status=ValidationStatus.FAIL,
                message=f"Error reading file: {str(e)}",
                suggestion="Check file encoding and permissions"
            ))
            return results
        
        # Run all validations
        results.extend(self.validate_tron_isolation(file_path, content))
        results.extend(self.validate_distroless_compliance(file_path, content))
        results.extend(self.validate_security_compliance(file_path, content))
        results.extend(self.validate_performance_requirements(file_path, content))
        results.extend(self.validate_docker_requirements(file_path))
        results.extend(self.validate_api_specification_alignment(file_path, content))
        results.extend(self.validate_requirements_txt(file_path))
        
        return results

    def generate_report(self) -> Dict[str, Any]:
        """Generate validation report"""
        total_files = len(self.python_files)
        total_results = len(self.results)
        
        status_counts = {
            "PASS": 0,
            "FAIL": 0,
            "WARNING": 0,
            "INFO": 0
        }
        
        for result in self.results:
            status_counts[result.status.value] += 1
        
        # Group results by file
        file_results = {}
        for result in self.results:
            if result.file_path not in file_results:
                file_results[result.file_path] = []
            file_results[result.file_path].append(result)
        
        return {
            "summary": {
                "total_files": total_files,
                "total_issues": total_results,
                "status_counts": status_counts,
                "pass_rate": (status_counts["PASS"] / total_results * 100) if total_results > 0 else 100
            },
            "file_results": file_results,
            "detailed_results": self.results
        }

    def run_validation(self) -> bool:
        """Run complete validation"""
        logger.info("Starting Python files build alignment validation...")
        
        # Discover Python files
        self.python_files = self.discover_python_files()
        
        if not self.python_files:
            logger.warning("No Python files found to validate")
            return False
        
        # Validate each file
        for file_path in self.python_files:
            logger.info(f"Validating: {file_path}")
            file_results = self.validate_file(file_path)
            self.results.extend(file_results)
        
        # Generate report
        report = self.generate_report()
        
        # Print summary
        print("\n" + "="*80)
        print("LUCID PYTHON BUILD ALIGNMENT VALIDATION REPORT")
        print("="*80)
        print(f"Total files validated: {report['summary']['total_files']}")
        print(f"Total issues found: {report['summary']['total_issues']}")
        print(f"Pass rate: {report['summary']['pass_rate']:.1f}%")
        print("\nStatus breakdown:")
        for status, count in report['summary']['status_counts'].items():
            print(f"  {status}: {count}")
        
        # Print detailed results
        print("\nDetailed Results:")
        print("-" * 80)
        
        for file_path, file_results in report['file_results'].items():
            if file_results:
                print(f"\nFile: {file_path}")
                for result in file_results:
                    # Use ASCII-safe status icons for Windows console compatibility
                    status_icon = {
                        "PASS": "[OK]",
                        "FAIL": "[X]", 
                        "WARNING": "[!]",
                        "INFO": "[i]"
                    }[result.status.value]
                    
                    print(f"  {status_icon} {result.status.value}: {result.message}")
                    if result.line_number:
                        print(f"    Line {result.line_number}")
                    if result.suggestion:
                        print(f"    Suggestion: {result.suggestion}")
        
        # Return success if no failures
        return report['summary']['status_counts']['FAIL'] == 0

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Validate Python files build alignment")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fix", "-f", action="store_true", help="Attempt to fix issues")
    parser.add_argument("--project-root", "-p", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run validation
    validator = PythonBuildValidator(args.project_root)
    success = validator.run_validation()
    
    if success:
        logger.info("[OK] All validations passed!")
        sys.exit(0)
    else:
        logger.error("[X] Some validations failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
