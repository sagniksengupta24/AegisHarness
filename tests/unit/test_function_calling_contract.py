"""Tests verifying the Gemini / Application-controlled function calling contract (Section 5).

Lifecycle contract:
declare tool -> model requests function -> Aegis executes function -> Aegis creates function response
-> model receives result -> next turn.

Covers:
1. Single tool call (model -> read_file -> result -> model -> finish)
2. Multiple tool calls in one turn (model -> tool A + tool B -> results -> model)
3. Invalid tool (model -> unknown tool -> structured denial/error -> no execution)
4. Invalid arguments (model -> malformed arguments -> schema failure -> no execution)
5. Tool failure recovery (model -> tool failure -> model receives failure -> recovery)
"""

from pathlib import Path
import pytest

from aegis.client import FakeModelClient, ModelResponse
from aegis.config import AegisConfig, VerificationConfig
from aegis.models import AgentStatus, ToolCallRequest, VerificationReport
from aegis.orchestrator import Orchestrator


def test_single_tool_call_lifecycle(tmp_path: Path):
    """1. Single tool call: model -> read_file -> result -> model -> finish."""
    (tmp_path / "greeting.txt").write_text("Hello Aegis World", encoding="utf-8")

    # Turn 1: model requests read_file
    tc1 = ToolCallRequest(id="c_read1", name="read_file", arguments={"file_path": "greeting.txt"})
    resp1 = ModelResponse(text="Reading greeting", tool_calls=[tc1])

    # Turn 2: model sees result and proposes completion
    resp2 = ModelResponse(text="Greeting read successfully. TASK_COMPLETE", tool_calls=[], is_proposing_completion=True)

    fake_client = FakeModelClient([resp1, resp2])
    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 0", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=fake_client)

    result = orchestrator.run_task("Read greeting")

    assert result.status == AgentStatus.COMPLETED
    audit = orchestrator.registry.audit_log
    assert len(audit) == 1
    assert audit[0]["tool"] == "read_file"
    assert audit[0]["success"] is True

    # Verify conversation history received structured tool result
    last_call = fake_client.call_history[-1]
    tool_messages = [m for m in last_call["messages"] if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["call_id"] == "c_read1"
    assert "Hello Aegis World" in tool_messages[0]["output"]


def test_multiple_tool_calls_in_one_turn(tmp_path: Path):
    """2. Multiple tool calls in single turn: model -> tool A + tool B -> results -> model."""
    (tmp_path / "f1.txt").write_text("file 1 content", encoding="utf-8")
    (tmp_path / "f2.txt").write_text("file 2 content", encoding="utf-8")

    # Turn 1: model proposes two tool calls in the same turn
    tc_a = ToolCallRequest(id="c_f1", name="read_file", arguments={"file_path": "f1.txt"})
    tc_b = ToolCallRequest(id="c_f2", name="read_file", arguments={"file_path": "f2.txt"})
    resp1 = ModelResponse(text="Reading both files in one turn", tool_calls=[tc_a, tc_b])

    resp2 = ModelResponse(text="Both read. TASK_COMPLETE", tool_calls=[], is_proposing_completion=True)

    fake_client = FakeModelClient([resp1, resp2])
    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 0", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=fake_client)

    result = orchestrator.run_task("Read two files")

    assert result.status == AgentStatus.COMPLETED
    audit = orchestrator.registry.audit_log
    assert len(audit) == 2
    assert audit[0]["tool"] == "read_file"
    assert audit[1]["tool"] == "read_file"

    # Both results must be returned to model in order
    last_call = fake_client.call_history[-1]
    tool_messages = [m for m in last_call["messages"] if m.get("role") == "tool"]
    assert len(tool_messages) == 2
    assert tool_messages[0]["call_id"] == "c_f1"
    assert "file 1 content" in tool_messages[0]["output"]
    assert tool_messages[1]["call_id"] == "c_f2"
    assert "file 2 content" in tool_messages[1]["output"]


def test_invalid_unknown_tool_rejection(tmp_path: Path):
    """3. Invalid tool: model -> unknown tool -> structured denial/error -> no execution."""
    tc_bad = ToolCallRequest(id="c_bad", name="execute_arbitrary_magic", arguments={"foo": "bar"})
    resp1 = ModelResponse(text="Calling unknown tool", tool_calls=[tc_bad])
    resp2 = ModelResponse(text="Tool was unknown, stopping.", tool_calls=[], is_proposing_completion=False)

    fake_client = FakeModelClient([resp1, resp2])
    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 0", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=fake_client)

    result = orchestrator.run_task("Trigger unknown tool")

    audit = orchestrator.registry.audit_log
    assert len(audit) == 1
    assert audit[0]["tool"] == "execute_arbitrary_magic"
    assert audit[0]["success"] is False
    assert "unknown tool" in audit[0]["error"].lower()

    # Model receives structured error response for that call ID
    last_call = fake_client.call_history[-1]
    tool_messages = [m for m in last_call["messages"] if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["call_id"] == "c_bad"
    assert tool_messages[0]["success"] is False
    assert "unknown tool" in tool_messages[0]["error"].lower()


def test_invalid_arguments_schema_failure(tmp_path: Path):
    """4. Invalid arguments: model -> malformed arguments -> schema failure -> no execution."""
    # read_file requires 'file_path: str', but model sends wrong schema / missing required arg
    tc_malformed = ToolCallRequest(id="c_malformed", name="read_file", arguments={"wrong_param": 12345})
    resp1 = ModelResponse(text="Calling with bad args", tool_calls=[tc_malformed])
    resp2 = ModelResponse(text="Schema failed.", tool_calls=[], is_proposing_completion=False)

    fake_client = FakeModelClient([resp1, resp2])
    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 0", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=fake_client)

    result = orchestrator.run_task("Bad args test")

    audit = orchestrator.registry.audit_log
    assert len(audit) == 1
    assert audit[0]["success"] is False
    assert "invalid arguments" in audit[0]["error"].lower() or "validation error" in audit[0]["error"].lower()

    # Tool execution did not touch any files
    last_call = fake_client.call_history[-1]
    tool_messages = [m for m in last_call["messages"] if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["success"] is False


def test_tool_failure_recovery_lifecycle(tmp_path: Path):
    """5. Tool failure recovery: model -> tool failure -> model receives failure -> recovery."""
    # Model attempts to read non-existent file, gets error, then reads real file and completes
    (tmp_path / "real.txt").write_text("recovered content", encoding="utf-8")

    tc_fail = ToolCallRequest(id="c_nonexistent", name="read_file", arguments={"file_path": "missing.txt"})
    resp1 = ModelResponse(text="Reading missing file", tool_calls=[tc_fail])

    # Turn 2: Model receives error and calls correct tool
    tc_recover = ToolCallRequest(id="c_real", name="read_file", arguments={"file_path": "real.txt"})
    resp2 = ModelResponse(text="Missing file failed, reading real.txt now", tool_calls=[tc_recover])

    # Turn 3: Model completes
    resp3 = ModelResponse(text="Recovered successfully. TASK_COMPLETE", tool_calls=[], is_proposing_completion=True)

    fake_client = FakeModelClient([resp1, resp2, resp3])
    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 0", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=fake_client)

    result = orchestrator.run_task("Tool failure recovery")

    assert result.status == AgentStatus.COMPLETED
    audit = orchestrator.registry.audit_log
    assert len(audit) == 2
    assert audit[0]["success"] is False  # First call failed cleanly
    assert audit[1]["success"] is True   # Second call recovered
