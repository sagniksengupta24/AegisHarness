"""Integration tests for MCP Tool Adapter & Policy Proxy with deterministic MCP server."""

import json
from pathlib import Path
from typing import Any
import pytest

from aegis.mcp.adapter import MCPToolAdapter
from aegis.guard import GateGuard
from aegis.session.checkpoint import SessionCheckpoint
from aegis.tools.base import ToolContext
from aegis.models import PolicyDecision


class DeterministicMCPServer:
    """In-memory deterministic Model Context Protocol (MCP) server simulator."""

    def __init__(self):
        self.received_calls: list[dict[str, Any]] = []

    def handle_echo(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.received_calls.append({"method": "echo", "args": arguments})
        msg = arguments.get("message", "")
        return {"status": "success", "echoed": msg}

    def handle_fetch_config(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.received_calls.append({"method": "fetch_config", "args": arguments})
        path = arguments.get("file_path", "")
        return {"status": "ok", "path_processed": path}


def test_mcp_adapter_end_to_end_flow(tmp_path: Path):
    """Proves: Aegis -> MCPToolAdapter -> MCP Server -> tool response -> GateGuard -> Aegis result."""
    server = DeterministicMCPServer()

    adapter = MCPToolAdapter(
        name="mcp_echo",
        description="Echoes message back from deterministic MCP server",
        parameters_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
        invoker=server.handle_echo,
    )

    gateguard = GateGuard(repo_root=tmp_path)
    checkpoint = SessionCheckpoint(tmp_path)
    ctx = ToolContext(
        repo_root=tmp_path,
        gateguard=gateguard,
        executor=None,
        checkpoint=checkpoint,
    )

    result = adapter.execute({"message": "Hello from Aegis to MCP"}, ctx, "call_mcp_1")

    assert result.success is True
    assert "Hello from Aegis to MCP" in result.output
    assert len(server.received_calls) == 1
    assert server.received_calls[0]["args"]["message"] == "Hello from Aegis to MCP"


def test_mcp_adapter_denies_path_traversal_before_server(tmp_path: Path):
    """Proves: PathGuard intercepts malicious path parameters before dispatching to MCP server."""
    server = DeterministicMCPServer()

    adapter = MCPToolAdapter(
        name="mcp_fetch",
        description="Fetches config via MCP",
        parameters_schema={
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
        },
        invoker=server.handle_fetch_config,
    )

    gateguard = GateGuard(repo_root=tmp_path)
    checkpoint = SessionCheckpoint(tmp_path)
    ctx = ToolContext(
        repo_root=tmp_path,
        gateguard=gateguard,
        executor=None,
        checkpoint=checkpoint,
    )

    # Attempt traversal via MCP parameter
    res = adapter.execute({"file_path": "../../etc/passwd"}, ctx, "call_mcp_trav")

    assert res.success is False
    assert "blocked by pathguard" in res.error.lower()
    # Invariant: Server was never reached!
    assert len(server.received_calls) == 0


def test_mcp_adapter_sanitizes_secret_output(tmp_path: Path):
    """Proves: SecretGuard scrubs secrets in responses returned by MCP servers."""
    secret_leak = "AIzaSyD_FakeGoogleKeyInMCPResponse123456"

    def leaking_server(args: dict[str, Any]) -> str:
        return f"Response containing token: {secret_leak}"

    adapter = MCPToolAdapter(
        name="mcp_leaker",
        description="Server that returns credentials",
        parameters_schema={"type": "object", "properties": {}},
        invoker=leaking_server,
    )

    gateguard = GateGuard(repo_root=tmp_path)
    checkpoint = SessionCheckpoint(tmp_path)
    ctx = ToolContext(repo_root=tmp_path, gateguard=gateguard, executor=None, checkpoint=checkpoint)

    res = adapter.execute({}, ctx, "call_mcp_leak")
    assert res.success is True
    assert secret_leak not in res.output
    assert "[REDACTED_SECRET]" in res.output
