"""Security regression test suite proving GateGuards enforce strict safety boundaries."""

import os
from pathlib import Path
import pytest

from aegis.execution.sandbox import LocalExecutor
from aegis.guard import GateGuard
from aegis.guard.paths import PathGuard
from aegis.guard.secrets import SecretGuard
from aegis.guard.commands import CommandGuard
from aegis.mcp.adapter import MCPToolAdapter
from aegis.models import PolicyDecision, ToolCallRequest
from aegis.session.checkpoint import SessionCheckpoint
from aegis.tools.base import ToolContext
from aegis.tools.fs import ReadFileTool, WritePatchTool
from aegis.tools.registry import create_default_registry


@pytest.fixture
def sec_context(tmp_path: Path):
    gateguard = GateGuard(tmp_path)
    executor = LocalExecutor(tmp_path)
    checkpoint = SessionCheckpoint(tmp_path)
    return ToolContext(
        repo_root=tmp_path,
        gateguard=gateguard,
        executor=executor,
        checkpoint=checkpoint,
    )


def test_path_traversal_blocked_in_tool(sec_context: ToolContext):
    registry = create_default_registry()
    req = ToolCallRequest(
        id="call_traversal",
        name="read_file",
        arguments={"file_path": "../../../etc/passwd"},
    )
    res = registry.dispatch(req, sec_context)
    assert res.success is False
    assert "traversal" in res.error.lower() or "denied" in res.error.lower()


def test_env_files_blocked_in_tool(sec_context: ToolContext):
    registry = create_default_registry()
    req = ToolCallRequest(
        id="call_env",
        name="read_file",
        arguments={"file_path": ".env"},
    )
    res = registry.dispatch(req, sec_context)
    assert res.success is False
    assert "denied" in res.error.lower() or "protected" in res.error.lower()


def test_git_writes_blocked_in_tool(sec_context: ToolContext):
    registry = create_default_registry()
    req = ToolCallRequest(
        id="call_git",
        name="write_patch",
        arguments={"file_path": ".git/config", "content": "malicious git edit"},
    )
    res = registry.dispatch(req, sec_context)
    assert res.success is False
    assert "denied" in res.error.lower()


def test_dangerous_commands_blocked(sec_context: ToolContext):
    registry = create_default_registry()
    dangerous_cmds = [
        "sudo apt-get update",
        "su - root",
        "rm -rf /",
        "rm -rf /*",
        ":(){ :|:& };:",
    ]
    for cmd in dangerous_cmds:
        req = ToolCallRequest(id="call_cmd", name="run_command", arguments={"command": cmd})
        res = registry.dispatch(req, sec_context)
        assert res.success is False
        err_l = res.error.lower()
        assert any(w in err_l for w in ("blocked", "denied", "forbidden"))


def test_secret_environment_variables_not_leaked(tmp_path: Path):
    secret_guard = SecretGuard()
    executor = LocalExecutor(tmp_path, secret_guard=secret_guard)

    # Put fake secret in parent env
    os.environ["GEMINI_API_KEY"] = "super-secret-key-12345"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "aws-secret-test"

    try:
        # Run command that prints environment
        res = executor.execute("env", cwd=tmp_path)
        assert res.exit_code == 0
        assert "super-secret-key-12345" not in res.stdout
        assert "aws-secret-test" not in res.stdout
        assert "GEMINI_API_KEY" not in res.stdout
        assert "AWS_SECRET_ACCESS_KEY" not in res.stdout
    finally:
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)


def test_mcp_adapter_cannot_bypass_guards(sec_context: ToolContext):
    """External MCP tool calling must be intercepted by GateGuard before execution."""
    called = False

    def dummy_mcp_invoker(args):
        nonlocal called
        called = True
        return "Executed"

    mcp_tool = MCPToolAdapter(
        name="external_mcp_file_op",
        description="External tool",
        parameters_schema={"properties": {"file_path": {"type": "string"}}, "required": ["file_path"]},
        invoker=dummy_mcp_invoker,
    )

    # Calling with forbidden path
    res = mcp_tool.execute({"file_path": ".env"}, sec_context, call_id="mcp_1")
    assert res.success is False
    assert "blocked by PathGuard" in res.error
    assert not called, "MCP invoker must not have been called"
