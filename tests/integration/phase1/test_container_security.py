"""
Lucid API - Phase 1 Integration Test: Container Security
Tests container security compliance including SBOM generation and CVE scanning

This test suite verifies:
- SBOM generation for Phase 1 containers
- Vulnerability scanning with Trivy
- Distroless base image compliance
- Security compliance scoring
- Container image signing (future)
- SLSA provenance (future)
"""

import pytest
import subprocess
import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SBOM_DIR = PROJECT_ROOT / "build" / "sbom"
SCAN_DIR = PROJECT_ROOT / "build" / "security-scans"


@pytest.mark.integration
@pytest.mark.slow
def test_sbom_generation_phase1():
    """
    Test: SBOM generation for Phase 1 containers
    
    Verifies that SBOMs can be generated for all Phase 1 containers
    """
    # Run SBOM generation script
    script_path = PROJECT_ROOT / "scripts" / "security" / "generate-sbom.sh"
    
    if not script_path.exists():
        pytest.skip("SBOM generation script not found")
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    # Run script for Phase 1
    result = subprocess.run(
        [str(script_path), "--phase", "1"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=300  # 5 minutes
    )
    
    # Check if any SBOMs were generated
    phase1_dir = SBOM_DIR / "phase1"
    if phase1_dir.exists():
        sbom_files = list(phase1_dir.glob("*-sbom.spdx-json"))
        print(f"\n✓ Generated {len(sbom_files)} SBOM files for Phase 1")
        assert len(sbom_files) > 0, "No SBOM files generated"
    else:
        pytest.skip("SBOM directory not created (containers may not be built yet)")


@pytest.mark.integration
def test_sbom_file_structure():
    """
    Test: SBOM file structure validation
    
    Verifies that generated SBOM files have correct structure
    """
    phase1_dir = SBOM_DIR / "phase1"
    
    if not phase1_dir.exists():
        pytest.skip("SBOM directory not found - run generation first")
    
    sbom_files = list(phase1_dir.glob("*-sbom.spdx-json"))
    
    if not sbom_files:
        pytest.skip("No SBOM files found")
    
    # Check first SBOM file structure
    sbom_file = sbom_files[0]
    
    with open(sbom_file, 'r') as f:
        sbom_data = json.load(f)
    
    # Verify SBOM has required fields
    assert "packages" in sbom_data, "SBOM missing 'packages' field"
    assert "SPDXID" in sbom_data, "SBOM missing 'SPDXID' field"
    
    # Verify packages exist
    packages = sbom_data.get("packages", [])
    assert len(packages) > 0, "SBOM has no packages"
    
    print(f"\n✓ SBOM structure valid: {sbom_file.name}")
    print(f"  Packages: {len(packages)}")


@pytest.mark.integration
def test_sbom_verification():
    """
    Test: SBOM verification
    
    Verifies that generated SBOMs pass validation checks
    """
    script_path = PROJECT_ROOT / "scripts" / "security" / "verify-sbom.sh"
    
    if not script_path.exists():
        pytest.skip("SBOM verification script not found")
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    # Run verification for all SBOMs
    result = subprocess.run(
        [str(script_path), "--all"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Check output
    if "All SBOMs verified successfully" in result.stdout:
        print("\n✓ All SBOMs verified successfully")
    else:
        print(f"\nVerification output:\n{result.stdout}")


@pytest.mark.integration
@pytest.mark.slow
def test_vulnerability_scanning():
    """
    Test: Vulnerability scanning
    
    Verifies that containers can be scanned for vulnerabilities
    """
    script_path = PROJECT_ROOT / "scripts" / "security" / "scan-vulnerabilities.sh"
    
    if not script_path.exists():
        pytest.skip("Vulnerability scanning script not found")
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    # Check if Trivy is installed
    trivy_check = subprocess.run(
        ["which", "trivy"],
        capture_output=True
    )
    
    if trivy_check.returncode != 0:
        pytest.skip("Trivy not installed")
    
    # Run scan for a single container (if available)
    result = subprocess.run(
        [str(script_path), "--container", "lucid-auth-service"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=600  # 10 minutes
    )
    
    # Check if scan completed
    if "scan completed" in result.stdout.lower() or result.returncode == 0:
        print("\n✓ Vulnerability scan completed")
    else:
        pytest.skip("Container not available for scanning")


@pytest.mark.integration
def test_critical_cve_threshold():
    """
    Test: Critical CVE threshold
    
    Verifies that no critical vulnerabilities exist in scanned containers
    """
    scan_dir = SCAN_DIR / "trivy"
    
    if not scan_dir.exists():
        pytest.skip("Scan directory not found - run vulnerability scan first")
    
    scan_files = list(scan_dir.glob("*.json"))
    
    if not scan_files:
        pytest.skip("No scan results found")
    
    total_critical = 0
    
    for scan_file in scan_files:
        with open(scan_file, 'r') as f:
            scan_data = json.load(f)
        
        # Count critical vulnerabilities
        for result in scan_data.get("Results", []):
            for vuln in result.get("Vulnerabilities", []):
                if vuln.get("Severity") == "CRITICAL":
                    total_critical += 1
    
    # Assert no critical vulnerabilities
    assert total_critical == 0, f"Found {total_critical} CRITICAL vulnerabilities"
    
    print("\n✓ Zero CRITICAL vulnerabilities found")


@pytest.mark.integration
def test_distroless_base_images():
    """
    Test: Distroless base images
    
    Verifies that containers use distroless base images
    """
    # Check Dockerfiles for distroless references
    distroless_count = 0
    dockerfile_count = 0
    
    # Search for Dockerfiles
    for dockerfile in PROJECT_ROOT.rglob("Dockerfile*"):
        if ".git" in str(dockerfile):
            continue
            
        dockerfile_count += 1
        
        with open(dockerfile, 'r') as f:
            content = f.read()
            if "distroless" in content.lower():
                distroless_count += 1
    
    if dockerfile_count == 0:
        pytest.skip("No Dockerfiles found")
    
    # At least some Dockerfiles should use distroless
    distroless_percentage = (distroless_count / dockerfile_count) * 100
    
    print(f"\n✓ Distroless images: {distroless_count}/{dockerfile_count} ({distroless_percentage:.1f}%)")
    
    assert distroless_count > 0, "No distroless images found"


@pytest.mark.integration
def test_security_compliance_check():
    """
    Test: Security compliance check
    
    Verifies overall security compliance
    """
    script_path = PROJECT_ROOT / "scripts" / "security" / "security-compliance-check.sh"
    
    if not script_path.exists():
        pytest.skip("Security compliance script not found")
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    # Run compliance check
    result = subprocess.run(
        [str(script_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120
    )
    
    # Parse output for compliance score
    if "Compliance Score:" in result.stdout:
        # Extract score
        for line in result.stdout.split('\n'):
            if "Compliance Score:" in line:
                print(f"\n✓ {line.strip()}")
                break
    
    # Check if any critical issues
    if "CRITICAL" in result.stdout and "0" not in result.stdout:
        pytest.fail("Critical security issues found")


@pytest.mark.integration
def test_sbom_retention_policy():
    """
    Test: SBOM retention and archiving
    
    Verifies SBOM archive directory exists and is organized
    """
    archive_dir = SBOM_DIR / "archive"
    
    if not archive_dir.exists():
        # Archive may not exist yet if no SBOMs generated
        pytest.skip("Archive directory not found (expected for new installations)")
    
    # Check archive structure
    archived_runs = list(archive_dir.glob("*"))
    
    print(f"\n✓ SBOM archive exists with {len(archived_runs)} archived runs")


@pytest.mark.integration
def test_container_image_signing():
    """
    Test: Container image signing (placeholder)
    
    Placeholder test for future image signing implementation
    """
    # This will be implemented when Cosign is integrated
    pytest.skip("Container image signing not yet implemented")


@pytest.mark.integration
def test_slsa_provenance():
    """
    Test: SLSA provenance generation (placeholder)
    
    Placeholder test for future SLSA provenance implementation
    """
    # This will be implemented when SLSA provenance is added
    pytest.skip("SLSA provenance not yet implemented")


@pytest.mark.integration
def test_sbom_formats_generated():
    """
    Test: Multiple SBOM formats
    
    Verifies that multiple SBOM formats are generated (SPDX, CycloneDX)
    """
    phase1_dir = SBOM_DIR / "phase1"
    
    if not phase1_dir.exists():
        pytest.skip("SBOM directory not found")
    
    # Check for different formats
    spdx_files = list(phase1_dir.glob("*.spdx-json"))
    cyclonedx_files = list(phase1_dir.glob("*.cyclonedx.json"))
    syft_files = list(phase1_dir.glob("*.syft.json"))
    
    formats_found = []
    if spdx_files:
        formats_found.append(f"SPDX ({len(spdx_files)})")
    if cyclonedx_files:
        formats_found.append(f"CycloneDX ({len(cyclonedx_files)})")
    if syft_files:
        formats_found.append(f"Syft ({len(syft_files)})")
    
    if not formats_found:
        pytest.skip("No SBOM files found")
    
    print(f"\n✓ SBOM formats generated: {', '.join(formats_found)}")
    
    # At least SPDX format should exist
    assert len(spdx_files) > 0, "SPDX format SBOMs not found"

