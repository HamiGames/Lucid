#!/usr/bin/env python3
"""
LUCID Complete Project Validation Runner

This script runs both Python build alignment validation and Electron GUI alignment validation
to provide a comprehensive project validation report.

Usage:
    python scripts/validation/run-complete-validation.py [--verbose] [--python-only] [--gui-only]

Author: LUCID Project Team
Version: 1.0.0
"""

import os
import sys
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationRunner:
    """Main validation runner class"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.scripts_dir = self.project_root / "scripts" / "validation"
        self.results = {
            "python_validation": None,
            "gui_validation": None,
            "timestamp": datetime.now().isoformat()
        }
    
    def run_python_validation(self, verbose: bool = False) -> bool:
        """Run Python build alignment validation"""
        logger.info("Running Python build alignment validation...")
        
        python_script = self.scripts_dir / "validate-python-build-alignment.py"
        if not python_script.exists():
            logger.error(f"Python validation script not found: {python_script}")
            return False
        
        try:
            cmd = [sys.executable, str(python_script)]
            if verbose:
                cmd.append("--verbose")
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            self.results["python_validation"] = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
            if result.returncode == 0:
                logger.info("[OK] Python validation passed!")
            else:
                logger.error("[X] Python validation failed!")
                if result.stderr:
                    logger.error(f"Error output: {result.stderr}")
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error running Python validation: {str(e)}")
            self.results["python_validation"] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    def run_gui_validation(self, verbose: bool = False) -> bool:
        """Run Electron GUI alignment validation"""
        logger.info("Running Electron GUI alignment validation...")
        
        gui_script = self.scripts_dir / "validate-electron-gui-alignment.py"
        if not gui_script.exists():
            logger.error(f"GUI validation script not found: {gui_script}")
            return False
        
        try:
            cmd = [sys.executable, str(gui_script)]
            if verbose:
                cmd.append("--verbose")
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            self.results["gui_validation"] = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
            if result.returncode == 0:
                logger.info("[OK] GUI validation passed!")
            else:
                logger.error("[X] GUI validation failed!")
                if result.stderr:
                    logger.error(f"Error output: {result.stderr}")
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error running GUI validation: {str(e)}")
            self.results["gui_validation"] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    def generate_summary_report(self):
        """Generate summary report"""
        print("\n" + "="*100)
        print("LUCID COMPLETE PROJECT VALIDATION SUMMARY")
        print("="*100)
        print(f"Validation completed at: {self.results['timestamp']}")
        print()
        
        # Python validation summary
        if self.results["python_validation"]:
            python_result = self.results["python_validation"]
            status = "[OK] PASSED" if python_result["success"] else "[X] FAILED"
            print(f"Python Build Alignment Validation: {status}")
            if not python_result["success"] and "error" in python_result:
                print(f"  Error: {python_result['error']}")
        else:
            print("Python Build Alignment Validation: [SKIP] SKIPPED")
        
        # GUI validation summary
        if self.results["gui_validation"]:
            gui_result = self.results["gui_validation"]
            status = "[OK] PASSED" if gui_result["success"] else "[X] FAILED"
            print(f"Electron GUI Alignment Validation: {status}")
            if not gui_result["success"] and "error" in gui_result:
                print(f"  Error: {gui_result['error']}")
        else:
            print("Electron GUI Alignment Validation: [SKIP] SKIPPED")
        
        print()
        
        # Overall status
        python_success = self.results["python_validation"]["success"] if self.results["python_validation"] else True
        gui_success = self.results["gui_validation"]["success"] if self.results["gui_validation"] else True
        
        if python_success and gui_success:
            print("[SUCCESS] OVERALL STATUS: ALL VALIDATIONS PASSED!")
            return True
        else:
            print("[WARNING] OVERALL STATUS: SOME VALIDATIONS FAILED!")
            return False
    
    def save_detailed_report(self):
        """Save detailed report to file"""
        report_file = self.project_root / "validation-report.json"
        
        try:
            import json
            with open(report_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            logger.info(f"Detailed report saved to: {report_file}")
        except Exception as e:
            logger.error(f"Error saving detailed report: {str(e)}")
    
    def run_complete_validation(self, python_only: bool = False, gui_only: bool = False, verbose: bool = False) -> bool:
        """Run complete validation"""
        logger.info("Starting LUCID complete project validation...")
        
        python_success = True
        gui_success = True
        
        # Run Python validation
        if not gui_only:
            python_success = self.run_python_validation(verbose)
        
        # Run GUI validation  
        if not python_only:
            gui_success = self.run_gui_validation(verbose)
        
        # Generate summary
        overall_success = self.generate_summary_report()
        
        # Save detailed report
        self.save_detailed_report()
        
        return overall_success

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run complete LUCID project validation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--python-only", action="store_true", help="Run only Python validation")
    parser.add_argument("--gui-only", action="store_true", help="Run only GUI validation")
    parser.add_argument("--project-root", "-p", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if args.python_only and args.gui_only:
        logger.error("Cannot specify both --python-only and --gui-only")
        sys.exit(1)
    
    # Run validation
    runner = ValidationRunner(args.project_root)
    success = runner.run_complete_validation(
        python_only=args.python_only,
        gui_only=args.gui_only,
        verbose=args.verbose
    )
    
    if success:
        logger.info("[SUCCESS] All validations completed successfully!")
        sys.exit(0)
    else:
        logger.error("[X] Some validations failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
