"""Shell command execution tool under Aegis policy enforcement."""

from typing import Any, Optional
from pydantic import BaseModel, Field

from aegis.models import PolicyDecision, ToolResult
from aegis.tools.base import BaseTool, ToolContext, ToolPermission


class RunCommandArgs(BaseModel):
    command: str = Field(description="Shell command line string to execute within repository")
    timeout_seconds: Optional[int] = Field(default=None, description="Optional custom command timeout in seconds")


class RunCommandTool(BaseTool):
    name = "run_command"
    description = "Execute a command inside the workspace under strict command guardrail policies."
    permission = ToolPermission.EXECUTE
    args_schema = RunCommandArgs

    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        args = RunCommandArgs.model_validate(arguments)
        cmd_str = args.command

        # CommandGuard evaluation
        cmd_eval = context.gateguard.command_guard.evaluate_command(cmd_str)
        if cmd_eval.decision != PolicyDecision.ALLOW:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Command execution blocked: {cmd_eval.reason}",
            )

        exec_res = context.executor.execute(
            command=cmd_str,
            cwd=context.repo_root,
            timeout=args.timeout_seconds,
        )

        success = (exec_res.exit_code == 0 and not exec_res.timed_out)
        out_msg = f"Command: {cmd_str}\nExit Code: {exec_res.exit_code}\nDuration: {exec_res.duration_ms}ms\n\n"
        if exec_res.stdout:
            out_msg += f"STDOUT:\n{exec_res.stdout}\n"
        if exec_res.stderr:
            out_msg += f"STDERR:\n{exec_res.stderr}\n"

        err_msg = exec_res.error or (f"Command failed with exit code {exec_res.exit_code}" if not success else None)

        return ToolResult(
            tool_name=self.name,
            call_id=call_id,
            success=success,
            output=out_msg,
            error=err_msg,
            metadata={
                "exit_code": exec_res.exit_code,
                "duration_ms": exec_res.duration_ms,
                "timed_out": exec_res.timed_out,
                "backend": exec_res.backend,
            },
        )
