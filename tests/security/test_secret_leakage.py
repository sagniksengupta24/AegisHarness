"""Tests verifying secret exfiltration prevention across stdout, stderr, logs, traces, and tools."""

import json
from pathlib import Path
import pytest

from aegis.execution.sandbox import LocalExecutor
from aegis.guard.secrets import SecretGuard
from aegis.logging import scrub_secrets, register_custom_secret
from aegis.telemetry.tracer import TelemetryTracer
from aegis.models import TaskResult, AgentStatus
from aegis.diff.engine import compute_unified_diff


def test_custom_secret_scrubbing_in_subprocess_output(tmp_path: Path):
    secret_value = "TEST_SECRET_123_CONFIDENTIAL_TOKEN"
    register_custom_secret(secret_value)
    guard = SecretGuard()
    executor = LocalExecutor(tmp_path, secret_guard=guard)

    # Execute command that deliberately prints the secret to stdout and stderr
    cmd = f"python3 -c \"import sys; sys.stdout.write('{secret_value}\\n'); sys.stderr.write('err: {secret_value}\\n')\""
    result = executor.execute(cmd)

    assert secret_value not in result.stdout
    assert secret_value not in result.stderr
    assert "[REDACTED_SECRET]" in result.stdout
    assert "[REDACTED_SECRET]" in result.stderr


def test_standard_api_key_pattern_scrubbed_in_diff_and_logs():
    fake_key = "AIzaSyD987654321FakeSecretForTestingOnly"
    text = f"const apiKey = '{fake_key}';"
    scrubbed = scrub_secrets(text)

    assert fake_key not in scrubbed
    assert "[REDACTED_SECRET]" in scrubbed

    diff = compute_unified_diff("line1\n", f"line1\n{text}\n", "config.js")
    scrubbed_diff = scrub_secrets(diff)
    assert fake_key not in scrubbed_diff


def test_telemetry_trace_scrubs_secrets_before_disk_write(tmp_path: Path):
    secret_token = "TEST_SECRET_TELEMETRY_998877"
    register_custom_secret(secret_token)

    tracer = TelemetryTracer(tmp_path)
    res = TaskResult(
        session_id="test_sess_001",
        task="Test task",
        status=AgentStatus.COMPLETED,
        turns=1,
        changed_files=["app.py"],
        duration_seconds=1.2,
    )
    tool_audit = [
        {"tool_name": "run_command", "output": f"Output contained {secret_token}"}
    ]

    trace_file = tracer.write_trace(
        session_id="test_sess_001",
        task=f"Task with secret {secret_token}",
        model_name="gemini-test",
        turns=1,
        tool_audit=tool_audit,
        task_result=res,
    )

    assert trace_file is not None
    assert trace_file.exists()
    trace_content = trace_file.read_text(encoding="utf-8")

    assert secret_token not in trace_content
    assert "[REDACTED_SECRET]" in trace_content


def test_safe_env_strips_registered_and_standard_sensitive_vars():
    guard = SecretGuard()
    custom_env = {
        "PATH": "/usr/bin",
        "GEMINI_API_KEY": "secret_gemini",
        "CUSTOM_APP_SECRET": "custom_secret_val",
        "GITHUB_TOKEN": "ghp_12345",
        "DATABASE_URL": "postgres://user:pass@localhost/db",
        "SAFE_VAR": "public_value",
    }
    safe = guard.get_safe_env(base_env=custom_env)

    assert "GEMINI_API_KEY" not in safe
    assert "CUSTOM_APP_SECRET" not in safe
    assert "GITHUB_TOKEN" not in safe
    assert "DATABASE_URL" not in safe
    assert safe.get("PATH") == "/usr/bin"
    assert safe.get("CI") == "1"
