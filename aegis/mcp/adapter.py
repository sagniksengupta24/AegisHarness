"""Modular MCP tool adapter proxy enforcing Aegis GateGuard security boundaries."""

from typing import Any, Callable, Dict, Optional, Type
from pydantic import BaseModel, create_model

from aegis.models import PolicyDecision, ToolResult
from aegis.tools.base import BaseTool, ToolContext, ToolPermission


class MCPToolAdapter(BaseTool):
    """Wraps an external Model Context Protocol (MCP) tool under Aegis GateGuard enforcement."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        invoker: Callable[[dict[str, Any]], Any],
        permission: ToolPermission = ToolPermission.EXECUTE,
        timeout_seconds: int = 30,
    ):
        self.name = name
        self.description = description
        self.permission = permission
        self.timeout_seconds = timeout_seconds
        self.invoker = invoker
        self._raw_schema = parameters_schema

        # Create dynamic pydantic model from properties for validation
        fields = {}
        props = parameters_schema.get("properties", {})
        reqs = parameters_schema.get("required", [])
        for k in props:
            fields[k] = (Any, ... if k in reqs else None)
        self.args_schema = create_model(f"MCP_{name}_Args", **fields)

    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        # Pre-execution GateGuard validation
        for k, v in arguments.items():
            if isinstance(v, str):
                # Path check if key smells like path
                if any(p in k.lower() for p in ("path", "dir", "file")):
                    pe = context.gateguard.path_guard.evaluate_path(v)
                    if pe.decision != PolicyDecision.ALLOW:
                        return ToolResult(
                            tool_name=self.name,
                            call_id=call_id,
                            success=False,
                            output="",
                            error=f"MCP call blocked by PathGuard: {pe.reason}",
                        )
                # Secret check
                se = context.gateguard.secret_guard.scan_content(v, context=f"MCP param '{k}'")
                if se.decision != PolicyDecision.ALLOW:
                    return ToolResult(
                        tool_name=self.name,
                        call_id=call_id,
                        success=False,
                        output="",
                        error=f"MCP call blocked by SecretGuard: {se.reason}",
                    )

        # Isolated invocation
        try:
            raw_out = self.invoker(arguments)
            out_str = str(raw_out)
            # Post-execution secret sanitization
            clean_out = context.gateguard.secret_guard.sanitize_content(out_str)
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=True,
                output=clean_out,
                metadata={"mcp": True},
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"MCP tool error: {e}",
            )
