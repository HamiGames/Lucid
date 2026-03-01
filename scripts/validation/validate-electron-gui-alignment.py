#!/usr/bin/env python3
"""
LUCID Electron GUI Alignment Validator

This script validates the electron-gui directory structure and files against
the build plan requirements. It performs comprehensive checks for:
- File structure alignment
- TypeScript/React component validation
- API integration alignment
- Configuration file validation
- Build system alignment
- Security compliance

Usage:
    python scripts/validation/validate-electron-gui-alignment.py [--verbose] [--fix]

Author: LUCID Project Team
Version: 1.0.0
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
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

class ElectronGUIValidator:
    """Main validator class for Electron GUI alignment"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.electron_gui_path = self.project_root / "electron-gui"
        self.results: List[ValidationResult] = []
        
        # Expected file structure based on build plan
        self.expected_structure = {
            "main/": [
                "index.ts",
                "tor-manager.ts", 
                "docker-manager.ts",
                "window-manager.ts",
                "preload.ts"
            ],
            "renderer/": [
                "admin/",
                "developer/", 
                "node/",
                "user/"
            ],
            "shared/": [
                "api-client.ts",
                "constants.ts",
                "ipc-channels.ts",
                "tor-types.ts",
                "types.ts",
                "utils.ts"
            ],
            "configs/": [
                "docker.config.json",
                "env.development.json", 
                "env.production.json",
                "tor.config.json"
            ]
        }
        
        # Required GUI components
        self.required_components = {
            "admin": [
                "App.tsx",
                "components/",
                "pages/",
                "services/",
                "store/"
            ],
            "developer": [
                "App.tsx",
                "components/",
                "pages/",
                "services/"
            ],
            "node": [
                "App.tsx", 
                "components/",
                "pages/",
                "services/"
            ],
            "user": [
                "App.tsx",
                "components/",
                "pages/",
                "services/"
            ]
        }
        
        # API endpoint patterns
        self.api_endpoints = [
            "API_GATEWAY_URL",
            "BLOCKCHAIN_CORE_URL", 
            "AUTH_SERVICE_URL",
            "SESSION_API_URL",
            "NODE_MANAGEMENT_URL",
            "ADMIN_INTERFACE_URL",
            "TRON_PAYMENT_URL"
        ]
        
        # Security patterns
        self.security_patterns = [
            r'eval\(',
            r'innerHTML',
            r'dangerouslySetInnerHTML',
            r'localStorage\.setItem',
            r'sessionStorage\.setItem'
        ]

    def validate_file_structure(self) -> List[ValidationResult]:
        """Validate electron-gui file structure"""
        results = []
        
        if not self.electron_gui_path.exists():
            results.append(ValidationResult(
                file_path="electron-gui/",
                status=ValidationStatus.FAIL,
                message="electron-gui directory not found",
                suggestion="Create electron-gui directory structure"
            ))
            return results
        
        # Check main directory structure
        for dir_path, expected_files in self.expected_structure.items():
            full_path = self.electron_gui_path / dir_path
            if not full_path.exists():
                results.append(ValidationResult(
                    file_path=str(full_path),
                    status=ValidationStatus.FAIL,
                    message=f"Required directory missing: {dir_path}",
                    suggestion=f"Create directory: {dir_path}"
                ))
            else:
                # Check for expected files
                for expected_file in expected_files:
                    file_path = full_path / expected_file
                    if not file_path.exists():
                        results.append(ValidationResult(
                            file_path=str(file_path),
                            status=ValidationStatus.FAIL,
                            message=f"Required file missing: {expected_file}",
                            suggestion=f"Create file: {file_path}"
                        ))
        
        # Check renderer structure
        renderer_path = self.electron_gui_path / "renderer"
        if renderer_path.exists():
            for gui_type, components in self.required_components.items():
                gui_path = renderer_path / gui_type
                if not gui_path.exists():
                    results.append(ValidationResult(
                        file_path=str(gui_path),
                        status=ValidationStatus.FAIL,
                        message=f"GUI type missing: {gui_type}",
                        suggestion=f"Create GUI directory: {gui_path}"
                    ))
                else:
                    for component in components:
                        comp_path = gui_path / component
                        if not comp_path.exists():
                            results.append(ValidationResult(
                                file_path=str(comp_path),
                                status=ValidationStatus.FAIL,
                                message=f"Component missing: {component}",
                                suggestion=f"Create component: {comp_path}"
                            ))
        
        return results

    def validate_typescript_files(self, file_path: Path) -> List[ValidationResult]:
        """Validate TypeScript files"""
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
        
        # Check for proper imports
        if file_path.suffix == '.tsx' or file_path.suffix == '.ts':
            # Check for React imports in TSX files
            if file_path.suffix == '.tsx' and 'import React' not in content:
                results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message="Missing React import in TSX file",
                    suggestion="Add 'import React from \"react\"'"
                ))
            
            # Check for proper TypeScript types
            if 'any' in content and 'any[]' not in content:
                any_count = content.count('any')
                if any_count > 3:
                    results.append(ValidationResult(
                        file_path=str(file_path),
                        status=ValidationStatus.WARNING,
                        message=f"Multiple 'any' types found ({any_count})",
                        suggestion="Use specific types instead of 'any'"
                    ))
            
            # Check for proper error handling
            if 'try' in content and 'catch' not in content:
                results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message="Try block without catch",
                    suggestion="Add proper error handling"
                ))
        
        return results

    def validate_api_integration(self, file_path: Path) -> List[ValidationResult]:
        """Validate API integration"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return results
        
        # Check for API endpoint usage
        if 'api-client' in str(file_path) or 'api' in str(file_path).lower():
            for endpoint in self.api_endpoints:
                if endpoint not in content:
                    results.append(ValidationResult(
                        file_path=str(file_path),
                        status=ValidationStatus.WARNING,
                        message=f"API endpoint not found: {endpoint}",
                        suggestion=f"Add {endpoint} configuration"
                    ))
        
        # Check for proper HTTP client usage
        if 'fetch' in content or 'axios' in content:
            if 'error' not in content.lower() and 'catch' not in content:
                results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message="HTTP requests without error handling",
                    suggestion="Add proper error handling for API calls"
                ))
        
        return results

    def validate_configuration_files(self, file_path: Path) -> List[ValidationResult]:
        """Validate configuration files"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            results.append(ValidationResult(
                file_path=str(file_path),
                status=ValidationStatus.FAIL,
                message=f"Error reading config file: {str(e)}",
                suggestion="Check file format and permissions"
            ))
            return results
        
        # Validate JSON files
        if file_path.suffix == '.json':
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.FAIL,
                    message=f"Invalid JSON format: {str(e)}",
                    suggestion="Fix JSON syntax"
                ))
        
        # Check for required configuration keys
        if 'env' in file_path.name:
            required_keys = [
                'API_GATEWAY_URL',
                'BLOCKCHAIN_CORE_URL',
                'AUTH_SERVICE_URL'
            ]
            
            for key in required_keys:
                if key not in content:
                    results.append(ValidationResult(
                        file_path=str(file_path),
                        status=ValidationStatus.FAIL,
                        message=f"Required config key missing: {key}",
                        suggestion=f"Add {key} to configuration"
                    ))
        
        return results

    def validate_security_compliance(self, file_path: Path) -> List[ValidationResult]:
        """Validate security compliance"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return results
        
        # Check for security anti-patterns
        for pattern in self.security_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message=f"Potential security issue: {match.group()}",
                    line_number=line_num,
                    suggestion="Review for security implications"
                ))
        
        # Check for proper input validation
        if 'onChange' in content or 'onInput' in content:
            if 'validate' not in content and 'sanitize' not in content:
                results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message="Input handling without validation",
                    suggestion="Add input validation and sanitization"
                ))
        
        return results

    def validate_build_system(self) -> List[ValidationResult]:
        """Validate build system files"""
        results = []
        
        # Check for package.json
        package_json = self.electron_gui_path / "package.json"
        if not package_json.exists():
            results.append(ValidationResult(
                file_path=str(package_json),
                status=ValidationStatus.FAIL,
                message="package.json not found",
                suggestion="Create package.json with required dependencies"
            ))
        else:
            try:
                with open(package_json, 'r') as f:
                    package_data = json.load(f)
                
                # Check for required dependencies
                required_deps = [
                    'electron',
                    'react',
                    'typescript',
                    '@types/react'
                ]
                
                dependencies = package_data.get('dependencies', {})
                dev_dependencies = package_data.get('devDependencies', {})
                all_deps = {**dependencies, **dev_dependencies}
                
                for dep in required_deps:
                    if dep not in all_deps:
                        results.append(ValidationResult(
                            file_path=str(package_json),
                            status=ValidationStatus.FAIL,
                            message=f"Required dependency missing: {dep}",
                            suggestion=f"Add {dep} to package.json"
                        ))
                        
            except Exception as e:
                results.append(ValidationResult(
                    file_path=str(package_json),
                    status=ValidationStatus.FAIL,
                    message=f"Error reading package.json: {str(e)}",
                    suggestion="Check JSON format"
                ))
        
        # Check for webpack configs
        webpack_files = [
            "webpack.common.js",
            "webpack.main.config.js", 
            "webpack.renderer.config.js"
        ]
        
        for webpack_file in webpack_files:
            webpack_path = self.electron_gui_path / webpack_file
            if not webpack_path.exists():
                results.append(ValidationResult(
                    file_path=str(webpack_path),
                    status=ValidationStatus.FAIL,
                    message=f"Webpack config missing: {webpack_file}",
                    suggestion=f"Create {webpack_file}"
                ))
        
        # Check for TypeScript config
        tsconfig_files = [
            "tsconfig.json",
            "tsconfig.main.json"
        ]
        
        for tsconfig_file in tsconfig_files:
            tsconfig_path = self.electron_gui_path / tsconfig_file
            if not tsconfig_path.exists():
                results.append(ValidationResult(
                    file_path=str(tsconfig_path),
                    status=ValidationStatus.FAIL,
                    message=f"TypeScript config missing: {tsconfig_file}",
                    suggestion=f"Create {tsconfig_file}"
                ))
        
        return results

    def validate_tor_integration(self) -> List[ValidationResult]:
        """Validate Tor integration"""
        results = []
        
        # Check for Tor manager
        tor_manager = self.electron_gui_path / "main" / "tor-manager.ts"
        if not tor_manager.exists():
            results.append(ValidationResult(
                file_path=str(tor_manager),
                status=ValidationStatus.FAIL,
                message="Tor manager not found",
                suggestion="Create tor-manager.ts in main/"
            ))
        
        # Check for Tor config
        tor_config = self.electron_gui_path / "configs" / "tor.config.json"
        if not tor_config.exists():
            results.append(ValidationResult(
                file_path=str(tor_config),
                status=ValidationStatus.FAIL,
                message="Tor configuration not found",
                suggestion="Create tor.config.json"
            ))
        
        return results

    def validate_docker_integration(self) -> List[ValidationResult]:
        """Validate Docker integration"""
        results = []
        
        # Check for Docker service
        docker_service = self.electron_gui_path / "main" / "docker-service.ts"
        if not docker_service.exists():
            results.append(ValidationResult(
                file_path=str(docker_service),
                status=ValidationStatus.FAIL,
                message="Docker service not found",
                suggestion="Create docker-service.ts in main/"
            ))
        
        # Check for Docker config
        docker_config = self.electron_gui_path / "configs" / "docker.config.json"
        if not docker_config.exists():
            results.append(ValidationResult(
                file_path=str(docker_config),
                status=ValidationStatus.FAIL,
                message="Docker configuration not found",
                suggestion="Create docker.config.json"
            ))
        
        return results

    def validate_file(self, file_path: Path) -> List[ValidationResult]:
        """Validate a single file"""
        results = []
        
        # TypeScript/React validation
        if file_path.suffix in ['.ts', '.tsx']:
            results.extend(self.validate_typescript_files(file_path))
            results.extend(self.validate_api_integration(file_path))
            results.extend(self.validate_security_compliance(file_path))
        
        # Configuration validation
        if file_path.suffix in ['.json', '.js'] and 'config' in str(file_path):
            results.extend(self.validate_configuration_files(file_path))
        
        return results

    def run_validation(self) -> bool:
        """Run complete validation"""
        logger.info("Starting Electron GUI alignment validation...")
        
        if not self.electron_gui_path.exists():
            logger.error("electron-gui directory not found!")
            return False
        
        # Validate file structure
        logger.info("Validating file structure...")
        self.results.extend(self.validate_file_structure())
        
        # Validate build system
        logger.info("Validating build system...")
        self.results.extend(self.validate_build_system())
        
        # Validate Tor integration
        logger.info("Validating Tor integration...")
        self.results.extend(self.validate_tor_integration())
        
        # Validate Docker integration
        logger.info("Validating Docker integration...")
        self.results.extend(self.validate_docker_integration())
        
        # Validate individual files
        logger.info("Validating individual files...")
        for file_path in self.electron_gui_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.ts', '.tsx', '.js', '.json']:
                file_results = self.validate_file(file_path)
                self.results.extend(file_results)
        
        # Generate report
        self.generate_report()
        
        # Return success if no failures
        fail_count = sum(1 for r in self.results if r.status == ValidationStatus.FAIL)
        return fail_count == 0

    def generate_report(self):
        """Generate validation report"""
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
        
        # Print summary
        print("\n" + "="*80)
        print("LUCID ELECTRON GUI ALIGNMENT VALIDATION REPORT")
        print("="*80)
        print(f"Total issues found: {total_results}")
        print(f"Pass rate: {(status_counts['PASS'] / total_results * 100) if total_results > 0 else 100:.1f}%")
        print("\nStatus breakdown:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        # Print detailed results
        print("\nDetailed Results:")
        print("-" * 80)
        
        for file_path, file_results in file_results.items():
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

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Validate Electron GUI alignment")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fix", "-f", action="store_true", help="Attempt to fix issues")
    parser.add_argument("--project-root", "-p", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run validation
    validator = ElectronGUIValidator(args.project_root)
    success = validator.run_validation()
    
    if success:
        logger.info("[OK] All validations passed!")
        sys.exit(0)
    else:
        logger.error("[X] Some validations failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
