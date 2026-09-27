"""Unit tests for verification runner and gate reports."""

from pathlib import Path
from aegis.config import VerificationConfig
from aegis.execution.sandbox import LocalExecutor
from aegis.verifier.runner import VerificationRunner


def test_verification_runner_pass(tmp_path: Path):
    executor = LocalExecutor(tmp_path)
    config = VerificationConfig(
        pre_flight=None,
        lint=None,
        test_cmd="echo 'Tests passed' && exit 0",
        build_cmd=None,
    )
    runner = VerificationRunner(tmp_path, executor, config)
    report = runner.run_all()
    assert report.status == "PASS"
    assert len(report.gates) == 1
    assert report.gates[0].exit_code == 0


def test_verification_runner_fail(tmp_path: Path):
    executor = LocalExecutor(tmp_path)
    config = VerificationConfig(
        pre_flight=None,
        lint=None,
        test_cmd="echo 'Test assertion error' >&2 && exit 1",
        build_cmd=None,
    )
    runner = VerificationRunner(tmp_path, executor, config)
    report = runner.run_all()
    assert report.status == "FAIL"
    assert report.actionable_instruction is not None
    assert "Test assertion error" in report.actionable_instruction
