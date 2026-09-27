"""GateGuard centralized security pipeline for Aegis."""

from pathlib import Path
from typing import Any, Optional

from aegis.errors import PolicyViolationError, ToolDeniedError
from aegis.guard.ast import scan_python_code
from aegis.guard.commands import CommandGuard
from aegis.guard.paths import PathGuard
from aegis.guard.secrets import SecretGuard
from aegis.models import PolicyDecision, PolicyResult, ToolCallRequest


class GateGuard:
    """Centralized policy engine coordinating path, secret, command, and AST guards."""

    def __init__(
        self,
        repo_root: Path,
        deny_paths: Optional[list[str]] = None,
        blocked_commands: Optional[list[str]] = None,
        allow_network: bool = False,
    ):
        self.repo_root = repo_root.resolve()
        self.path_guard = PathGuard(self.repo_root, deny_patterns=deny_paths)
        self.secret_guard = SecretGuard()
        self.command_guard = CommandGuard(blocked_commands=blocked_commands, allow_network=allow_network)

    def evaluate_tool_request(self, request: ToolCallRequest) -> PolicyResult:
        """Evaluates tool invocation against all active GateGuard policies."""
        args = request.arguments

        # 1. Path Guard checks on arguments containing paths
        path_keys = ("path", "file_path", "target_path", "directory", "dir_path", "target")
        for key in path_keys:
            if key in args and isinstance(args[key], str):
                path_val = args[key]
                path_eval = self.path_guard.evaluate_path(path_val)
                if path_eval.decision != PolicyDecision.ALLOW:
                    return path_eval

        # 2. Secret Guard checks on contents/patches being written or searched
        content_keys = ("content", "patch", "text", "query")
        for key in content_keys:
            if key in args and isinstance(args[key], str):
                secret_eval = self.secret_guard.scan_content(args[key], context=f"tool argument '{key}'")
                if secret_eval.decision != PolicyDecision.ALLOW:
                    return secret_eval

        # 3. Command Guard checks on run_command
        if request.name == "run_command":
            cmd = args.get("command") or args.get("cmd")
            if cmd:
                cmd_eval = self.command_guard.evaluate_command(cmd)
                if cmd_eval.decision != PolicyDecision.ALLOW:
                    return cmd_eval

        # 4. AST scanner checks on write_patch or write_file targeting Python files
        if request.name in ("write_patch", "write_file"):
            target_path = args.get("path") or args.get("file_path") or ""
            content = args.get("content") or args.get("patch") or ""
            if str(target_path).endswith(".py") and content:
                ast_eval = scan_python_code(content, file_path=str(target_path))
                if ast_eval.decision == PolicyDecision.DENY:
                    return ast_eval
                # If REVIEW, we log but allow or require interactive mode

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Tool request satisfies all GateGuard policies",
            rule_name="gateguard_pass",
        )

    def authorize_or_raise(self, request: ToolCallRequest) -> None:
        """Validates tool request and raises ToolDeniedError if policy rejects it."""
        result = self.evaluate_tool_request(request)
        if result.decision == PolicyDecision.DENY:
            raise ToolDeniedError(result.reason, details=result.metadata)
