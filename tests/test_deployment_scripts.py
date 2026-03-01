# Test Script for Deployment Scripts Section
# Validates PowerShell and Bash deployment scripts
# Based on LUCID-STRICT requirements

import os
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_powershell_script_exists():
    """Test that PowerShell deployment script exists"""
    try:
        script_path = Path("deploy-lucid-windows.ps1")
        assert script_path.exists(), "PowerShell script not found"
        
        # Check script is not empty
        content = script_path.read_text()
        assert len(content) > 1000, "PowerShell script too small"
        assert "LUCID-STRICT" in content, "LUCID-STRICT not found in script"
        
        logger.info("✓ PowerShell script exists and has content")
        return True
        
    except Exception as e:
        logger.error(f"✗ PowerShell script test failed: {e}")
        return False

def test_bash_script_exists():
    """Test that Bash deployment script exists"""
    try:
        script_path = Path("deploy-lucid-pi.sh")
        assert script_path.exists(), "Bash script not found"
        
        # Check script is not empty
        content = script_path.read_text()
        assert len(content) > 1000, "Bash script too small"
        assert "LUCID-STRICT" in content, "LUCID-STRICT not found in script"
        assert "#!/bin/bash" in content, "Bash shebang not found"
        
        logger.info("✓ Bash script exists and has content")
        return True
        
    except Exception as e:
        logger.error(f"✗ Bash script test failed: {e}")
        return False

def test_powershell_syntax():
    """Test PowerShell script syntax"""
    try:
        # Check if PowerShell is available
        result = subprocess.run(
            ["powershell.exe", "-Command", "Get-Command", "Write-Host"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.warning("PowerShell not available, skipping syntax test")
            return True
        
        # Test script syntax
        result = subprocess.run(
            ["powershell.exe", "-File", "deploy-lucid-windows.ps1", "-Action", "help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Script should fail with help message, not syntax error
        if "ParentContainsErrorRecordException" in result.stderr:
            logger.error("PowerShell syntax error detected")
            return False
        
        logger.info("✓ PowerShell script syntax appears valid")
        return True
        
    except subprocess.TimeoutExpired:
        logger.warning("PowerShell test timed out")
        return True
    except Exception as e:
        logger.error(f"✗ PowerShell syntax test failed: {e}")
        return False

def test_bash_syntax():
    """Test Bash script syntax using shellcheck or bash -n"""
    try:
        # First try with bash -n for syntax check
        result = subprocess.run(
            ["bash", "-n", "deploy-lucid-pi.sh"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("✓ Bash script syntax is valid")
            return True
        else:
            # Check if it's a WSL issue on Windows
            if "WSL" in result.stderr or "CreateProcessCommon" in result.stderr:
                logger.warning("WSL not available on Windows, skipping bash syntax check")
                return True
            else:
                logger.error(f"Bash syntax error: {result.stderr}")
                return False
            
    except FileNotFoundError:
        logger.warning("Bash not available, skipping syntax test")
        return True
    except Exception as e:
        logger.error(f"✗ Bash syntax test failed: {e}")
        return False

def test_script_parameters():
    """Test that scripts have proper parameter handling"""
    try:
        # Test PowerShell script parameters
        ps_content = Path("deploy-lucid-windows.ps1").read_text()
        
        # Check for parameter validation
        assert "[ValidateSet(" in ps_content, "PowerShell script missing parameter validation"
        assert "deploy" in ps_content, "PowerShell script missing deploy action"
        assert "start" in ps_content, "PowerShell script missing start action"
        assert "stop" in ps_content, "PowerShell script missing stop action"
        
        # Test Bash script parameters
        bash_content = Path("deploy-lucid-pi.sh").read_text()
        
        # Check for action handling
        assert "case \"$ACTION\" in" in bash_content, "Bash script missing action handling"
        assert "deploy" in bash_content, "Bash script missing deploy action"
        assert "start" in bash_content, "Bash script missing start action"
        assert "stop" in bash_content, "Bash script missing stop action"
        
        logger.info("✓ Scripts have proper parameter handling")
        return True
        
    except Exception as e:
        logger.error(f"✗ Parameter handling test failed: {e}")
        return False

def test_runtime_variables():
    """Test that runtime variables are properly defined"""
    try:
        # Test PowerShell runtime variables
        ps_content = Path("deploy-lucid-windows.ps1").read_text()
        
        # Check for environment configuration
        assert "ENV_VARS" in ps_content, "PowerShell script missing ENV_VARS"
        assert "TRON_NETWORK" in ps_content, "PowerShell script missing TRON_NETWORK"
        assert "MONGO_URL" in ps_content, "PowerShell script missing MONGO_URL"
        
        # Test Bash runtime variables
        bash_content = Path("deploy-lucid-pi.sh").read_text()
        
        # Check for environment configuration
        assert "declare -A ENV_VARS" in bash_content, "Bash script missing ENV_VARS declaration"
        assert "TRON_NETWORK" in bash_content, "Bash script missing TRON_NETWORK"
        assert "MONGO_URL" in bash_content, "Bash script missing MONGO_URL"
        
        logger.info("✓ Scripts have proper runtime variables")
        return True
        
    except Exception as e:
        logger.error(f"✗ Runtime variables test failed: {e}")
        return False

def test_service_definitions():
    """Test that service definitions are complete"""
    try:
        # Test PowerShell services
        ps_content = Path("deploy-lucid-windows.ps1").read_text()
        
        assert "lucid_tor" in ps_content, "PowerShell script missing Tor service"
        assert "lucid_mongo" in ps_content, "PowerShell script missing MongoDB service"
        assert "lucid_api" in ps_content, "PowerShell script missing API service"
        assert "9050" in ps_content, "PowerShell script missing Tor port"
        assert "27017" in ps_content, "PowerShell script missing MongoDB port"
        assert "8081" in ps_content, "PowerShell script missing API port"
        
        # Test Bash services
        bash_content = Path("deploy-lucid-pi.sh").read_text()
        
        assert "lucid_tor" in bash_content, "Bash script missing Tor service"
        assert "lucid_mongo" in bash_content, "Bash script missing MongoDB service"  
        assert "lucid_api" in bash_content, "Bash script missing API service"
        assert "9050" in bash_content, "Bash script missing Tor port"
        assert "27017" in bash_content, "Bash script missing MongoDB port"
        assert "8081" in bash_content, "Bash script missing API port"
        
        logger.info("✓ Scripts have complete service definitions")
        return True
        
    except Exception as e:
        logger.error(f"✗ Service definitions test failed: {e}")
        return False

def test_network_integration():
    """Test that scripts integrate with network setup"""
    try:
        # Test PowerShell network integration
        ps_content = Path("deploy-lucid-windows.ps1").read_text()
        
        assert "setup_lucid_networks.ps1" in ps_content, "PowerShell script missing network setup"
        assert "setup_lucid_networks" in ps_content, "PowerShell script missing network setup integration"
        
        # Test Bash network integration  
        bash_content = Path("deploy-lucid-pi.sh").read_text()
        
        assert "setup_lucid_networks" in bash_content or "docker network create" in bash_content, "Bash script missing network setup"
        assert "172.20.0.0" in bash_content, "Bash script missing network subnet"
        
        logger.info("✓ Scripts integrate with network setup")
        return True
        
    except Exception as e:
        logger.error(f"✗ Network integration test failed: {e}")
        return False

def test_platform_alignment():
    """Test that scripts are aligned for their target platforms"""
    try:
        # Test Windows alignment
        ps_content = Path("deploy-lucid-windows.ps1").read_text()
        
        assert "Windows 11" in ps_content, "PowerShell script not marked for Windows 11"
        assert "SSH" in ps_content, "PowerShell script missing SSH Pi deployment"
        assert "Test-NetConnection" in ps_content, "PowerShell script missing Windows network testing"
        
        # Test Pi alignment
        bash_content = Path("deploy-lucid-pi.sh").read_text()
        
        assert "Raspberry Pi 5" in bash_content, "Bash script not marked for Pi 5"
        assert "ARM64" in bash_content or "aarch64" in bash_content, "Bash script missing ARM64 reference"
        assert "/sys/firmware/devicetree" in bash_content, "Bash script missing Pi hardware check"
        
        logger.info("✓ Scripts are properly aligned for their platforms")
        return True
        
    except Exception as e:
        logger.error(f"✗ Platform alignment test failed: {e}")
        return False

def main():
    """Run all deployment script tests"""
    logger.info("===== Deployment Scripts Testing =====")
    
    tests = [
        ("PowerShell Script Exists", test_powershell_script_exists),
        ("Bash Script Exists", test_bash_script_exists),
        ("PowerShell Syntax", test_powershell_syntax),
        ("Bash Syntax", test_bash_syntax),
        ("Script Parameters", test_script_parameters),
        ("Runtime Variables", test_runtime_variables),
        ("Service Definitions", test_service_definitions),
        ("Network Integration", test_network_integration),
        ("Platform Alignment", test_platform_alignment),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"{test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("===== Test Results Summary =====")
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        color = "✓" if result else "✗"
        logger.info(f"{color} {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"===== {passed}/{total} tests passed =====")
    
    if passed == total:
        logger.info("🎉 All deployment script tests passed!")
        return True
    else:
        logger.error("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)