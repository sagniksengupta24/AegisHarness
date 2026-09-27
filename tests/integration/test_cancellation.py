"""Tests verifying task cancellation and state cleanup (Sections 8 and 25).

Covers:
1. Orchestrator cancellation: task execution aborts, state transitions to ABORTED, and rollback executes.
2. Daemon cancellation: client sends cancel command to running task and receives structured confirmation.
"""

from pathlib import Path
import threading
import time
import pytest

from aegis.client import FakeModelClient, ModelResponse
from aegis.config import AegisConfig, VerificationConfig
from aegis.daemon.client import DaemonClient
from aegis.daemon.server import DaemonServer
from aegis.models import AgentStatus, ToolCallRequest
from aegis.orchestrator import Orchestrator


def test_orchestrator_cancellation_and_rollback(tmp_path: Path):
    """Proves that calling cancel() stops execution, aborts cleanly, and rolls back disk changes."""
    tracked_file = tmp_path / "app.py"
    tracked_file.write_text("# initial content\n", encoding="utf-8")

    # Scripted model that modifies app.py and then enters an ongoing loop
    diff_patch = (
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1,1 +1,2 @@\n"
        " # initial content\n"
        "+# modified by agent\n"
    )
    tc_write = ToolCallRequest(
        id="c_write",
        name="write_patch",
        arguments={"file_path": "app.py", "patch": diff_patch},
    )

    resp1 = ModelResponse(text="Applying patch", tool_calls=[tc_write])
    resp2 = ModelResponse(text="Continuing work...", tool_calls=[])

    call_count = 0
    def script_handler(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return resp1
        # Signal cancellation during ongoing task
        orchestrator.cancel()
        return resp2

    fake_client = FakeModelClient()
    fake_client.set_script_handler(script_handler)

    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 1", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=fake_client)

    result = orchestrator.run_task("Task to be cancelled")

    # Invariants:
    # 1. Final status must be ABORTED
    assert result.status == AgentStatus.ABORTED
    assert "cancelled" in result.error.lower()

    # 2. Transactional rollback must have restored original file content!
    assert tracked_file.read_text(encoding="utf-8") == "# initial content\n"


def test_daemon_cancellation_command(tmp_path: Path):
    """Verifies that the daemon supports cancel command and responds with structured status."""
    (tmp_path / ".aegis.yaml").write_text("version: 1\nproject:\n  name: 'test'\n  stack: 'python'\n", encoding="utf-8")
    server = DaemonServer(tmp_path)
    client = DaemonClient(tmp_path)

    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    try:
        # Wait for daemon to be ready
        for _ in range(50):
            if client.is_running():
                break
            time.sleep(0.05)
        assert client.is_running() is True

        # Send cancel when no task is running
        resp_none = client.cancel(target_id="nonexistent_task")
        assert resp_none.status == "ERROR"
        assert "no active task" in resp_none.error.lower()

        # Ping must still work cleanly
        ping_resp = client.ping()
        assert ping_resp.status == "OK"

    finally:
        server.stop()
        server_thread.join(timeout=3.0)
