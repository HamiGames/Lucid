#!/usr/bin/env python3
"""
Lucid Import Path Validator and Fixer
=====================================

This script systematically validates and fixes all import pathways, 
file references, and broken links after the project restructuring.

Critical for preventing devcontainer implosion at 8% project completion.
"""

import os
import re
import sys
import glob
import json
from pathlib import Path
from typing import List, Dict, Tuple, Set
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImportPathValidator:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.errors = []
        self.fixes_applied = 0
        
        # Define the new project structure
        self.new_structure = {
            'configs': ['environment', 'docker', 'ssh'],
            'docs': ['guides', 'build-docs', 'verification', 'specs'],
            'scripts': ['devcontainer', 'build', 'network', 'deployment'],
            'infrastructure': ['compose', 'containers'],
            'build': ['logs', 'artifacts']
        }
        
        # Import mapping for moved files
        self.import_mappings = {
            # Old import -> New import
            'from admin.system.admin_manager': 'from admin.system.admin_manager',
            'from admin.system.governance': 'from admin.system.governance',
            'from admin.system.policies': 'from admin.system.policies',
            'from admin.system.keys': 'from admin.system.keys',
            'from blockchain.core.storage': 'from blockchain.core.storage',
            'from blockchain.core.node': 'from blockchain.core.node',
        }
        
        # File reference mappings for moved files
        self.file_mappings = {
            '.devcontainer/': 'infrastructure/containers/.devcontainer/',
            '06-orchestration-runtime/': 'infrastructure/compose/',
            'Build_guide_docs/': 'docs/build-docs/Build_guide_docs/',
            '.verify/': 'docs/verification/.verify/',
        }

    def validate_all_paths(self) -> bool:
        """Validate all paths in the project and fix issues."""
        logger.info("Starting comprehensive path validation...")
        
        # Phase 1: Python import validation
        self._validate_python_imports()
        
        # Phase 2: Docker file reference validation
        self._validate_docker_references()
        
        # Phase 3: Script reference validation
        self._validate_script_references()
        
        # Phase 4: Configuration file validation
        self._validate_config_references()
        
        # Phase 5: DevContainer validation
        self._validate_devcontainer()
        
        # Generate report
        self._generate_report()
        
        return len(self.errors) == 0

    def _validate_python_imports(self):
        """Validate and fix Python import statements."""
        logger.info("Validating Python imports...")
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Check for relative imports that may be broken
                relative_imports = re.findall(r'^from \.[^\s]+ import', content, re.MULTILINE)
                for imp in relative_imports:
                    # Validate the import path exists
                    self._validate_relative_import(py_file, imp)
                
                # Fix known import mappings
                for old_import, new_import in self.import_mappings.items():
                    if old_import in content:
                        content = content.replace(old_import, new_import)
                        logger.info(f"Fixed import in {py_file}: {old_import} -> {new_import}")
                        self.fixes_applied += 1
                
                # Write back if changes were made
                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
            except Exception as e:
                self.errors.append(f"Error processing {py_file}: {e}")

    def _validate_relative_import(self, file_path: Path, import_statement: str):
        """Validate a relative import exists."""
        try:
            # Extract the module path from import statement
            match = re.match(r'from \.([\w.]+) import', import_statement)
            if not match:
                return
                
            module_path = match.group(1)
            current_dir = file_path.parent
            
            # Convert relative path to absolute
            parts = module_path.split('.')
            target_dir = current_dir
            
            for part in parts:
                target_dir = target_dir / part
                
            # Check if the target exists as a directory with __init__.py or as a .py file
            if not ((target_dir.is_dir() and (target_dir / '__init__.py').exists()) or 
                   (target_dir.with_suffix('.py')).exists()):
                self.errors.append(f"Broken relative import in {file_path}: {import_statement}")
                
        except Exception as e:
            self.errors.append(f"Error validating import in {file_path}: {e}")

    def _validate_docker_references(self):
        """Validate Docker file references and build contexts."""
        logger.info("Validating Docker references...")
        
        # Find all Docker files
        docker_files = []
        docker_files.extend(self.project_root.rglob("Dockerfile*"))
        docker_files.extend(self.project_root.rglob("docker-compose*.yml"))
        docker_files.extend(self.project_root.rglob("docker-compose*.yaml"))
        
        for docker_file in docker_files:
            try:
                with open(docker_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Check build contexts
                contexts = re.findall(r'context:\s*(.+)', content)
                for context in contexts:
                    context = context.strip()
                    if not self._validate_path_exists(docker_file, context):
                        self.errors.append(f"Invalid build context in {docker_file}: {context}")
                
                # Check COPY/ADD statements
                copies = re.findall(r'(?:COPY|ADD)\s+([^\s]+)', content, re.IGNORECASE)
                for copy_path in copies:
                    if not copy_path.startswith('--') and '://' not in copy_path:
                        if not self._validate_path_exists(docker_file, copy_path):
                            self.errors.append(f"Invalid COPY/ADD path in {docker_file}: {copy_path}")
                
                # Fix known file mappings
                for old_path, new_path in self.file_mappings.items():
                    if old_path in content:
                        content = content.replace(old_path, new_path)
                        logger.info(f"Fixed path in {docker_file}: {old_path} -> {new_path}")
                        self.fixes_applied += 1
                
                # Write back if changes were made
                if content != original_content:
                    with open(docker_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
            except Exception as e:
                self.errors.append(f"Error processing {docker_file}: {e}")

    def _validate_script_references(self):
        """Validate script file references."""
        logger.info("Validating script references...")
        
        script_files = []
        script_files.extend(self.project_root.rglob("*.sh"))
        script_files.extend(self.project_root.rglob("*.ps1"))
        
        for script_file in script_files:
            try:
                with open(script_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check for file references (basic patterns)
                file_refs = re.findall(r'["\']([^"\']*\.[a-zA-Z]+)["\']', content)
                for ref in file_refs:
                    if '/' in ref or '\\' in ref:  # Looks like a path
                        if not self._validate_path_exists(script_file, ref):
                            # Only report if it looks like a local file reference
                            if not ref.startswith('http') and not ref.startswith('ftp'):
                                self.errors.append(f"Potentially broken path in {script_file}: {ref}")
                                
            except Exception as e:
                self.errors.append(f"Error processing {script_file}: {e}")

    def _validate_config_references(self):
        """Validate configuration file references."""
        logger.info("Validating configuration references...")
        
        config_files = []
        config_files.extend(self.project_root.rglob("*.json"))
        config_files.extend(self.project_root.rglob("*.yaml"))
        config_files.extend(self.project_root.rglob("*.yml"))
        config_files.extend(self.project_root.rglob("*.toml"))
        
        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Fix known file mappings
                for old_path, new_path in self.file_mappings.items():
                    if old_path in content:
                        content = content.replace(old_path, new_path)
                        logger.info(f"Fixed path in {config_file}: {old_path} -> {new_path}")
                        self.fixes_applied += 1
                
                # Write back if changes were made
                if content != original_content:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
            except Exception as e:
                self.errors.append(f"Error processing {config_file}: {e}")

    def _validate_devcontainer(self):
        """Specifically validate devcontainer configuration."""
        logger.info("Validating devcontainer configuration...")
        
        devcontainer_json = self.project_root / "infrastructure/containers/.devcontainer/devcontainer.json"
        if devcontainer_json.exists():
            try:
                with open(devcontainer_json, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Check postCreateCommand path
                post_create = config.get('postCreateCommand', [])
                if isinstance(post_create, list) and len(post_create) > 2:
                    script_path = post_create[2]  # Usually the script path
                    if script_path.startswith('/workspaces/Lucid/'):
                        local_path = script_path.replace('/workspaces/Lucid/', '')
                        if not (self.project_root / local_path).exists():
                            self.errors.append(f"DevContainer postCreateCommand script missing: {script_path}")
                
                # Check dockerComposeFile
                compose_file = config.get('dockerComposeFile')
                if compose_file:
                    compose_path = devcontainer_json.parent / compose_file
                    if not compose_path.exists():
                        self.errors.append(f"DevContainer compose file missing: {compose_file}")
                        
            except Exception as e:
                self.errors.append(f"Error validating devcontainer.json: {e}")

    def _validate_path_exists(self, base_file: Path, target_path: str) -> bool:
        """Check if a path exists relative to the base file."""
        try:
            if target_path.startswith('/'):
                # Absolute path - check from project root
                full_path = self.project_root / target_path.lstrip('/')
            else:
                # Relative path - check from base file directory
                full_path = base_file.parent / target_path
            
            return full_path.exists()
        except Exception:
            return False

    def _generate_report(self):
        """Generate validation report."""
        logger.info("=== VALIDATION REPORT ===")
        logger.info(f"Fixes applied: {self.fixes_applied}")
        logger.info(f"Errors found: {len(self.errors)}")
        
        if self.errors:
            logger.error("ERRORS FOUND:")
            for i, error in enumerate(self.errors, 1):
                logger.error(f"  {i}. {error}")
        else:
            logger.info("✅ All paths validated successfully!")
        
        # Write detailed report to file
        report_file = self.project_root / "build/logs/path_validation_report.txt"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("LUCID PROJECT PATH VALIDATION REPORT\n")
            f.write("=====================================\n\n")
            f.write(f"Generated: {os.popen('date').read().strip()}\n")
            f.write(f"Project Root: {self.project_root}\n")
            f.write(f"Fixes Applied: {self.fixes_applied}\n")
            f.write(f"Errors Found: {len(self.errors)}\n\n")
            
            if self.errors:
                f.write("ERRORS:\n")
                f.write("-------\n")
                for i, error in enumerate(self.errors, 1):
                    f.write(f"{i}. {error}\n")
            else:
                f.write("✅ All paths validated successfully!\n")
        
        logger.info(f"Detailed report written to: {report_file}")

def main():
    """Main entry point."""
    print("🔍 Lucid Import Path Validator and Fixer")
    print("==========================================")
    print("Preventing devcontainer implosion since 8% project completion!\n")
    
    # Find project root (look for key files)
    current = Path.cwd()
    project_root = None
    
    while current != current.parent:
        if (current / "README.md").exists() and (current / "infrastructure").exists():
            project_root = current
            break
        current = current.parent
    
    if not project_root:
        print("❌ Could not find project root directory!")
        sys.exit(1)
    
    print(f"📁 Project root: {project_root}")
    
    validator = ImportPathValidator(str(project_root))
    success = validator.validate_all_paths()
    
    if success:
        print("\n✅ ALL PATHS VALIDATED SUCCESSFULLY!")
        print("🚀 DevContainer is safe to launch!")
        sys.exit(0)
    else:
        print(f"\n❌ {len(validator.errors)} ERRORS FOUND!")
        print("⚠️  DevContainer may have issues. Check the report!")
        sys.exit(1)

if __name__ == "__main__":
    main()