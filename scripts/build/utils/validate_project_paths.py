#!/usr/bin/env python3
"""
Lucid Project Path Validation Tool - Genius Level
Comprehensive validation of all imports, file paths, and references.
Excludes virtual environments and external dependencies.
"""

import os
import sys
import json
import ast
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import importlib.util

class PathValidator:
    """Professional path validation with comprehensive error detection."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors: List[Dict] = []
        self.fixes_applied: List[Dict] = []
        self.excluded_dirs = {'.venv', '__pycache__', '.git', '.mypy_cache', '.ruff_cache', 'node_modules'}
        
    def validate_all(self) -> Tuple[int, int]:
        """Run all validation checks."""
        print("🚀 Starting comprehensive path validation...")
        
        # Validate Python imports
        python_errors = self.validate_python_imports()
        
        # Validate Docker files
        docker_errors = self.validate_docker_files()
        
        # Validate shell scripts
        script_errors = self.validate_shell_scripts()
        
        # Validate config files
        config_errors = self.validate_config_files()
        
        # Validate devcontainer
        devcontainer_errors = self.validate_devcontainer()
        
        total_errors = len(python_errors) + len(docker_errors) + len(script_errors) + len(config_errors) + len(devcontainer_errors)
        
        self._print_summary(python_errors, docker_errors, script_errors, config_errors, devcontainer_errors)
        
        return total_errors, len(self.fixes_applied)
    
    def validate_python_imports(self) -> List[Dict]:
        """Validate all Python import statements."""
        print("📦 Validating Python imports...")
        errors = []
        
        for py_file in self._find_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Parse AST
                try:
                    tree = ast.parse(content)
                except SyntaxError as e:
                    errors.append({
                        'file': str(py_file),
                        'type': 'syntax_error',
                        'message': f"Syntax error: {e.msg}",
                        'line': e.lineno
                    })
                    continue
                
                # Check import statements
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if not self._is_import_valid(alias.name, py_file):
                                errors.append({
                                    'file': str(py_file),
                                    'type': 'import_error',
                                    'message': f"Invalid import: {alias.name}",
                                    'line': node.lineno
                                })
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            if not self._is_relative_import_valid(node.module, node.level, py_file):
                                errors.append({
                                    'file': str(py_file),
                                    'type': 'relative_import_error',
                                    'message': f"Invalid relative import: {'.' * node.level}{node.module}",
                                    'line': node.lineno
                                })
            
            except Exception as e:
                errors.append({
                    'file': str(py_file),
                    'type': 'processing_error',
                    'message': f"Error processing file: {str(e)}"
                })
        
        return errors
    
    def validate_docker_files(self) -> List[Dict]:
        """Validate Docker files for path issues."""
        print("🐳 Validating Docker files...")
        errors = []
        
        # Find all Docker files
        docker_files = list(self.project_root.rglob("Dockerfile*"))
        docker_files.extend(self.project_root.rglob("docker-compose*.yml"))
        docker_files.extend(self.project_root.rglob("docker-compose*.yaml"))
        
        for docker_file in docker_files:
            if self._is_excluded(docker_file):
                continue
                
            try:
                with open(docker_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    # Check COPY/ADD instructions
                    if re.match(r'^\s*(COPY|ADD)', line, re.IGNORECASE):
                        parts = line.split()
                        if len(parts) >= 3:
                            src_path = parts[1]
                            if not self._validate_docker_path(src_path, docker_file):
                                errors.append({
                                    'file': str(docker_file),
                                    'type': 'docker_copy_path',
                                    'message': f"Invalid COPY/ADD source path: {src_path}",
                                    'line': i
                                })
                    
                    # Check dockerfile paths in compose files
                    if 'dockerfile:' in line:
                        dockerfile_path = line.split('dockerfile:')[1].strip()
                        if not self._validate_compose_dockerfile_path(dockerfile_path, docker_file):
                            errors.append({
                                'file': str(docker_file),
                                'type': 'compose_dockerfile_path',
                                'message': f"Invalid dockerfile path: {dockerfile_path}",
                                'line': i
                            })
            
            except Exception as e:
                errors.append({
                    'file': str(docker_file),
                    'type': 'processing_error',
                    'message': f"Error processing Docker file: {str(e)}"
                })
        
        return errors
    
    def validate_shell_scripts(self) -> List[Dict]:
        """Validate shell script file references."""
        print("🔧 Validating shell scripts...")
        errors = []
        
        script_files = list(self.project_root.rglob("*.sh"))
        script_files.extend(self.project_root.rglob("*.ps1"))
        
        for script_file in script_files:
            if self._is_excluded(script_file):
                continue
                
            try:
                with open(script_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    # Check file references
                    file_refs = re.findall(r'([\'"])([^\'\"]*\.[a-zA-Z0-9]+)\1', line)
                    for _, file_path in file_refs:
                        if self._looks_like_file_path(file_path) and not self._validate_script_file_ref(file_path, script_file):
                            errors.append({
                                'file': str(script_file),
                                'type': 'script_file_ref',
                                'message': f"Invalid file reference: {file_path}",
                                'line': i
                            })
            
            except Exception as e:
                errors.append({
                    'file': str(script_file),
                    'type': 'processing_error',
                    'message': f"Error processing script: {str(e)}"
                })
        
        return errors
    
    def validate_config_files(self) -> List[Dict]:
        """Validate configuration files."""
        print("⚙️ Validating configuration files...")
        errors = []
        
        config_files = list(self.project_root.rglob("*.json"))
        config_files.extend(self.project_root.rglob("*.yaml"))
        config_files.extend(self.project_root.rglob("*.yml"))
        config_files.extend(self.project_root.rglob("*.toml"))
        
        for config_file in config_files:
            if self._is_excluded(config_file) or 'package-lock.json' in str(config_file):
                continue
            
            try:
                # Validate JSON syntax
                if config_file.suffix == '.json':
                    with open(config_file, 'r', encoding='utf-8') as f:
                        json.load(f)
                        
            except json.JSONDecodeError as e:
                errors.append({
                    'file': str(config_file),
                    'type': 'json_syntax',
                    'message': f"JSON syntax error: {e.msg}",
                    'line': e.lineno if hasattr(e, 'lineno') else 0
                })
            except Exception as e:
                errors.append({
                    'file': str(config_file),
                    'type': 'processing_error',
                    'message': f"Error processing config: {str(e)}"
                })
        
        return errors
    
    def validate_devcontainer(self) -> List[Dict]:
        """Validate devcontainer configuration."""
        print("📦 Validating devcontainer...")
        errors = []
        
        devcontainer_file = self.project_root / "infrastructure" / "containers" / ".devcontainer" / "devcontainer.json"
        
        if devcontainer_file.exists():
            try:
                with open(devcontainer_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Check postCreateCommand script
                if 'postCreateCommand' in config and isinstance(config['postCreateCommand'], list):
                    if len(config['postCreateCommand']) > 2:
                        script_path = config['postCreateCommand'][2]
                        # Remove /workspaces/Lucid prefix for local validation
                        local_script_path = script_path.replace('/workspaces/Lucid/', '')
                        if not (self.project_root / local_script_path).exists():
                            errors.append({
                                'file': str(devcontainer_file),
                                'type': 'devcontainer_script',
                                'message': f"postCreateCommand script not found: {local_script_path}",
                                'line': 0
                            })
                
                # Check dockerComposeFile
                if 'dockerComposeFile' in config:
                    compose_file = Path(devcontainer_file.parent) / config['dockerComposeFile']
                    if not compose_file.exists():
                        errors.append({
                            'file': str(devcontainer_file),
                            'type': 'devcontainer_compose',
                            'message': f"Docker compose file not found: {config['dockerComposeFile']}",
                            'line': 0
                        })
                        
            except Exception as e:
                errors.append({
                    'file': str(devcontainer_file),
                    'type': 'devcontainer_error',
                    'message': f"Error validating devcontainer: {str(e)}"
                })
        
        return errors
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files excluding virtual environments."""
        python_files = []
        for py_file in self.project_root.rglob("*.py"):
            if not self._is_excluded(py_file):
                python_files.append(py_file)
        return python_files
    
    def _is_excluded(self, path: Path) -> bool:
        """Check if path should be excluded from validation."""
        path_str = str(path)
        return any(excluded in path_str for excluded in self.excluded_dirs)
    
    def _is_import_valid(self, import_name: str, current_file: Path) -> bool:
        """Check if an import statement is valid."""
        # Skip standard library and third-party imports
        if '.' not in import_name or import_name.split('.')[0] in {'os', 'sys', 'json', 'ast', 're', 'pathlib', 'typing', 'collections', 'email', 'logging', 'zipfile'}:
            return True
        
        # For project imports, try to resolve
        try:
            spec = importlib.util.find_spec(import_name)
            return spec is not None
        except (ImportError, ValueError, ModuleNotFoundError):
            # Check if it's a local module that exists as a file
            module_path = self.project_root / import_name.replace('.', '/') 
            return module_path.is_dir() or (module_path.with_suffix('.py')).exists()
    
    def _is_relative_import_valid(self, module_name: str, level: int, current_file: Path) -> bool:
        """Check if a relative import is valid."""
        if not module_name:
            return True  # from . import ... is usually valid
        
        # Calculate the target directory based on relative import level
        current_dir = current_file.parent
        target_dir = current_dir
        for _ in range(level - 1):
            target_dir = target_dir.parent
            if target_dir == self.project_root.parent:
                return False  # Gone too far up
        
        # Check if the target module exists
        module_path = target_dir / module_name.replace('.', '/')
        return module_path.is_dir() or (module_path.with_suffix('.py')).exists()
    
    def _validate_docker_path(self, src_path: str, docker_file: Path) -> bool:
        """Validate Docker COPY/ADD source path."""
        if src_path.startswith('http') or src_path == '.':
            return True  # URL or current directory
        
        # For Dockerfiles, paths are relative to build context
        docker_dir = docker_file.parent
        # Try different possible contexts
        possible_contexts = [docker_dir, docker_dir.parent, self.project_root]
        
        for context in possible_contexts:
            full_path = context / src_path
            if full_path.exists():
                return True
        
        return False
    
    def _validate_compose_dockerfile_path(self, dockerfile_path: str, compose_file: Path) -> bool:
        """Validate dockerfile path in docker-compose."""
        compose_dir = compose_file.parent
        full_path = compose_dir / dockerfile_path
        return full_path.exists()
    
    def _looks_like_file_path(self, path: str) -> bool:
        """Determine if a string looks like a file path."""
        return ('/' in path or '\\' in path) and not path.startswith('http') and len(path) > 3
    
    def _validate_script_file_ref(self, file_path: str, script_file: Path) -> bool:
        """Validate file reference in script."""
        script_dir = script_file.parent
        
        # Try relative to script directory
        if (script_dir / file_path).exists():
            return True
        
        # Try relative to project root
        if (self.project_root / file_path).exists():
            return True
        
        # Try absolute paths or system paths
        if file_path.startswith('/') and Path(file_path).exists():
            return True
        
        return False
    
    def _print_summary(self, python_errors, docker_errors, script_errors, config_errors, devcontainer_errors):
        """Print validation summary."""
        print("\n" + "="*60)
        print("📊 VALIDATION SUMMARY")
        print("="*60)
        
        total_errors = len(python_errors) + len(docker_errors) + len(script_errors) + len(config_errors) + len(devcontainer_errors)
        
        if total_errors == 0:
            print("🎉 ALL VALIDATIONS PASSED! No path errors detected.")
            print("✅ Project is ready for devcontainer rebuild!")
        else:
            print(f"❌ Found {total_errors} path/import errors:")
            print(f"   • Python imports: {len(python_errors)}")
            print(f"   • Docker files: {len(docker_errors)}")
            print(f"   • Shell scripts: {len(script_errors)}")
            print(f"   • Config files: {len(config_errors)}")
            print(f"   • Devcontainer: {len(devcontainer_errors)}")
            
            # Show critical errors
            print("\n🔍 CRITICAL ERRORS:")
            for error_list, category in [(python_errors, "Python"), (docker_errors, "Docker"), 
                                        (script_errors, "Scripts"), (config_errors, "Config"), 
                                        (devcontainer_errors, "Devcontainer")]:
                for error in error_list[:3]:  # Show first 3 errors per category
                    file_path = Path(error['file']).relative_to(self.project_root)
                    print(f"   {category}: {file_path}:{error.get('line', '?')} - {error['message']}")
        
        print("="*60)

def main():
    """Main validation function."""
    project_root = Path(__file__).parent.parent.parent  # ../../../ from scripts/build/
    
    if not project_root.exists():
        print("❌ Project root not found!")
        sys.exit(1)
    
    print(f"🎯 Validating project: {project_root}")
    
    validator = PathValidator(project_root)
    total_errors, fixes_applied = validator.validate_all()
    
    if total_errors == 0:
        print("\n🚀 PROJECT IS READY! All path validations passed.")
        print("✅ You can safely rebuild the devcontainer.")
        return 0
    else:
        print(f"\n⚠️  Found {total_errors} issues that need attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())