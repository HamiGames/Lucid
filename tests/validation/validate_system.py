"""
System Validation

Comprehensive system validation that orchestrates all validation tests.
Validates the complete Lucid system across all 10 clusters.

This is the main validation entry point that runs:
- Service Health Validation
- API Response Validation  
- Integration Validation
- Container Status Validation

Usage:
    python -m tests.validation.validate_system
    ./scripts/validation/run-full-validation.sh
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

# Import validation modules
from .test_all_services_healthy import ServiceHealthValidator
from .test_all_apis_responding import APIResponseValidator
from .test_all_integrations import IntegrationValidator
from .test_all_containers_running import ContainerValidator

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Overall validation result"""
    validation_type: str
    is_successful: bool
    execution_time_ms: float
    details: Dict[str, Any]
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class SystemValidationReport:
    """Complete system validation report"""
    timestamp: datetime
    overall_success: bool
    total_execution_time_ms: float
    validation_results: List[ValidationResult]
    summary: Dict[str, Any]
    recommendations: List[str]


class SystemValidator:
    """Main system validator that orchestrates all validation tests"""
    
    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token
        self.validation_results: List[ValidationResult] = []
    
    async def run_service_health_validation(self) -> ValidationResult:
        """Run service health validation"""
        start_time = datetime.utcnow()
        
        try:
            async with ServiceHealthValidator() as validator:
                results = await validator.check_all_services()
                report = validator.generate_health_report(results)
                
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds() * 1000
                
                is_successful = report["summary"]["unhealthy_services"] == 0
                
                return ValidationResult(
                    validation_type="service_health",
                    is_successful=is_successful,
                    execution_time_ms=execution_time,
                    details=report,
                    error_message=None if is_successful else f"{report['summary']['unhealthy_services']} unhealthy services"
                )
        
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ValidationResult(
                validation_type="service_health",
                is_successful=False,
                execution_time_ms=execution_time,
                details={},
                error_message=str(e)
            )
    
    async def run_api_response_validation(self) -> ValidationResult:
        """Run API response validation"""
        start_time = datetime.utcnow()
        
        try:
            async with APIResponseValidator(auth_token=self.auth_token) as validator:
                results = await validator.test_all_endpoints()
                report = validator.generate_api_report(results)
                
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds() * 1000
                
                is_successful = report["summary"]["non_responding_endpoints"] == 0
                
                return ValidationResult(
                    validation_type="api_response",
                    is_successful=is_successful,
                    execution_time_ms=execution_time,
                    details=report,
                    error_message=None if is_successful else f"{report['summary']['non_responding_endpoints']} non-responding endpoints"
                )
        
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ValidationResult(
                validation_type="api_response",
                is_successful=False,
                execution_time_ms=execution_time,
                details={},
                error_message=str(e)
            )
    
    async def run_integration_validation(self) -> ValidationResult:
        """Run integration validation"""
        start_time = datetime.utcnow()
        
        try:
            async with IntegrationValidator(auth_token=self.auth_token) as validator:
                results = await validator.test_all_integrations()
                report = validator.generate_integration_report(results)
                
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds() * 1000
                
                is_successful = report["summary"]["failed_tests"] == 0
                
                return ValidationResult(
                    validation_type="integration",
                    is_successful=is_successful,
                    execution_time_ms=execution_time,
                    details=report,
                    error_message=None if is_successful else f"{report['summary']['failed_tests']} failed integration tests"
                )
        
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ValidationResult(
                validation_type="integration",
                is_successful=False,
                execution_time_ms=execution_time,
                details={},
                error_message=str(e)
            )
    
    async def run_container_validation(self) -> ValidationResult:
        """Run container validation"""
        start_time = datetime.utcnow()
        
        try:
            validator = ContainerValidator()
            results = await validator.validate_all_containers()
            report = validator.generate_container_report(results)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            is_successful = report["summary"]["stopped_containers"] == 0
            
            return ValidationResult(
                validation_type="container_status",
                is_successful=is_successful,
                execution_time_ms=execution_time,
                details=report,
                error_message=None if is_successful else f"{report['summary']['stopped_containers']} stopped containers"
            )
        
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ValidationResult(
                validation_type="container_status",
                is_successful=False,
                execution_time_ms=execution_time,
                details={},
                error_message=str(e)
            )
    
    async def run_all_validations(self) -> SystemValidationReport:
        """Run all validation tests"""
        overall_start_time = datetime.utcnow()
        self.validation_results = []
        
        logger.info("Starting comprehensive system validation...")
        
        # Run validations in parallel for better performance
        validation_tasks = [
            self.run_service_health_validation(),
            self.run_api_response_validation(),
            self.run_integration_validation(),
            self.run_container_validation()
        ]
        
        try:
            # Execute all validations concurrently
            results = await asyncio.gather(*validation_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    validation_type = ["service_health", "api_response", "integration", "container_status"][i]
                    self.validation_results.append(ValidationResult(
                        validation_type=validation_type,
                        is_successful=False,
                        execution_time_ms=0,
                        details={},
                        error_message=str(result)
                    ))
                else:
                    self.validation_results.append(result)
            
            # Generate overall report
            overall_end_time = datetime.utcnow()
            total_execution_time = (overall_end_time - overall_start_time).total_seconds() * 1000
            
            report = self._generate_system_report(total_execution_time)
            
            logger.info(f"System validation completed in {total_execution_time:.2f}ms")
            logger.info(f"Overall success: {report.overall_success}")
            
            return report
        
        except Exception as e:
            overall_end_time = datetime.utcnow()
            total_execution_time = (overall_end_time - overall_start_time).total_seconds() * 1000
            
            logger.error(f"System validation failed: {str(e)}")
            
            return SystemValidationReport(
                timestamp=overall_start_time,
                overall_success=False,
                total_execution_time_ms=total_execution_time,
                validation_results=self.validation_results,
                summary={
                    "total_validations": 4,
                    "successful_validations": 0,
                    "failed_validations": 4,
                    "success_rate": 0.0
                },
                recommendations=[f"System validation failed with error: {str(e)}"]
            )
    
    def _generate_system_report(self, total_execution_time: float) -> SystemValidationReport:
        """Generate comprehensive system validation report"""
        successful_validations = sum(1 for r in self.validation_results if r.is_successful)
        failed_validations = len(self.validation_results) - successful_validations
        success_rate = (successful_validations / len(self.validation_results)) * 100
        
        overall_success = failed_validations == 0
        
        # Generate summary statistics
        summary = {
            "total_validations": len(self.validation_results),
            "successful_validations": successful_validations,
            "failed_validations": failed_validations,
            "success_rate": round(success_rate, 2),
            "total_execution_time_ms": round(total_execution_time, 2),
            "validation_breakdown": {
                result.validation_type: {
                    "success": result.is_successful,
                    "execution_time_ms": round(result.execution_time_ms, 2),
                    "error": result.error_message
                }
                for result in self.validation_results
            }
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        return SystemValidationReport(
            timestamp=datetime.utcnow(),
            overall_success=overall_success,
            total_execution_time_ms=total_execution_time,
            validation_results=self.validation_results,
            summary=summary,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        for result in self.validation_results:
            if not result.is_successful:
                if result.validation_type == "service_health":
                    recommendations.append(
                        "Service Health: Check and restart unhealthy services. Review service logs for errors."
                    )
                elif result.validation_type == "api_response":
                    recommendations.append(
                        "API Response: Check API endpoints and ensure all services are responding correctly."
                    )
                elif result.validation_type == "integration":
                    recommendations.append(
                        "Integration: Review integration points between clusters and check service mesh connectivity."
                    )
                elif result.validation_type == "container_status":
                    recommendations.append(
                        "Container Status: Check Docker containers and restart stopped or unhealthy containers."
                    )
        
        if not recommendations:
            recommendations.append("All validations passed successfully. System is healthy and operational.")
        
        return recommendations
    
    def print_report(self, report: SystemValidationReport):
        """Print validation report to console"""
        print("\n" + "="*80)
        print("LUCID SYSTEM VALIDATION REPORT")
        print("="*80)
        print(f"Timestamp: {report.timestamp.isoformat()}")
        print(f"Overall Success: {'✅ PASS' if report.overall_success else '❌ FAIL'}")
        print(f"Total Execution Time: {report.total_execution_time_ms:.2f}ms")
        print(f"Success Rate: {report.summary['success_rate']}%")
        print()
        
        print("VALIDATION BREAKDOWN:")
        print("-" * 40)
        for validation_type, details in report.summary['validation_breakdown'].items():
            status = "✅ PASS" if details['success'] else "❌ FAIL"
            print(f"{validation_type.replace('_', ' ').title()}: {status} ({details['execution_time_ms']:.2f}ms)")
            if details['error']:
                print(f"  Error: {details['error']}")
        print()
        
        print("RECOMMENDATIONS:")
        print("-" * 40)
        for i, recommendation in enumerate(report.recommendations, 1):
            print(f"{i}. {recommendation}")
        print()
        
        if report.overall_success:
            print("🎉 SYSTEM VALIDATION PASSED - All clusters are operational!")
        else:
            print("⚠️  SYSTEM VALIDATION FAILED - Please review recommendations above.")
        
        print("="*80)
    
    def save_report(self, report: SystemValidationReport, filepath: str):
        """Save validation report to file"""
        report_data = {
            "timestamp": report.timestamp.isoformat(),
            "overall_success": report.overall_success,
            "total_execution_time_ms": report.total_execution_time_ms,
            "summary": report.summary,
            "validation_results": [
                {
                    "validation_type": r.validation_type,
                    "is_successful": r.is_successful,
                    "execution_time_ms": r.execution_time_ms,
                    "error_message": r.error_message,
                    "timestamp": r.timestamp.isoformat(),
                    "details": r.details
                }
                for r in report.validation_results
            ],
            "recommendations": report.recommendations
        }
        
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Validation report saved to {filepath}")


async def main():
    """Main entry point for system validation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Lucid System Validation")
    parser.add_argument("--auth-token", help="Authentication token for protected endpoints")
    parser.add_argument("--output", help="Output file for validation report")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode (no console output)")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run validation
    validator = SystemValidator(auth_token=args.auth_token)
    report = await validator.run_all_validations()
    
    # Print report
    if not args.quiet:
        validator.print_report(report)
    
    # Save report if requested
    if args.output:
        validator.save_report(report, args.output)
    
    # Exit with appropriate code
    exit_code = 0 if report.overall_success else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
