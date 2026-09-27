"""Git inspection tools: git_status and git_diff."""

import subprocess
from typing import Any, Optional
from pydantic import BaseModel, Field

from aegis.models import ToolResult
from aegis.tools.base import BaseTool, ToolContext, ToolPermission


class GitStatusArgs(BaseModel):
    verbose: bool = Field(default=False, description="Whether to include full status output")


class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Inspect repository git status safely without modifying any files."
    permission = ToolPermission.READ
    args_schema = GitStatusArgs

    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        try:
            res = subprocess.run(
                ["git", "status", "--short" if not arguments.get("verbose") else ""],
                cwd=str(context.repo_root),
                capture_output=True,
                text=True,
                timeout=10,
            )
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=(res.returncode == 0),
                output=res.stdout if res.returncode == 0 else res.stderr,
                error=None if res.returncode == 0 else "git status failed",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Git status failed: {e}",
            )


class GitDiffArgs(BaseModel):
    staged: bool = Field(default=False, description="Show staged changes diff")
    file_path: Optional[str] = Field(default=None, description="Optional path to limit diff to")


class GitDiffTool(BaseTool):
    name = "git_diff"
    description = "Inspect current git diff safely."
    permission = ToolPermission.READ
    args_schema = GitDiffArgs

    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        args = GitDiffArgs.model_validate(arguments)
        cmd = ["git", "diff"]
        if args.staged:
            cmd.append("--cached")
        if args.file_path:
            # Check path guard
            pe = context.gateguard.path_guard.evaluate_path(args.file_path)
            if pe.decision != pe.decision.ALLOW:
                return ToolResult(tool_name=self.name, call_id=call_id, success=False, output="", error=pe.reason)
            cmd.extend(["--", args.file_path])

        try:
            res = subprocess.run(
                [c for c in cmd if c],
                cwd=str(context.repo_root),
                capture_output=True,
                text=True,
                timeout=10,
            )
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=(res.returncode == 0),
                output=res.stdout or "[No git diff changes]",
                error=None if res.returncode == 0 else res.stderr,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Git diff failed: {e}",
            )
