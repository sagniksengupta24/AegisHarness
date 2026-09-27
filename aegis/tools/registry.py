"""ToolRegistry managing tool discovery, schema generation, and safe invocation."""

import time
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from aegis.errors import PolicyViolationError, ToolDeniedError
from aegis.logging import get_logger
from aegis.models import PolicyDecision, ToolCallRequest, ToolResult
from aegis.tools.base import BaseTool, ToolContext
from aegis.tools.fs import ReadFileTool, SearchTool, ViewTreeTool, WritePatchTool
from aegis.tools.git_guard import GitDiffTool, GitStatusTool
from aegis.tools.inspect import RecallTool, RememberTool, RunVerificationTool
from aegis.tools.shell import RunCommandTool

logger = get_logger("aegis.tools")


class ToolRegistry:
    """Central registry for discovering, inspecting, and dispatching tool invocations."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self.audit_log: list[dict[str, Any]] = []

    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance in the registry."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieves a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """Returns all registered tool instances."""
        return list(self._tools.values())

    def get_gemini_tool_declarations(self) -> list[dict[str, Any]]:
        """Exports tool specifications formatted for Gemini function calling."""
        declarations = []
        for tool in self._tools.values():
            schema = tool.get_json_schema()
            # Clean pydantic schema for Gemini function declaration
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            declarations.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "OBJECT",
                    "properties": properties,
                    "required": required,
                },
            })
        return declarations

    def dispatch(self, request: ToolCallRequest, context: ToolContext) -> ToolResult:
        """Dispatches a tool call through GateGuard authorization and execution."""
        tool = self.get_tool(request.name)
        start_time = time.perf_counter()

        if not tool:
            res = ToolResult(
                tool_name=request.name,
                call_id=request.id,
                success=False,
                output="",
                error=f"Unknown tool '{request.name}'. Available: {list(self._tools.keys())}",
            )
            self._log_audit(request, res, duration_ms=0)
            return res

        # 1. Schema argument validation
        try:
            tool.args_schema.model_validate(request.arguments)
        except ValidationError as ve:
            res = ToolResult(
                tool_name=request.name,
                call_id=request.id,
                success=False,
                output="",
                error=f"Invalid arguments for tool '{request.name}': {ve}",
            )
            self._log_audit(request, res, duration_ms=0)
            return res

        # 2. GateGuard authorization
        policy_eval = context.gateguard.evaluate_tool_request(request)
        if policy_eval.decision == PolicyDecision.DENY:
            res = ToolResult(
                tool_name=request.name,
                call_id=request.id,
                success=False,
                output="",
                error=f"Tool call denied by GateGuard ({policy_eval.rule_name}): {policy_eval.reason}",
                metadata={"rule_name": policy_eval.rule_name, "decision": policy_eval.decision.value},
            )
            self._log_audit(request, res, duration_ms=0)
            return res

        # 3. Execution
        try:
            res = tool.execute(request.arguments, context, call_id=request.id)
        except Exception as e:
            logger.exception(f"Unhandled exception in tool {tool.name}")
            res = ToolResult(
                tool_name=request.name,
                call_id=request.id,
                success=False,
                output="",
                error=f"Tool execution failed: {e}",
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        self._log_audit(request, res, duration_ms)
        return res

    def _log_audit(self, request: ToolCallRequest, result: ToolResult, duration_ms: int) -> None:
        """Records structured audit entry."""
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "call_id": request.id,
            "tool": request.name,
            "arguments": request.arguments,
            "success": result.success,
            "error": result.error,
            "duration_ms": duration_ms,
        }
        self.audit_log.append(entry)


def create_default_registry() -> ToolRegistry:
    """Instantiates registry populated with all core Aegis tools."""
    registry = ToolRegistry()
    registry.register(ViewTreeTool())
    registry.register(ReadFileTool())
    registry.register(WritePatchTool())
    registry.register(RunCommandTool())
    registry.register(GitStatusTool())
    registry.register(GitDiffTool())
    registry.register(RunVerificationTool())
    registry.register(SearchTool())
    registry.register(RememberTool())
    registry.register(RecallTool())
    return registry
