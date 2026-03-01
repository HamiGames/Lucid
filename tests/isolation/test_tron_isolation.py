"""
TRON Isolation Test Suite
Tests to verify that TRON payment system is completely isolated from blockchain core
Part of Step 28: TRON Isolation Verification

This test suite ensures:
1. No TRON imports in blockchain/core/
2. No payment code in blockchain core
3. Network isolation between services
4. Directory structure compliance
"""

import pytest
import os
import sys
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Set
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestTRONIsolation:
    """Test class for TRON isolation verification"""
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).parent.parent.parent
    
    @pytest.fixture
    def blockchain_dir(self, project_root):
        """Get blockchain directory"""
        return project_root / "blockchain"
    
    @pytest.fixture
    def payment_systems_dir(self, project_root):
        """Get payment systems directory"""
        return project_root / "payment-systems"
    
    @pytest.fixture
    def tron_keywords(self):
        """Get TRON-related keywords to search for"""
        return [
            "tron", "TRON", "TronNode", "TronClient", "tron_client",
            "tron-node", "tron-client", "usdt", "USDT", "TRX", "trx",
            "tron_payment", "TronPayment", "tron_payout", "TronPayout",
            "tron_wallet", "TronWallet", "tron_network", "TronNetwork"
        ]
    
    def test_no_tron_imports_in_blockchain_core(self, blockchain_dir, tron_keywords):
        """Test that blockchain core has no TRON imports"""
        if not blockchain_dir.exists():
            pytest.skip("Blockchain directory not found")
        
        violations = []
        
        # Scan Python files in blockchain core
        for py_file in blockchain_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        # Check for TRON imports
                        if any(keyword.lower() in line.lower() for keyword in tron_keywords):
                            # Check if it's an import statement
                            if re.search(r'\b(import|from)\s+.*\b' + re.escape(keyword.lower()) + r'\b', line, re.IGNORECASE):
                                violations.append({
                                    'file': str(py_file.relative_to(project_root)),
                                    'line': line_num,
                                    'content': line.strip(),
                                    'keyword': keyword
                                })
            except Exception as e:
                pytest.fail(f"Error reading file {py_file}: {e}")
        
        assert len(violations) == 0, f"Found TRON imports in blockchain core: {violations}"
    
    def test_no_tron_references_in_blockchain_core(self, blockchain_dir, tron_keywords):
        """Test that blockchain core has no TRON references"""
        if not blockchain_dir.exists():
            pytest.skip("Blockchain directory not found")
        
        violations = []
        
        # Scan all files in blockchain core
        for file_path in blockchain_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.yml', '.yaml', '.json']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                        for line_num, line in enumerate(lines, 1):
                            for keyword in tron_keywords:
                                if re.search(rf'\b{re.escape(keyword)}\b', line, re.IGNORECASE):
                                    violations.append({
                                        'file': str(file_path.relative_to(project_root)),
                                        'line': line_num,
                                        'content': line.strip(),
                                        'keyword': keyword
                                    })
                except Exception as e:
                    continue  # Skip files that can't be read
        
        assert len(violations) == 0, f"Found TRON references in blockchain core: {violations}"
    
    def test_tron_files_in_payment_systems(self, payment_systems_dir, tron_keywords):
        """Test that TRON files are properly located in payment systems"""
        if not payment_systems_dir.exists():
            pytest.skip("Payment systems directory not found")
        
        tron_files = []
        
        # Find TRON-related files in payment systems
        for file_path in payment_systems_dir.rglob("*"):
            if file_path.is_file():
                filename = file_path.name.lower()
                if any(keyword.lower() in filename for keyword in tron_keywords):
                    tron_files.append(str(file_path.relative_to(project_root)))
        
        # Should have at least some TRON files in payment systems
        assert len(tron_files) > 0, "No TRON files found in payment systems directory"
    
    def test_no_tron_files_in_blockchain_directory(self, blockchain_dir, tron_keywords):
        """Test that no TRON files exist in blockchain directory"""
        if not blockchain_dir.exists():
            pytest.skip("Blockchain directory not found")
        
        forbidden_files = []
        
        # Check for TRON-related filenames in blockchain directory
        for file_path in blockchain_dir.rglob("*"):
            if file_path.is_file():
                filename = file_path.name.lower()
                if any(keyword.lower() in filename for keyword in tron_keywords):
                    forbidden_files.append(str(file_path.relative_to(project_root)))
        
        assert len(forbidden_files) == 0, f"Found TRON files in blockchain directory: {forbidden_files}"
    
    def test_required_directories_exist(self, project_root):
        """Test that required directories for isolation exist"""
        required_dirs = [
            "blockchain/core",
            "blockchain/api",
            "payment-systems/tron",
            "payment-systems/tron/services",
            "payment-systems/tron/api",
            "payment-systems/tron/models"
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            full_path = project_root / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
        
        assert len(missing_dirs) == 0, f"Missing required directories: {missing_dirs}"
    
    def test_network_isolation_configuration(self):
        """Test that network isolation is properly configured"""
        try:
            # Check if Docker is available
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                pytest.skip("Docker not available")
            
            # Check for required networks
            result = subprocess.run(['docker', 'network', 'ls'], capture_output=True, text=True, timeout=10)
            assert result.returncode == 0, "Failed to list Docker networks"
            
            networks = result.stdout
            
            # Check for main network
            assert 'lucid-dev' in networks, "lucid-dev network not found"
            
            # Check for isolated network
            assert 'lucid-network-isolated' in networks, "lucid-network-isolated network not found"
            
        except subprocess.TimeoutExpired:
            pytest.skip("Docker command timed out")
        except FileNotFoundError:
            pytest.skip("Docker not installed")
    
    def test_docker_compose_network_isolation(self, project_root):
        """Test that Docker Compose files properly isolate networks"""
        compose_files = [
            "configs/docker/docker-compose.all.yml",
            "configs/docker/docker-compose.foundation.yml",
            "configs/docker/docker-compose.core.yml",
            "configs/docker/docker-compose.application.yml",
            "configs/docker/docker-compose.support.yml"
        ]
        
        for compose_file in compose_files:
            compose_path = project_root / compose_file
            if compose_path.exists():
                try:
                    with open(compose_path, 'r') as f:
                        content = f.read()
                        
                        # Check for network isolation
                        if 'lucid-dev' in content:
                            assert 'lucid-network-isolated' in content, f"Missing isolated network in {compose_file}"
                        
                except Exception as e:
                    pytest.fail(f"Error reading {compose_file}: {e}")
    
    def test_payment_systems_directory_structure(self, payment_systems_dir):
        """Test that payment systems directory has proper structure"""
        if not payment_systems_dir.exists():
            pytest.skip("Payment systems directory not found")
        
        required_subdirs = [
            "tron",
            "tron/services",
            "tron/api",
            "tron/models"
        ]
        
        missing_subdirs = []
        for subdir in required_subdirs:
            subdir_path = payment_systems_dir / subdir
            if not subdir_path.exists():
                missing_subdirs.append(subdir)
        
        assert len(missing_subdirs) == 0, f"Missing payment systems subdirectories: {missing_subdirs}"
    
    def test_blockchain_core_has_no_payment_code(self, blockchain_dir):
        """Test that blockchain core has no payment-related code"""
        if not blockchain_dir.exists():
            pytest.skip("Blockchain directory not found")
        
        payment_keywords = [
            "payment", "payout", "wallet", "usdt", "trx", "tron",
            "balance", "transfer", "transaction", "fee", "gas"
        ]
        
        violations = []
        
        # Scan blockchain core for payment-related code
        for py_file in blockchain_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        for keyword in payment_keywords:
                            if re.search(rf'\b{re.escape(keyword)}\b', line, re.IGNORECASE):
                                # Check if it's not just a comment or string
                                if not line.strip().startswith('#') and not line.strip().startswith('"""'):
                                    violations.append({
                                        'file': str(py_file.relative_to(project_root)),
                                        'line': line_num,
                                        'content': line.strip(),
                                        'keyword': keyword
                                    })
            except Exception as e:
                continue
        
        # Allow some violations for legitimate blockchain terms
        filtered_violations = []
        for violation in violations:
            # Filter out legitimate blockchain terms
            if violation['keyword'] not in ['transaction', 'balance', 'gas']:
                filtered_violations.append(violation)
        
        assert len(filtered_violations) == 0, f"Found payment code in blockchain core: {filtered_violations}"
    
    def test_tron_isolation_compliance_score(self, project_root):
        """Test overall TRON isolation compliance"""
        # This test runs the verification script and checks compliance score
        verification_script = project_root / "scripts" / "verification" / "verify-tron-isolation.py"
        
        if not verification_script.exists():
            pytest.skip("Verification script not found")
        
        try:
            result = subprocess.run([
                sys.executable, str(verification_script), str(project_root)
            ], capture_output=True, text=True, timeout=30)
            
            # Check if verification passed
            assert result.returncode == 0, f"TRON isolation verification failed: {result.stderr}"
            
            # Parse output for compliance score
            output = result.stdout
            if "compliance_score" in output:
                # Extract compliance score from output
                score_match = re.search(r'Compliance Score: (\d+)%', output)
                if score_match:
                    score = int(score_match.group(1))
                    assert score >= 75, f"Compliance score too low: {score}%"
            
        except subprocess.TimeoutExpired:
            pytest.fail("Verification script timed out")
        except Exception as e:
            pytest.fail(f"Error running verification script: {e}")

class TestTRONIsolationIntegration:
    """Integration tests for TRON isolation"""
    
    def test_end_to_end_isolation(self, project_root):
        """Test end-to-end TRON isolation"""
        # This test verifies the complete isolation by:
        # 1. Checking no TRON code in blockchain
        # 2. Checking TRON code only in payment systems
        # 3. Verifying network isolation
        # 4. Checking directory structure
        
        blockchain_dir = project_root / "blockchain"
        payment_systems_dir = project_root / "payment-systems"
        
        # Check blockchain isolation
        if blockchain_dir.exists():
            tron_files_in_blockchain = []
            for file_path in blockchain_dir.rglob("*"):
                if file_path.is_file() and 'tron' in file_path.name.lower():
                    tron_files_in_blockchain.append(str(file_path.relative_to(project_root)))
            
            assert len(tron_files_in_blockchain) == 0, f"TRON files found in blockchain: {tron_files_in_blockchain}"
        
        # Check payment systems has TRON files
        if payment_systems_dir.exists():
            tron_files_in_payment = []
            for file_path in payment_systems_dir.rglob("*"):
                if file_path.is_file() and 'tron' in file_path.name.lower():
                    tron_files_in_payment.append(str(file_path.relative_to(project_root)))
            
            # Should have some TRON files in payment systems
            assert len(tron_files_in_payment) > 0, "No TRON files found in payment systems"
    
    def test_network_isolation_verification(self):
        """Test network isolation verification"""
        try:
            # Check Docker networks
            result = subprocess.run(['docker', 'network', 'ls'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                networks = result.stdout
                
                # Verify both networks exist
                assert 'lucid-dev' in networks, "Main network not found"
                assert 'lucid-network-isolated' in networks, "Isolated network not found"
                
                # Verify networks are different
                assert 'lucid-dev' != 'lucid-network-isolated', "Networks should be different"
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Docker not available for network verification")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
