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
