"""Dogfood test verifying VerificationRunner empty gates handling."""

from aegis.config import VerificationConfig
from aegis.execution.sandbox import LocalExecutor
from aegis.verifier.runner import VerificationRunner


def test_verification_runner_empty_gates(tmp_path):
    executor = LocalExecutor(tmp_path)
    config = VerificationConfig(pre_flight=None, lint=None, test_cmd=None, build_cmd=None)
    runner = VerificationRunner(tmp_path, executor, config)
    report = runner.run_all()
    assert report.status == "PASS"
    assert len(report.gates) == 0

def test_verification_runner_silent_nonzero_exit_code(tmp_path):
    """Verifies runner handles gate command with non-zero exit code and empty stdout/stderr."""
    executor = LocalExecutor(tmp_path)
    config = VerificationConfig(test_cmd="exit 42", required_gates=["test_cmd"])
    runner = VerificationRunner(tmp_path, executor, config)
    report = runner.run_all()
    assert report.status == "FAIL"
    assert len(report.gates) == 1
    assert report.gates[0].status == "FAIL"
    assert "42" in (report.gates[0].error or "")
