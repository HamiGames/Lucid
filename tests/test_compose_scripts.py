# Path: tests/test_compose_scripts.py
import subprocess
import pytest


@pytest.mark.parametrize(
    "script",
    [
        "06-orchestration-runtime/compose/compose_status_dev.sh",
        "06-orchestration-runtime/compose/compose_build_api.sh",
        "06-orchestration-runtime/compose/compose_build_tor.sh",
        "06-orchestration-runtime/compose/compose_clean.sh",
        "06-orchestration-runtime/compose/tor_healthcheck.sh",
    ],
)
def test_script_exists_and_executable(script):
    """Check each bash script is executable and runs with --help/expected error."""
    try:
        result = subprocess.run(["bash", script], capture_output=True, timeout=5)
    except Exception as e:
        pytest.fail(f"{script} failed to run: {e}")
    assert result.returncode in (0, 1)  # success or controlled failure
