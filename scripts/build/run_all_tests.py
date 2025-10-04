# Lucid RDP Master Test Orchestration Script
# Runs comprehensive tests across all sections
# Based on LUCID-STRICT requirements

import sys
import subprocess
import logging
import time
from pathlib import Path
from typing import List, Tuple, Dict
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test suite configuration
TEST_SUITES = [
    {
        "name": "Core Structures Test",
        "script": "test_core_structures.py",
        "description": "Validates core data structures and blockchain concepts",
        "timeout": 60,
        "required": True
    },
    {
        "name": "Deployment Scripts Test", 
        "script": "test_deployment_scripts.py",
        "description": "Validates PowerShell and Bash deployment scripts",
        "timeout": 120,
        "required": True
    },
    {
        "name": "Network Architecture Test",
        "script": "06-orchestration-runtime/net/setup_lucid_networks.ps1",
        "args": ["-Action", "status"],
        "description": "Validates Docker network setup",
        "timeout": 30,
        "required": True,
        "type": "powershell"
    }
]

# System requirements for testing
SYSTEM_REQUIREMENTS = {
    "python_min_version": (3, 11),
    "docker_required": True,
    "powershell_required": True,
    "min_memory_gb": 4,
    "min_disk_gb": 10
}

class TestResult:
    """Represents result of a test execution"""
    
    def __init__(self, name: str, passed: bool = False, 
                 duration: float = 0.0, output: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.duration = duration
        self.output = output
        self.error = error

class TestOrchestrator:
    """Orchestrates comprehensive testing across all Lucid RDP components"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()
        
    def check_system_requirements(self) -> bool:
        """Check if system meets testing requirements"""
        logger.info("Checking system requirements...")
        
        # Check Python version
        python_version = sys.version_info
        min_version = SYSTEM_REQUIREMENTS["python_min_version"]
        
        if python_version < min_version:
            logger.error(f"Python {min_version[0]}.{min_version[1]}+ required, found {python_version.major}.{python_version.minor}")
            return False
        else:
            logger.info(f"✓ Python {python_version.major}.{python_version.minor} meets requirements")
        
        # Check Docker
        if SYSTEM_REQUIREMENTS["docker_required"]:
            try:
                result = subprocess.run(
                    ["docker", "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info("✓ Docker is available")
                else:
                    logger.error("Docker is required but not working")
                    return False
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.error("Docker is required but not found")
                return False
        
        # Check PowerShell (Windows)
        if SYSTEM_REQUIREMENTS["powershell_required"]:
            try:
                result = subprocess.run(
                    ["powershell.exe", "-Command", "Get-Host"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info("✓ PowerShell is available")
                else:
                    logger.warning("PowerShell not working - some tests may be skipped")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("PowerShell not found - some tests may be skipped")
        
        # Check available memory (rough estimate)
        try:
            import psutil
            memory_gb = psutil.virtual_memory().total / (1024**3)
            min_memory = SYSTEM_REQUIREMENTS["min_memory_gb"]
            
            if memory_gb >= min_memory:
                logger.info(f"✓ Memory: {memory_gb:.1f}GB available (>= {min_memory}GB required)")
            else:
                logger.warning(f"Memory: {memory_gb:.1f}GB available (< {min_memory}GB recommended)")
        except ImportError:
            logger.warning("psutil not available, cannot check memory")
        
        logger.info("System requirements check completed")
        return True
    
    def run_python_test(self, test_config: Dict) -> TestResult:
        """Run a Python test script"""
        script_path = Path(test_config["script"])
        
        if not script_path.exists():
            return TestResult(
                name=test_config["name"],
                passed=False,
                error=f"Test script not found: {script_path}"
            )
        
        logger.info(f"Running {test_config['name']}...")
        start_time = time.time()
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=test_config.get("timeout", 60)
            )
            
            duration = time.time() - start_time
            passed = result.returncode == 0
            
            return TestResult(
                name=test_config["name"],
                passed=passed,
                duration=duration,
                output=result.stdout,
                error=result.stderr
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                name=test_config["name"],
                passed=False,
                duration=duration,
                error=f"Test timed out after {test_config.get('timeout', 60)} seconds"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name=test_config["name"],
                passed=False,
                duration=duration,
                error=f"Test execution failed: {str(e)}"
            )
    
    def run_powershell_test(self, test_config: Dict) -> TestResult:
        """Run a PowerShell test script"""
        script_path = Path(test_config["script"])
        
        if not script_path.exists():
            return TestResult(
                name=test_config["name"],
                passed=False,
                error=f"Test script not found: {script_path}"
            )
        
        logger.info(f"Running {test_config['name']}...")
        start_time = time.time()
        
        try:
            cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
            if test_config.get("args"):
                cmd.extend(test_config["args"])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=test_config.get("timeout", 60)
            )
            
            duration = time.time() - start_time
            passed = result.returncode == 0
            
            return TestResult(
                name=test_config["name"],
                passed=passed,
                duration=duration,
                output=result.stdout,
                error=result.stderr
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                name=test_config["name"],
                passed=False,
                duration=duration,
                error=f"Test timed out after {test_config.get('timeout', 60)} seconds"
            )
        except FileNotFoundError:
            return TestResult(
                name=test_config["name"],
                passed=False,
                duration=0,
                error="PowerShell not available"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name=test_config["name"],
                passed=False,
                duration=duration,
                error=f"Test execution failed: {str(e)}"
            )
    
    def run_test_suite(self, test_config: Dict) -> TestResult:
        """Run a single test suite"""
        test_type = test_config.get("type", "python")
        
        if test_type == "python":
            return self.run_python_test(test_config)
        elif test_type == "powershell":
            return self.run_powershell_test(test_config)
        else:
            return TestResult(
                name=test_config["name"],
                passed=False,
                error=f"Unknown test type: {test_type}"
            )
    
    def run_all_tests(self) -> bool:
        """Run all configured test suites"""
        logger.info("===== Starting Lucid RDP Comprehensive Testing =====")
        
        # Check system requirements first
        if not self.check_system_requirements():
            logger.error("System requirements not met, aborting tests")
            return False
        
        total_tests = len(TEST_SUITES)
        passed_tests = 0
        
        # Run each test suite
        for i, test_config in enumerate(TEST_SUITES, 1):
            logger.info(f"[{i}/{total_tests}] {test_config['description']}")
            
            result = self.run_test_suite(test_config)
            self.results.append(result)
            
            if result.passed:
                logger.info(f"✓ {result.name} PASSED ({result.duration:.1f}s)")
                passed_tests += 1
            else:
                logger.error(f"✗ {result.name} FAILED ({result.duration:.1f}s)")
                if result.error:
                    logger.error(f"Error: {result.error}")
                
                # Stop on required test failure
                if test_config.get("required", False):
                    logger.error(f"Required test failed: {result.name}")
                    if input("Continue testing despite required test failure? (y/N): ").lower() != 'y':
                        break
        
        # Generate summary
        self.generate_test_summary(passed_tests, total_tests)
        
        return passed_tests == total_tests
    
    def generate_test_summary(self, passed: int, total: int):
        """Generate comprehensive test summary"""
        total_duration = time.time() - self.start_time
        
        logger.info("===== Test Summary =====")
        logger.info(f"Tests Run: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {total - passed}")
        logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
        logger.info(f"Total Duration: {total_duration:.1f}s")
        
        # Detailed results
        logger.info("\n===== Detailed Results =====")
        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            logger.info(f"{status:4} | {result.name:30} | {result.duration:6.1f}s")
            
            if not result.passed and result.error:
                logger.info(f"     | Error: {result.error}")
        
        # Save results to file
        self.save_test_results()
        
        # Final status
        if passed == total:
            logger.info("\n🎉 ALL TESTS PASSED! Lucid RDP is ready for deployment.")
        else:
            logger.error(f"\n❌ {total - passed} TEST(S) FAILED. Review issues before deployment.")
    
    def save_test_results(self):
        """Save test results to JSON file"""
        try:
            results_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_duration": time.time() - self.start_time,
                "results": [
                    {
                        "name": r.name,
                        "passed": r.passed,
                        "duration": r.duration,
                        "output": r.output[:1000] if r.output else "",  # Truncate long output
                        "error": r.error
                    }
                    for r in self.results
                ]
            }
            
            with open("test-results.json", "w") as f:
                json.dump(results_data, f, indent=2)
            
            logger.info("Test results saved to test-results.json")
            
        except Exception as e:
            logger.warning(f"Could not save test results: {e}")

def main():
    """Main execution function"""
    orchestrator = TestOrchestrator()
    success = orchestrator.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())