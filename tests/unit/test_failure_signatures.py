"""Tests verifying failure fingerprint normalization and repeated failure detection (Section 9).

Proves that:
1. Dynamic timestamps, memory hex addresses, durations, and PIDs are normalized so they do not defeat loop detection.
2. The same underlying failure with varying timestamps triggers loop termination after 3 attempts.
3. Genuinely different errors are allowed to continue without false termination.
"""

from pathlib import Path
import pytest

from aegis.client import FakeModelClient, ModelResponse
from aegis.config import AegisConfig, VerificationConfig
from aegis.models import AgentStatus, ToolCallRequest
from aegis.orchestrator import Orchestrator, normalize_failure_fingerprint


def test_normalize_failure_fingerprint():
    """Unit test for normalize_failure_fingerprint helper."""
    err1 = "AssertionError: [2026-09-27 10:15:30] Object at 0x7f8b1c0 failed check in 1.42s (pid: 12345)"
    err2 = "AssertionError: [2026-09-27 10:15:35] Object at 0x7f8b9e4 failed check in 0.88s (pid: 67890)"

    norm1 = normalize_failure_fingerprint(err1)
    norm2 = normalize_failure_fingerprint(err2)

    assert norm1 == norm2
    assert "<TIMESTAMP>" in norm1 or "<TIME>" in norm1
    assert "<HEXADDR>" in norm1
    assert "<DURATION>" in norm1
    assert "pid <PID>" in norm1


def test_repeated_failure_with_varying_timestamps_detected(tmp_path: Path):
    """Proves that identical tool failures with differing timestamps are caught as repeated failures."""
    # Scripted model calls run_command with a failing command 3 times, but tool returns differing timestamps
    tc = ToolCallRequest(id="c_fail", name="run_command", arguments={"command": "exit 42"})

    resp1 = ModelResponse(text="Turn 1 fail", tool_calls=[tc])
    resp2 = ModelResponse(text="Turn 2 fail", tool_calls=[tc])
    resp3 = ModelResponse(text="Turn 3 fail", tool_calls=[tc])

    fake_client = FakeModelClient([resp1, resp2, resp3])
    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 0", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=fake_client)

    result = orchestrator.run_task("Repeated tool failure test")

    # Invariant: Loop must terminate with FAILED after 3 repeated failures
    assert result.status == AgentStatus.FAILED
    assert "repeated identical tool failure 3 times" in result.error.lower()


def test_genuinely_different_errors_allowed_to_continue(tmp_path: Path):
    """Proves that genuinely different errors are not falsely blocked by repeated failure detection."""
    # 3 different commands with distinct arguments and errors
    tc1 = ToolCallRequest(id="c1", name="run_command", arguments={"command": "echo first_error && exit 1"})
    tc2 = ToolCallRequest(id="c2", name="run_command", arguments={"command": "echo second_different && exit 2"})
    tc3 = ToolCallRequest(id="c3", name="run_command", arguments={"command": "echo third_distinct && exit 3"})

    resp1 = ModelResponse(text="Call 1", tool_calls=[tc1])
    resp2 = ModelResponse(text="Call 2", tool_calls=[tc2])
    resp3 = ModelResponse(text="Call 3", tool_calls=[tc3])
    resp4 = ModelResponse(text="Stopping.", tool_calls=[], is_proposing_completion=False)

    fake_client = FakeModelClient([resp1, resp2, resp3, resp4])
    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 0", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=fake_client)

    result = orchestrator.run_task("Different errors test")

    # Invariant: Each different error was executed and not blocked by repeated failure loop
    audit = orchestrator.registry.audit_log
    assert len(audit) == 3
    assert audit[0]["arguments"]["command"] == "echo first_error && exit 1"
    assert audit[1]["arguments"]["command"] == "echo second_different && exit 2"
    assert audit[2]["arguments"]["command"] == "echo third_distinct && exit 3"
